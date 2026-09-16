"""Decode SWF vector shape records into renderer-neutral source evidence."""
from __future__ import annotations

from swf_inventory import BitReader, SwfError


def _align(bits: BitReader) -> None:
    """SWF style arrays following StateNewStyles restart on a byte boundary."""
    bits.bit = (bits.bit + 7) & ~7


def _rgba(bits: BitReader, alpha: bool) -> dict[str, int]:
    color = {"r": bits.read_unsigned(8), "g": bits.read_unsigned(8), "b": bits.read_unsigned(8)}
    color["a"] = bits.read_unsigned(8) if alpha else 255
    return color


def _matrix(bits: BitReader) -> dict[str, float]:
    sx = sy = 1.0
    r0 = r1 = 0.0
    if bits.read_unsigned(1):
        n = bits.read_unsigned(5); sx, sy = bits.read_signed(n) / 65536.0, bits.read_signed(n) / 65536.0
    if bits.read_unsigned(1):
        n = bits.read_unsigned(5); r0, r1 = bits.read_signed(n) / 65536.0, bits.read_signed(n) / 65536.0
    n = bits.read_unsigned(5); tx = bits.read_signed(n) / 20.0 if n else 0.0; ty = bits.read_signed(n) / 20.0 if n else 0.0
    return {"scale_x": sx,"scale_y": sy,"rotate_skew_0": r0,"rotate_skew_1": r1,"translate_x": tx,"translate_y": ty}


def _fill(bits: BitReader, shape_version: int) -> dict[str, object]:
    kind=bits.read_unsigned(8); alpha=shape_version>=3
    if kind==0:return {"type":"solid","color":_rgba(bits,alpha)}
    if kind in {0x10,0x12,0x13}:
        matrix=_matrix(bits);spread=interpolation=0
        if shape_version>=4:spread,interpolation=bits.read_unsigned(2),bits.read_unsigned(2)
        else:bits.read_unsigned(4)
        count=bits.read_unsigned(4);stops=[{"ratio":bits.read_unsigned(8),"color":_rgba(bits,alpha)} for _ in range(count)]
        result={"type":{0x10:"linear_gradient",0x12:"radial_gradient",0x13:"focal_gradient"}[kind],"matrix":matrix,"stops":stops,"spread":spread,"interpolation":interpolation}
        if kind==0x13:result["focal_point"]=bits.read_signed(16)/256.0
        return result
    if kind in {0x40,0x41,0x42,0x43}:return {"type":"bitmap","bitmap_id":bits.read_unsigned(16),"matrix":_matrix(bits),"repeat":kind in {0x40,0x42},"smooth":kind in {0x40,0x41}}
    raise SwfError(f"unsupported fill style 0x{kind:02x}")


def _fill_array(bits: BitReader, shape_version: int) -> list[dict[str, object]]:
    count=bits.read_unsigned(8)
    if count==0xFF and shape_version>=2:count=bits.read_unsigned(16)
    return [_fill(bits,shape_version) for _ in range(count)]


def _line_array(bits: BitReader, shape_version: int) -> list[dict[str, object]]:
    count=bits.read_unsigned(8)
    if count==0xFF and shape_version>=2:count=bits.read_unsigned(16)
    lines=[]
    for _ in range(count):
        width=bits.read_unsigned(16)/20.0
        if shape_version<4:lines.append({"width":width,"color":_rgba(bits,shape_version>=3)});continue
        start_cap=bits.read_unsigned(2);join=bits.read_unsigned(2);has_fill=bool(bits.read_unsigned(1));no_h=bool(bits.read_unsigned(1));no_v=bool(bits.read_unsigned(1));pixel_hint=bool(bits.read_unsigned(1));bits.read_unsigned(5);no_close=bool(bits.read_unsigned(1));end_cap=bits.read_unsigned(2)
        line={"width":width,"start_cap":start_cap,"join":join,"no_h_scale":no_h,"no_v_scale":no_v,"pixel_hinting":pixel_hint,"no_close":no_close,"end_cap":end_cap}
        if join==2:line["miter_limit"]=bits.read_unsigned(16)/256.0
        if has_fill:line["fill"]=_fill(bits,shape_version)
        else:line["color"]=_rgba(bits,True)
        lines.append(line)
    return lines


def decode_shape_records(payload: bytes, offset: int, shape_version: int) -> dict[str, object]:
    bits=BitReader(payload,offset);fills=_fill_array(bits,shape_version);lines=_line_array(bits,shape_version);fill_bits,line_bits=bits.read_unsigned(4),bits.read_unsigned(4);records=[];x=y=0
    while True:
        if bits.read_unsigned(1):
            straight=bool(bits.read_unsigned(1));n=bits.read_unsigned(4)+2
            if straight:
                general=bool(bits.read_unsigned(1));dx=dy=0
                if general:dx,dy=bits.read_signed(n),bits.read_signed(n)
                elif bits.read_unsigned(1):dy=bits.read_signed(n)
                else:dx=bits.read_signed(n)
                x+=dx;y+=dy;records.append({"type":"line","to":[x/20.0,y/20.0]})
            else:
                cdx,cdy=bits.read_signed(n),bits.read_signed(n);adx,ady=bits.read_signed(n),bits.read_signed(n);cx,cy=x+cdx,y+cdy;x,y=cx+adx,cy+ady;records.append({"type":"curve","control":[cx/20.0,cy/20.0],"to":[x/20.0,y/20.0]})
            continue
        flags=bits.read_unsigned(5)
        if flags==0:break
        change={"type":"style"}
        if flags&1:n=bits.read_unsigned(5);x,y=bits.read_signed(n),bits.read_signed(n);change["move_to"]=[x/20.0,y/20.0]
        if flags&2:change["fill_0"]=bits.read_unsigned(fill_bits)
        if flags&4:change["fill_1"]=bits.read_unsigned(fill_bits)
        if flags&8:change["line"]=bits.read_unsigned(line_bits)
        if flags&16:
            _align(bits);change["new_fills"]=_fill_array(bits,shape_version);change["new_lines"]=_line_array(bits,shape_version);fill_bits,line_bits=bits.read_unsigned(4),bits.read_unsigned(4)
        records.append(change)
    return {"fills":fills,"lines":lines,"records":records}
