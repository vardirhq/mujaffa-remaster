#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, json, math, struct, re
from pathlib import Path

SHAPE_TAGS={2,22,32}
CHAR_TAGS={2,6,7,10,11,14,20,21,22,32,33,34,35,36,37,39,46,48,60,75,83,84,87,90,91}

class Bits:
    def __init__(self,data:bytes,bit:int=0): self.data=data; self.bit=bit
    def u(self,n:int)->int:
        v=0
        for _ in range(n):
            bi,bj=divmod(self.bit,8)
            if bi>=len(self.data): raise ValueError('truncated bit stream')
            v=(v<<1)|((self.data[bi]>>(7-bj))&1); self.bit+=1
        return v
    def s(self,n:int)->int:
        if n<=0:return 0
        v=self.u(n); sign=1<<(n-1); return v-(1<<n) if v&sign else v
    def align(self): self.bit=((self.bit+7)//8)*8
    @property
    def off(self): return self.bit//8

def swf_tags(path:Path):
    raw=path.read_bytes()
    if raw[:3]==b'CWS':
        import zlib; raw=b'FWS'+raw[3:8]+zlib.decompress(raw[8:])
    if raw[:3]!=b'FWS': raise ValueError('only FWS/CWS supported')
    b=Bits(raw,64); n=b.u(5); [b.s(n) for _ in range(4)]; b.align(); off=b.off+4
    return raw,off

def iter_tags(data:bytes,offset:int=0):
    cur=offset
    while cur+2<=len(data):
        rec=struct.unpack_from('<H',data,cur)[0];cur+=2
        code=rec>>6; ln=rec&0x3f
        if ln==0x3f: ln=struct.unpack_from('<I',data,cur)[0];cur+=4
        p=data[cur:cur+ln];cur+=ln
        yield code,p
        if code==0:return

def read_matrix(data:bytes,offset:int):
    b=Bits(data,offset*8); a=d=1.0; bb=c=0.0
    if b.u(1):
        n=b.u(5); a=b.s(n)/65536.0; d=b.s(n)/65536.0
    if b.u(1):
        n=b.u(5); c=b.s(n)/65536.0; bb=b.s(n)/65536.0
    n=b.u(5); e=b.s(n)/20.0; f=b.s(n)/20.0; b.align()
    return b.off,(a,bb,c,d,e,f)

def skip_cx(data:bytes,offset:int):
    b=Bits(data,offset*8); add=b.u(1); mult=b.u(1); n=b.u(4)
    if mult:
        for _ in range(4): b.s(n)
    if add:
        for _ in range(4): b.s(n)
    b.align(); return b.off

def cstr(data:bytes,offset:int):
    end=data.find(b'\0',offset)
    return data[offset:end].decode('utf-8','replace'),end+1

def place2(p:bytes):
    o=0; flags=p[o];o+=1; depth=struct.unpack_from('<H',p,o)[0];o+=2
    x={'depth':depth,'move':bool(flags&1)}
    if flags&2: x['character']=struct.unpack_from('<H',p,o)[0];o+=2
    if flags&4: o,x['matrix']=read_matrix(p,o)
    if flags&8:o=skip_cx(p,o)
    if flags&0x10:o+=2
    if flags&0x20:x['name'],o=cstr(p,o)
    if flags&0x40:
        x['clip_depth']=struct.unpack_from('<H',p,o)[0]; o+=2
    return x

def mul(m1,m2):
    a,b,c,d,e,f=m1; A,B,C,D,E,F=m2
    return (a*A+c*B,b*A+d*B,a*C+c*D,b*C+d*D,a*E+c*F+e,b*E+d*F+f)

IDENT=(1.0,0.0,0.0,1.0,0.0,0.0)

class Movie:
    def __init__(self,path:Path):
        data,off=swf_tags(path); self.sprites={}; self.types={}
        for code,p in iter_tags(data,off):
            if code in CHAR_TAGS and len(p)>=2:self.types[struct.unpack_from('<H',p,0)[0]]=code
            if code==39:
                sid,frames=struct.unpack_from('<HH',p,0); self.sprites[sid]=(frames,p[4:])
    def display(self,sid:int,frame:int):
        frames,data=self.sprites[sid]; frame=max(1,min(frame,frames)); cur=1; disp={}
        for code,p in iter_tags(data):
            if cur>frame: break
            if code==26:
                x=place2(p); d=x['depth']; old=disp.get(d,{}).copy() if x.get('move') else {}
                old.update({k:v for k,v in x.items() if k not in ('depth','move')}); old['depth']=d; disp[d]=old
            elif code==28: disp.pop(struct.unpack_from('<H',p,0)[0],None)
            elif code==1: cur+=1
        return [disp[d] for d in sorted(disp)]
    def leaves(self,cid:int,frame:int=1,matrix=IDENT,path=(),overrides=None,skip_names=frozenset(),only_name=None,seen=(),masks=()):
        overrides=overrides or {}
        if cid in seen:return []
        t=self.types.get(cid)
        if t in SHAPE_TAGS:return [{'shape':cid,'matrix':matrix,'path':path,'masks':masks}]
        if t!=39 or cid not in self.sprites:return []
        out=[]; target=overrides.get(cid,frame)
        display=self.display(cid,target)
        local_masks=[item for item in display if 'clip_depth' in item and item.get('character') is not None]
        for item in display:
            child=item.get('character')
            if child is None or 'clip_depth' in item: continue
            name=item.get('name')
            if name in skip_names: continue
            if only_name is not None and name!=only_name: continue
            child_matrix=mul(matrix,item.get('matrix',IDENT))
            active=list(masks)
            for mask_item in local_masks:
                if mask_item['depth'] < item['depth'] <= mask_item['clip_depth']:
                    active.append((mask_item['character'], mul(matrix,mask_item.get('matrix',IDENT))))
            p=path+((name if name else f'#{item["depth"]}:{child}'),)
            out.extend(self.leaves(child,1,child_matrix,p,overrides,skip_names,None,seen+(cid,),tuple(active)))
        return out

def transform_bounds(bounds,m):
    x0,x1,y0,y1=bounds; a,b,c,d,e,f=m
    pts=[(x0,y0),(x0,y1),(x1,y0),(x1,y1)]
    xs=[a*x+c*y+e for x,y in pts]; ys=[b*x+d*y+f for x,y in pts]
    return min(xs),max(xs),min(ys),max(ys)

def sanitize(s): return re.sub(r'[^a-z0-9_-]+','-',s.lower()).strip('-')

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('swf',type=Path); ap.add_argument('reference_art',type=Path); ap.add_argument('out',type=Path); ap.add_argument('--scale',type=float,default=4.0)
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True); (a.out/'svg').mkdir(exist_ok=True); (a.out/'png').mkdir(exist_ok=True)
    movie=Movie(a.swf)
    art=json.loads((a.reference_art/'manifest.json').read_text(encoding='utf-8')); items={i['character_id']:i for i in art['items']}

    root=875
    root_disp=movie.display(root,1)
    root_named={i.get('name'):i for i in root_disp if i.get('name')}
    car_body=root_named['karosseri']; tyres=root_named['dæk']; speakers=root_named['speakers']

    body_disp=movie.display(car_body['character'],1)
    body_named={i.get('name'):i for i in body_disp if i.get('name')}
    discovered={k:{'character_id':v.get('character'),'depth':v['depth'],'matrix':v.get('matrix',IDENT)} for k,v in body_named.items()}

    categories={
      'farvestribe': {'sprite':66,'variants':['empty','pink','sort','grøn','hvid']},
      'hjulkapsel': {'sprite':74,'variants':['standard','racer','krom','guld']},
      'spoiler': {'sprite':87,'variants':['1','2','3','4','5']},
      'indtraek': {'sprite':93,'variants':['polyester','tiger','læder','skind']},
      'forrude': {'sprite':102,'variants':['empty','nosser','wunderbaum','hjerte','koran']},
      'vinduer': {'sprite':107,'variants':['standard','gradient','tonede','spejlrefleks']},
      'soltag': {'sprite':112,'variants':['off','on']},
      'udstodning': {'sprite':131,'variants':['1','2','3','4']},
      'daek': {'sprite':781,'variants':['1','2','3','4']},
      'paint': {'sprite':97,'variants':['tintable']},
      'nummerplade': {'sprite':109,'variants':['dynamic-text']},
    }

    speaker_disp=movie.display(126,1); speaker_named={i.get('name'):i for i in speaker_disp if i.get('name')}
    speaker_variant_frames = {
      'woofer': [(1,'empty'), (2,'drop1'), (30,'drop2'), (60,'drop3')],
      'front': [(1,'empty'), (2,'drop1'), (30,'drop2')],
      'side': [(1,'empty'), (2,'drop1'), (30,'drop2')],
      'rear': [(1,'empty'), (2,'drop1'), (30,'drop2')],
    }
    speaker_frames = {}
    for n,i in speaker_named.items():
        sid=i.get('character'); speaker_frames[f'speaker_{n}']=speaker_variant_frames[n]
        categories[f'speaker_{n}']={'sprite':sid,'variants':[label for _,label in speaker_variant_frames[n]]}

    def car_leaves(overrides=None):
        return (movie.leaves(root,1,overrides=overrides or {},only_name='karosseri') +
                movie.leaves(root,1,overrides=overrides or {},only_name='dæk') +
                movie.leaves(root,1,overrides=overrides or {},only_name='speakers'))

    sets=[]
    stock=car_leaves(); sets.append(stock)
    variant_specs=[]
    for cat,spec in categories.items():
        sid=spec['sprite']
        if cat in speaker_frames:
            choices=speaker_frames[cat]
        else:
            choices=[(idx, spec['variants'][idx-1] if idx-1 < len(spec['variants']) else str(idx)) for idx in range(1, movie.sprites.get(sid,(1,b''))[0] + 1)]
        for frame_index,label in choices:
            variant_specs.append((cat,frame_index,label))
            sets.append(car_leaves({sid:frame_index}))
    all_leaves=[leaf for ss in sets for leaf in ss if leaf['shape'] in items]
    bounds=[]
    for leaf in all_leaves: bounds.append(transform_bounds(items[leaf['shape']]['bounds'],leaf['matrix']))
    x0=min(b[0] for b in bounds); x1=max(b[1] for b in bounds); y0=min(b[2] for b in bounds); y1=max(b[3] for b in bounds)
    pad=4.0; canvas=(x0-pad,x1+pad,y0-pad,y1+pad); cw=canvas[1]-canvas[0]; ch=canvas[3]-canvas[2]

    def write_layer(name, leaves):
        body=[]; unresolved=[]; defs=[]; mask_ids={}
        def image_for(shape_id, matrix):
            info=items.get(shape_id)
            if not info: return ''
            svg=(a.reference_art/info['svg']).read_text(encoding='utf-8')
            encoded=base64.b64encode(svg.encode()).decode()
            bx0,bx1,by0,by1=info['bounds']; ms=' '.join(f'{v:.8g}' for v in matrix)
            return f'<image href="data:image/svg+xml;base64,{encoded}" x="{bx0}" y="{by0}" width="{bx1-bx0}" height="{by1-by0}" transform="matrix({ms})"/>'
        def ensure_mask(desc):
            key=(desc[0],tuple(round(v,7) for v in desc[1]))
            if key in mask_ids:return mask_ids[key]
            mid=f'm{len(mask_ids)+1}'; mask_ids[key]=mid
            mask_leaves=movie.leaves(desc[0],1,matrix=desc[1],overrides={})
            inner=''.join(image_for(ml['shape'],ml['matrix']) for ml in mask_leaves if ml['shape'] in items)
            defs.append(f'<mask id="{mid}" maskUnits="userSpaceOnUse" x="{canvas[0]}" y="{canvas[2]}" width="{cw}" height="{ch}" style="mask-type:alpha">{inner}</mask>')
            return mid
        for leaf in leaves:
            info=items.get(leaf['shape'])
            if not info: unresolved.append(leaf['shape']); continue
            element=image_for(leaf['shape'],leaf['matrix'])
            for desc in leaf.get('masks',()):
                element=f'<g mask="url(#{ensure_mask(desc)})">{element}</g>'
            body.append(element)
        out=f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{canvas[0]} {canvas[2]} {cw} {ch}"><defs>' + ''.join(defs) + '</defs>' + ''.join(body) + '</svg>'
        svg_path=a.out/'svg'/f'{name}.svg'; svg_path.write_text(out,encoding='utf-8')
        png_path=a.out/'png'/f'{name}.png'
        try:
            import cairosvg
            scale=a.scale; cairosvg.svg2png(bytestring=out.encode(),write_to=str(png_path),output_width=max(1,math.ceil(cw*scale)),output_height=max(1,math.ceil(ch*scale)))
        except ImportError: png_path=None
        return {'svg':str(svg_path.relative_to(a.out)),'png':str(png_path.relative_to(a.out)) if png_path else None,'shapes':len(leaves),'unresolved':sorted(set(unresolved))}

    outputs={}
    outputs['stock']=write_layer('car-stock',stock)
    for cat,idx,label in variant_specs:
        sid=categories[cat]['sprite']; leaves=car_leaves({sid:idx})
        outputs[f'{cat}:{label}']=write_layer(f'{sanitize(cat)}-{idx:02d}-{sanitize(label)}',leaves)

    manifest={
      'source':a.swf.name,'root_sprite':875,'body_sprite':car_body['character'],'tyre_sprite':tyres['character'],'speaker_sprite':speakers['character'],
      'canvas_bounds':canvas,'scale':a.scale,'root_instances':root_named,'body_named_instances':discovered,
      'speaker_instances':{k:{'character_id':v.get('character'),'depth':v['depth'],'matrix':v.get('matrix',IDENT)} for k,v in speaker_named.items()},
      'categories':categories,'outputs':outputs,
      'notes':['Paint is a tintable Flash Color transform, not a set of baked colour frames.','Number plate text is dynamic and must remain text in the remaster.','All PNGs share one registration canvas and may be stacked at the same origin.']
    }
    (a.out/'car-manifest.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print(f"car sprite {root}: {len(outputs)} reference renders on shared {cw:.1f}x{ch:.1f} canvas")

if __name__=='__main__': main()
