"""Decode DefineText/DefineText2 records into renderer-neutral source evidence."""
from __future__ import annotations

import struct

from swf_inventory import BitReader, SwfError


def _color(payload: bytes, offset: int, alpha: bool) -> tuple[int, dict[str, int]]:
    count = 4 if alpha else 3
    if offset + count > len(payload):
        raise SwfError("truncated text colour")
    values = list(payload[offset:offset + count])
    offset += count
    if not alpha:
        values.append(255)
    return offset, dict(zip("rgba", values))


def decode_text_records(payload: bytes, offset: int, text_version: int) -> dict[str, object]:
    """Decode the TEXTRECORD array after bounds and matrix."""
    if offset + 2 > len(payload):
        raise SwfError("truncated text header")
    glyph_bits = payload[offset]
    advance_bits = payload[offset + 1]
    offset += 2
    records: list[dict[str, object]] = []

    while True:
        if offset >= len(payload):
            raise SwfError("unterminated text records")
        flags = payload[offset]
        offset += 1
        if flags == 0:
            break
        if not flags & 0x80:
            raise SwfError(f"invalid text record flags 0x{flags:02x}")

        has_font = bool(flags & 0x08)
        has_color = bool(flags & 0x04)
        has_y = bool(flags & 0x02)
        has_x = bool(flags & 0x01)
        record: dict[str, object] = {}

        if has_font:
            if offset + 2 > len(payload):
                raise SwfError("truncated text font id")
            record["font_id"] = struct.unpack_from("<H", payload, offset)[0]
            offset += 2
        if has_color:
            offset, record["color"] = _color(payload, offset, text_version >= 2)
        if has_x:
            if offset + 2 > len(payload):
                raise SwfError("truncated text x offset")
            record["x_offset"] = struct.unpack_from("<h", payload, offset)[0] / 20.0
            offset += 2
        if has_y:
            if offset + 2 > len(payload):
                raise SwfError("truncated text y offset")
            record["y_offset"] = struct.unpack_from("<h", payload, offset)[0] / 20.0
            offset += 2
        if has_font:
            if offset + 2 > len(payload):
                raise SwfError("truncated text height")
            record["height"] = struct.unpack_from("<H", payload, offset)[0] / 20.0
            offset += 2

        if offset >= len(payload):
            raise SwfError("truncated glyph count")
        glyph_count = payload[offset]
        offset += 1
        bits = BitReader(payload, offset)
        glyphs = []
        for _ in range(glyph_count):
            glyphs.append({
                "index": bits.read_unsigned(glyph_bits),
                "advance": bits.read_signed(advance_bits) / 20.0,
            })
        offset = bits.byte_offset
        record["glyphs"] = glyphs
        records.append(record)

    return {"glyph_bits": glyph_bits, "advance_bits": advance_bits, "records": records}
