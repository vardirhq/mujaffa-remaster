"""Decode SWF vector shape records into renderer-neutral source evidence."""
from __future__ import annotations

import struct

from swf_inventory import BitReader, SwfError


def _rgba(payload: bytes, offset: int, alpha: bool) -> tuple[int, dict[str, int]]:
    count = 4 if alpha else 3
    if offset + count > len(payload):
        raise SwfError("truncated colour")
    values = list(payload[offset:offset + count])
    offset += count
    if not alpha:
        values.append(255)
    return offset, dict(zip("rgba", values))


def _matrix(payload: bytes, offset: int) -> tuple[int, dict[str, float]]:
    bits = BitReader(payload, offset)
    sx = sy = 1.0
    r0 = r1 = 0.0
    if bits.read_unsigned(1):
        n = bits.read_unsigned(5)
        sx, sy = bits.read_signed(n) / 65536.0, bits.read_signed(n) / 65536.0
    if bits.read_unsigned(1):
        n = bits.read_unsigned(5)
        r0, r1 = bits.read_signed(n) / 65536.0, bits.read_signed(n) / 65536.0
    n = bits.read_unsigned(5)
    tx = bits.read_signed(n) / 20.0 if n else 0.0
    ty = bits.read_signed(n) / 20.0 if n else 0.0
    return bits.byte_offset, {
        "scale_x": sx,
        "scale_y": sy,
        "rotate_skew_0": r0,
        "rotate_skew_1": r1,
        "translate_x": tx,
        "translate_y": ty,
    }


def _fill(payload: bytes, offset: int, shape_version: int) -> tuple[int, dict[str, object]]:
    if offset >= len(payload):
        raise SwfError("truncated fill style")
    kind = payload[offset]
    offset += 1
    alpha = shape_version >= 3
    if kind == 0:
        offset, color = _rgba(payload, offset, alpha)
        return offset, {"type": "solid", "color": color}
    if kind in {0x10, 0x12, 0x13}:
        offset, matrix = _matrix(payload, offset)
        if offset >= len(payload):
            raise SwfError("truncated gradient")
        flags_and_count = payload[offset]
        offset += 1
        spread = (flags_and_count >> 6) & 0x03 if shape_version >= 4 else 0
        interpolation = (flags_and_count >> 4) & 0x03 if shape_version >= 4 else 0
        count = flags_and_count & 0x0F
        stops = []
        for _ in range(count):
            if offset >= len(payload):
                raise SwfError("truncated gradient stop")
            ratio = payload[offset]
            offset += 1
            offset, color = _rgba(payload, offset, alpha)
            stops.append({"ratio": ratio, "color": color})
        result = {
            "type": {0x10: "linear_gradient", 0x12: "radial_gradient", 0x13: "focal_gradient"}[kind],
            "matrix": matrix,
            "stops": stops,
            "spread": spread,
            "interpolation": interpolation,
        }
        if kind == 0x13:
            if offset + 2 > len(payload):
                raise SwfError("truncated focal point")
            result["focal_point"] = struct.unpack_from("<h", payload, offset)[0] / 256.0
            offset += 2
        return offset, result
    if kind in {0x40, 0x41, 0x42, 0x43}:
        if offset + 2 > len(payload):
            raise SwfError("truncated bitmap fill")
        bitmap_id = struct.unpack_from("<H", payload, offset)[0]
        offset += 2
        offset, matrix = _matrix(payload, offset)
        return offset, {
            "type": "bitmap",
            "bitmap_id": bitmap_id,
            "matrix": matrix,
            "repeat": kind in {0x40, 0x42},
            "smooth": kind in {0x40, 0x41},
        }
    raise SwfError(f"unsupported fill style 0x{kind:02x}")


def _fill_array(payload: bytes, offset: int, shape_version: int) -> tuple[int, list[dict[str, object]]]:
    if offset >= len(payload):
        raise SwfError("truncated fill array")
    count = payload[offset]
    offset += 1
    if count == 0xFF:
        if offset + 2 > len(payload):
            raise SwfError("truncated extended fill count")
        count = struct.unpack_from("<H", payload, offset)[0]
        offset += 2
    fills = []
    for _ in range(count):
        offset, fill = _fill(payload, offset, shape_version)
        fills.append(fill)
    return offset, fills


def _line_array(payload: bytes, offset: int, shape_version: int) -> tuple[int, list[dict[str, object]]]:
    if offset >= len(payload):
        raise SwfError("truncated line array")
    count = payload[offset]
    offset += 1
    if count == 0xFF:
        if offset + 2 > len(payload):
            raise SwfError("truncated extended line count")
        count = struct.unpack_from("<H", payload, offset)[0]
        offset += 2
    lines = []
    for _ in range(count):
        if offset + 2 > len(payload):
            raise SwfError("truncated line style")
        width = struct.unpack_from("<H", payload, offset)[0] / 20.0
        offset += 2
        if shape_version < 4:
            offset, color = _rgba(payload, offset, shape_version >= 3)
            lines.append({"width": width, "color": color})
            continue
        bits = BitReader(payload, offset)
        start_cap = bits.read_unsigned(2)
        join = bits.read_unsigned(2)
        has_fill = bool(bits.read_unsigned(1))
        no_h = bool(bits.read_unsigned(1))
        no_v = bool(bits.read_unsigned(1))
        pixel_hint = bool(bits.read_unsigned(1))
        bits.read_unsigned(5)
        no_close = bool(bits.read_unsigned(1))
        end_cap = bits.read_unsigned(2)
        offset = bits.byte_offset
        line = {
            "width": width,
            "start_cap": start_cap,
            "join": join,
            "no_h_scale": no_h,
            "no_v_scale": no_v,
            "pixel_hinting": pixel_hint,
            "no_close": no_close,
            "end_cap": end_cap,
        }
        if join == 2:
            if offset + 2 > len(payload):
                raise SwfError("truncated miter limit")
            line["miter_limit"] = struct.unpack_from("<H", payload, offset)[0] / 256.0
            offset += 2
        if has_fill:
            offset, line["fill"] = _fill(payload, offset, shape_version)
        else:
            offset, line["color"] = _rgba(payload, offset, True)
        lines.append(line)
    return offset, lines


def decode_shape_records(payload: bytes, offset: int, shape_version: int) -> dict[str, object]:
    offset, fills = _fill_array(payload, offset, shape_version)
    offset, lines = _line_array(payload, offset, shape_version)
    bits = BitReader(payload, offset)
    fill_bits, line_bits = bits.read_unsigned(4), bits.read_unsigned(4)
    records = []
    x = y = 0
    while True:
        if bits.read_unsigned(1):
            straight = bool(bits.read_unsigned(1))
            n = bits.read_unsigned(4) + 2
            if straight:
                general = bool(bits.read_unsigned(1))
                dx = dy = 0
                if general:
                    dx, dy = bits.read_signed(n), bits.read_signed(n)
                elif bits.read_unsigned(1):
                    dy = bits.read_signed(n)
                else:
                    dx = bits.read_signed(n)
                x += dx
                y += dy
                records.append({"type": "line", "to": [x / 20.0, y / 20.0]})
            else:
                cdx, cdy = bits.read_signed(n), bits.read_signed(n)
                adx, ady = bits.read_signed(n), bits.read_signed(n)
                cx, cy = x + cdx, y + cdy
                x, y = cx + adx, cy + ady
                records.append({"type": "curve", "control": [cx / 20.0, cy / 20.0], "to": [x / 20.0, y / 20.0]})
            continue
        flags = bits.read_unsigned(5)
        if flags == 0:
            break
        change = {"type": "style"}
        if flags & 1:
            n = bits.read_unsigned(5)
            x, y = bits.read_signed(n), bits.read_signed(n)
            change["move_to"] = [x / 20.0, y / 20.0]
        if flags & 2:
            change["fill_0"] = bits.read_unsigned(fill_bits)
        if flags & 4:
            change["fill_1"] = bits.read_unsigned(fill_bits)
        if flags & 8:
            change["line"] = bits.read_unsigned(line_bits)
        if flags & 16:
            offset = bits.byte_offset
            offset, new_fills = _fill_array(payload, offset, shape_version)
            offset, new_lines = _line_array(payload, offset, shape_version)
            fills.extend(new_fills)
            lines.extend(new_lines)
            change["new_fills"] = new_fills
            change["new_lines"] = new_lines
            bits = BitReader(payload, offset)
            fill_bits, line_bits = bits.read_unsigned(4), bits.read_unsigned(4)
        records.append(change)
    return {"fills": fills, "lines": lines, "records": records}
