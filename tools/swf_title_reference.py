#!/usr/bin/env python3
"""Extract original Mujaffa opening/title timeline evidence from the SWF."""
from __future__ import annotations
import argparse,json,struct
from pathlib import Path
from swf_inventory import BitReader,SwfError,iter_tags,parse_header
from swf_shape_reference import decode_shape_records
from swf_text_reference import decode_text_records
from swf_font_reference import decode_define_font,decode_define_font2
from swf_button_reference import decode_button
OPENING_LABELS={"start","velkommen","speakDone","gotoInstruktioner","gotoGame","initGame"}
def _cstring(p):return p.split(b"\0",1)[0].decode("utf-8",errors="replace")
def _u16(p,o=0):return struct.unpack_from("<H",p,o)[0]
def _matrix(p,o):
 b=BitReader(p,o);sx=sy=1.;r0=r1=0.
 if b.read_unsigned(1):n=b.read_unsigned(5);sx,sy=b.read_signed(n)/65536.,b.read_signed(n)/65536.
 if b.read_unsigned(1):n=b.read_unsigned(5);r0,r1=b.read_signed(n)/65536.,b.read_signed(n)/65536.
 n=b.read_unsigned(5);tx=b.read_signed(n)/20. if n else 0.;ty=b.read_signed(n)/20. if n else 0.
 return {"scale_x":sx,"scale_y":sy,"rotate_skew_0":r0,"rotate_skew_1":r1,"translate_x":tx,"translate_y":ty},b.byte_offset
def _cxform(p,o):
 b=BitReader(p,o);ha=bool(b.read_unsigned(1));hm=bool(b.read_unsigned(1));n=b.read_unsigned(4);m=[256]*4;a=[0]*4
 if hm:m=[b.read_signed(n) for _ in range(4)]
 if ha:a=[b.read_signed(n) for _ in range(4)]
 return {"multiply":dict(zip("rgba",[v/256. for v in m])),"add":dict(zip("rgba",a))},b.byte_offset
def _rect(p,o=0):
 b=BitReader(p,o);n=b.read_unsigned(5);v=[b.read_signed(n) for _ in range(4)]
 return {"x_min":v[0]/20.,"x_max":v[1]/20.,"y_min":v[2]/20.,"y_max":v[3]/20.},b.byte_offset
def _place(code,p):
 if code==4:
  if len(p)<4:raise SwfError("truncated PlaceObject")
  cid,d=struct.unpack_from("<HH",p);m,_=_matrix(p,4);return {"character_id":cid,"depth":d,"move":False,"matrix":m}
 if code!=26:raise SwfError(f"unsupported placement tag {code}")
 if len(p)<3:raise SwfError("truncated PlaceObject2")
 f,o=p[0],3;e={"depth":_u16(p,1),"move":bool(f&1)}
 if f&2:e["character_id"]=_u16(p,o);o+=2
 if f&4:e["matrix"],o=_matrix(p,o)
 if f&8:e["color_transform"],o=_cxform(p,o)
 if f&16:e["ratio"]=_u16(p,o);o+=2
 if f&32:
  end=p.find(b"\0",o)
  if end<0:raise SwfError("unterminated name")
  e["name"]=p[o:end].decode("utf-8",errors="replace");o=end+1
 if f&64:e["clip_depth"]=_u16(p,o);o+=2
 if f&128:e["has_clip_actions"]=True
 return e
def _named(data,off):
 found={}
 for t in iter_tags(data,off):
  if t.code not in {56,76} or len(t.payload)<2:continue
  count,o=_u16(t.payload),2
  for _ in range(count):
   if o+2>len(t.payload):break
   cid=_u16(t.payload,o);o+=2;end=t.payload.find(b"\0",o)
   if end<0:break
   name=t.payload[o:end].decode("utf-8",errors="replace");o=end+1;found.setdefault((cid,name),set()).add("SymbolClass" if t.code==76 else "ExportAssets")
 return [{"character_id":cid,"name":name,"sources":sorted(src)} for (cid,name),src in sorted(found.items())]
def _sprite_timeline(payload):
 frame=1;events=[]
 for t in iter_tags(payload,0):
  if t.code==1:frame+=1;continue
  if t.code in {4,26}:e={"frame":frame,"tag":"PlaceObject" if t.code==4 else "PlaceObject2"};e.update(_place(t.code,t.payload));events.append(e)
  elif t.code==5 and len(t.payload)>=4:cid,d=struct.unpack_from("<HH",t.payload);events.append({"frame":frame,"tag":"RemoveObject","character_id":cid,"depth":d})
  elif t.code==28 and len(t.payload)>=2:events.append({"frame":frame,"tag":"RemoveObject2","depth":_u16(t.payload)})
  elif t.code==43:events.append({"frame":frame,"tag":"FrameLabel","label":_cstring(t.payload)})
 return events
def _definitions(data,off):
 kinds={2:"shape",22:"shape",32:"shape",83:"shape",7:"button",34:"button",10:"font",48:"font",75:"font",11:"text",33:"text",37:"edit_text",39:"sprite"};versions={2:1,22:2,32:3,83:4};out={}
 for t in iter_tags(data,off):
  if t.code not in kinds or len(t.payload)<2:continue
  cid=_u16(t.payload);entry={"kind":kinds[t.code],"tag_code":t.code}
  if t.code in versions:
   entry["bounds"],o=_rect(t.payload,2)
   if t.code==83:
    entry["edge_bounds"],o=_rect(t.payload,o);flags=t.payload[o];o+=1;entry["shape_flags"]={"uses_fill_winding":bool(flags&4),"uses_non_scaling_strokes":bool(flags&2),"uses_scaling_strokes":bool(flags&1)}
   entry["shape"]=decode_shape_records(t.payload,o,versions[t.code])
  elif t.code in {7,34}:entry["button"]=decode_button(t.payload,t.code)
  elif t.code==10:entry["font"]=decode_define_font(t.payload)
  elif t.code in {48,75}:entry["font"]=decode_define_font2(t.payload,t.code)
  elif t.code in {11,33}:
   entry["bounds"],o=_rect(t.payload,2);entry["matrix"],o=_matrix(t.payload,o);entry["text"]=decode_text_records(t.payload,o,1 if t.code==11 else 2)
  elif t.code==37:entry["bounds"],_=_rect(t.payload,2)
  elif t.code==39 and len(t.payload)>=4:entry["frame_count"]=_u16(t.payload,2);entry["timeline"]=_sprite_timeline(t.payload[4:])
  out[cid]=entry
 return out
def _counts(data,off):
 r={2:"DefineShape",22:"DefineShape2",32:"DefineShape3",83:"DefineShape4",7:"DefineButton",34:"DefineButton2",10:"DefineFont",48:"DefineFont2",75:"DefineFont3",11:"DefineText",33:"DefineText2",37:"DefineEditText",39:"DefineSprite",4:"PlaceObject",26:"PlaceObject2",70:"PlaceObject3",5:"RemoveObject",28:"RemoveObject2"};c={v:0 for v in r.values()}
 for t in iter_tags(data,off):
  if t.code in r:c[r[t.code]]+=1
 return {k:v for k,v in c.items() if v}
def _trace(data,off,end):
 frame=1;out=[]
 for t in iter_tags(data,off):
  if frame>end:break
  if t.code==1:frame+=1;continue
  if t.code in {4,26}:e={"frame":frame,"tag":"PlaceObject" if t.code==4 else "PlaceObject2"};e.update(_place(t.code,t.payload));out.append(e)
  elif t.code==5 and len(t.payload)>=4:cid,d=struct.unpack_from("<HH",t.payload);out.append({"frame":frame,"tag":"RemoveObject","character_id":cid,"depth":d})
  elif t.code==28 and len(t.payload)>=2:out.append({"frame":frame,"tag":"RemoveObject2","depth":_u16(t.payload)})
  elif t.code==43:out.append({"frame":frame,"tag":"FrameLabel","label":_cstring(t.payload)})
 return out
def _state(trace,frame,defs):
 s={}
 for e in trace:
  if int(e["frame"])>frame:break
  tag=str(e["tag"])
  if tag.startswith("PlaceObject"):
   d=int(e["depth"]);prior=s.get(d,{}) if e.get("move") else {};item={**prior,**{k:v for k,v in e.items() if k not in {"frame","tag","move"}}};cid=item.get("character_id")
   if cid in defs:item["definition"]={k:v for k,v in defs[cid].items() if k not in {"timeline","shape","text","font","button"}}
   s[d]=item
  elif tag.startswith("RemoveObject"):s.pop(int(e["depth"]),None)
 return [s[d] for d in sorted(s)]
def extract(path):
 data,h=parse_header(path.read_bytes());frame=0;labels=[]
 for t in iter_tags(data,h.tags_offset):
  if t.code==1:frame+=1
  elif t.code==43:
   label=_cstring(t.payload)
   if label in OPENING_LABELS:labels.append({"label":label,"frame":frame+1})
 missing=sorted(OPENING_LABELS-{e["label"] for e in labels})
 if missing:raise ValueError(f"opening labels missing from SWF: {', '.join(missing)}")
 labels.sort(key=lambda e:int(e["frame"]));trace=_trace(data,h.tags_offset,max(int(e["frame"]) for e in labels));defs=_definitions(data,h.tags_offset);snaps=[{"frame":int(e["frame"]),"label":e["label"],"display_list":_state(trace,int(e["frame"]),defs)} for e in labels]
 return {"schema_version":14,"source":path.name,"stage":[h.width,h.height],"frame_rate":h.fps,"opening_labels":labels,"named_characters":_named(data,h.tags_offset),"character_definitions":{str(k):v for k,v in sorted(defs.items())},"title_relevant_tag_counts":_counts(data,h.tags_offset),"opening_display_trace":trace,"opening_display_snapshots":snaps,"notes":["Shape definitions expose original vector records.","Static text and font definitions expose original glyph layout and outlines.","DefineButton/DefineButton2 definitions expose original Up/Over/Down/HitTest display records and transforms.","Button ActionScript targets remain to be decoded before classic title rendering.","This file deliberately contains no workshop economy data."]}
def main():
 p=argparse.ArgumentParser();p.add_argument("swf",type=Path);p.add_argument("--out",type=Path);a=p.parse_args();s=json.dumps(extract(a.swf),indent=2,ensure_ascii=False)+"\n"
 if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(s,encoding="utf-8")
 else:print(s,end="")
 return 0
if __name__=="__main__":raise SystemExit(main())
