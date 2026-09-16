"""Decode DefineButton/DefineButton2 visual state records."""
from __future__ import annotations
import struct
from swf_inventory import BitReader,SwfError

def _matrix(p,o):
 b=BitReader(p,o);sx=sy=1.;r0=r1=0.
 if b.read_unsigned(1):n=b.read_unsigned(5);sx,sy=b.read_signed(n)/65536.,b.read_signed(n)/65536.
 if b.read_unsigned(1):n=b.read_unsigned(5);r0,r1=b.read_signed(n)/65536.,b.read_signed(n)/65536.
 n=b.read_unsigned(5);tx=b.read_signed(n)/20. if n else 0.;ty=b.read_signed(n)/20. if n else 0.
 return {"scale_x":sx,"scale_y":sy,"rotate_skew_0":r0,"rotate_skew_1":r1,"translate_x":tx,"translate_y":ty},b.byte_offset

def _cxform(p,o,alpha=True):
 b=BitReader(p,o);ha=bool(b.read_unsigned(1));hm=bool(b.read_unsigned(1));n=b.read_unsigned(4);count=4 if alpha else 3;m=[256]*count;a=[0]*count
 if hm:m=[b.read_signed(n) for _ in range(count)]
 if ha:a=[b.read_signed(n) for _ in range(count)]
 keys="rgba"[:count];return {"multiply":dict(zip(keys,[v/256. for v in m])),"add":dict(zip(keys,a))},b.byte_offset

def _records(p,o,version):
 records=[]
 while True:
  if o>=len(p):raise SwfError("unterminated button records")
  flags=p[o];o+=1
  if flags==0:break
  if version==1:state=flags&0x0f
  else:state=flags&0x0f
  if o+4>len(p):raise SwfError("truncated button record")
  cid,depth=struct.unpack_from("<HH",p,o);o+=4;matrix,o=_matrix(p,o)
  rec={"character_id":cid,"depth":depth,"states":{"up":bool(state&1),"over":bool(state&2),"down":bool(state&4),"hit_test":bool(state&8)},"matrix":matrix}
  if version==2:
   rec["color_transform"],o=_cxform(p,o,True)
   if flags&0x10:
    if o>=len(p):raise SwfError("truncated button filter list")
    # Filters are not required for this SWF's classic title evidence yet. Preserve presence explicitly.
    raise SwfError("button filter list is not supported yet")
   if flags&0x20:
    if o+2>len(p):raise SwfError("truncated button blend mode")
    rec["blend_mode"]=p[o];o+=1
  records.append(rec)
 return o,records

def decode_button(payload:bytes,tag_code:int)->dict[str,object]:
 if len(payload)<2:raise SwfError("truncated button")
 if tag_code==7:
  _,records=_records(payload,2,1);return {"track_as_menu":False,"records":records,"has_actions":True}
 if tag_code!=34:raise SwfError(f"unsupported button tag {tag_code}")
 if len(payload)<5:raise SwfError("truncated DefineButton2")
 flags=payload[2];action_offset=struct.unpack_from("<H",payload,3)[0];records_end,records=_records(payload,5,2)
 action_start=3+action_offset if action_offset else None
 return {"track_as_menu":bool(flags&1),"records":records,"has_actions":bool(action_offset),"action_offset":action_start,"records_end":records_end}
