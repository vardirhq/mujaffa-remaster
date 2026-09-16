"""Decode classic SWF font definitions and glyph outlines."""
from __future__ import annotations

import struct

from swf_inventory import BitReader, SwfError


def _glyph_shape(payload: bytes, start: int, end: int) -> list[dict[str, object]]:
    bits = BitReader(payload, start)
    fill_bits = bits.read_unsigned(4)
    line_bits = bits.read_unsigned(4)
    records: list[dict[str, object]] = []
    x = y = 0
    while bits.bit < end * 8:
        if bits.read_unsigned(1):
            straight = bool(bits.read_unsigned(1))
            n = bits.read_unsigned(4) + 2
            if straight:
                general = bool(bits.read_unsigned(1));dx=dy=0
                if general:dx,dy=bits.read_signed(n),bits.read_signed(n)
                elif bits.read_unsigned(1):dy=bits.read_signed(n)
                else:dx=bits.read_signed(n)
                x+=dx;y+=dy;records.append({"type":"line","to":[x/20.,y/20.]})
            else:
                cdx,cdy=bits.read_signed(n),bits.read_signed(n);adx,ady=bits.read_signed(n),bits.read_signed(n);cx,cy=x+cdx,y+cdy;x,y=cx+adx,cy+ady;records.append({"type":"curve","control":[cx/20.,cy/20.],"to":[x/20.,y/20.]})
            continue
        flags=bits.read_unsigned(5)
        if flags==0:break
        change={"type":"style"}
        if flags&1:
            n=bits.read_unsigned(5);x,y=bits.read_signed(n),bits.read_signed(n);change["move_to"]=[x/20.,y/20.]
        if flags&2:change["fill_0"]=bits.read_unsigned(fill_bits)
        if flags&4:change["fill_1"]=bits.read_unsigned(fill_bits)
        if flags&8:change["line"]=bits.read_unsigned(line_bits)
        if flags&16:raise SwfError("font glyph unexpectedly introduces new styles")
        records.append(change)
    return records


def decode_define_font(payload: bytes) -> dict[str, object]:
    """Decode DefineFont (tag 10), whose glyph count is implied by offset table size."""
    if len(payload)<4:raise SwfError("truncated DefineFont")
    first=struct.unpack_from("<H",payload,2)[0]
    if first%2:raise SwfError("invalid DefineFont offset table")
    count=first//2
    if 2+count*2>len(payload):raise SwfError("truncated DefineFont offsets")
    offsets=[struct.unpack_from("<H",payload,2+i*2)[0] for i in range(count)]
    base=2
    glyphs=[]
    for i,rel in enumerate(offsets):
        start=base+rel;end=base+(offsets[i+1] if i+1<count else len(payload)-base)
        if not start<=end<=len(payload):raise SwfError("invalid DefineFont glyph range")
        glyphs.append({"index":i,"shape_records":_glyph_shape(payload,start,end)})
    return {"glyphs":glyphs}


def decode_define_font2(payload: bytes, tag_code: int) -> dict[str, object]:
    """Decode DefineFont2/3 metadata, code table, offsets and glyph outlines."""
    if len(payload)<8:raise SwfError("truncated DefineFont2/3")
    flags=payload[2];wide_offsets=bool(flags&0x08);wide_codes=bool(flags&0x04);has_layout=bool(flags&0x80)
    name_len=payload[4];o=5
    if o+name_len+2>len(payload):raise SwfError("truncated font name")
    name=payload[o:o+name_len].decode("latin-1",errors="replace");o+=name_len
    count=struct.unpack_from("<H",payload,o)[0];o+=2
    entry_size=4 if wide_offsets else 2
    table_start=o
    need=(count+1)*entry_size
    if o+need>len(payload):raise SwfError("truncated font offset table")
    fmt="<I" if wide_offsets else "<H"
    offsets=[struct.unpack_from(fmt,payload,o+i*entry_size)[0] for i in range(count)]
    code_rel=struct.unpack_from(fmt,payload,o+count*entry_size)[0]
    glyph_base=table_start
    code_offset=glyph_base+code_rel
    if code_offset>len(payload):raise SwfError("invalid font code table offset")
    glyphs=[]
    for i,rel in enumerate(offsets):
        start=glyph_base+rel;end=glyph_base+(offsets[i+1] if i+1<count else code_rel)
        if not start<=end<=code_offset:raise SwfError("invalid font glyph range")
        glyphs.append({"index":i,"shape_records":_glyph_shape(payload,start,end)})
    code_size=2 if wide_codes else 1
    if code_offset+count*code_size>len(payload):raise SwfError("truncated font code table")
    for i in range(count):
        code=struct.unpack_from("<H",payload,code_offset+i*2)[0] if wide_codes else payload[code_offset+i]
        glyphs[i]["code"]=code
        try:glyphs[i]["character"]=chr(code)
        except ValueError:pass
    result={"name":name,"bold":bool(flags&1),"italic":bool(flags&2),"ansi":bool(flags&0x10),"unicode":bool(flags&0x20),"shift_jis":bool(flags&0x40),"has_layout":has_layout,"units_per_em":20480 if tag_code==75 else 1024,"glyphs":glyphs}
    if has_layout:
        # Ascent, descent and leading are what an EditText needs to put its first
        # baseline where Flash put it; a static DefineText carries its own
        # offsets and never asks. They are in EM units, like the glyphs.
        o=code_offset+count*code_size
        if o+6>len(payload):raise SwfError("truncated font layout")
        result["ascent"],result["descent"],result["leading"]=struct.unpack_from("<HHh",payload,o)
        o+=6
        if o+count*2<=len(payload):
            result["advances"]=[struct.unpack_from("<h",payload,o+i*2)[0] for i in range(count)]
    return result
