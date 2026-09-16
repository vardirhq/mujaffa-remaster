#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import struct
import zlib
from dataclasses import dataclass
from pathlib import Path


class SwfError(ValueError):
    pass


class BitReader:
    def __init__(self, data: bytes, bit: int = 0) -> None:
        self.data = data
        self.bit = bit

    def u(self, n: int) -> int:
        value = 0
        for _ in range(n):
            byte_index, bit_index = divmod(self.bit, 8)
            if byte_index >= len(self.data):
                raise SwfError("unexpected end of bit stream")
            value = (value << 1) | ((self.data[byte_index] >> (7 - bit_index)) & 1)
            self.bit += 1
        return value

    def s(self, n: int) -> int:
        if n <= 0:
            return 0
        value = self.u(n)
        sign = 1 << (n - 1)
        return value - (1 << n) if value & sign else value

    def align(self) -> None:
        self.bit = (self.bit + 7) // 8 * 8

    @property
    def off(self) -> int:
        return self.bit // 8


def parse_swf(path: Path) -> tuple[bytes, int]:
    raw = path.read_bytes()
    if len(raw) < 8:
        raise SwfError("file is too short to be an SWF")

    signature = raw[:3]
    declared = struct.unpack_from("<I", raw, 4)[0]
    if signature == b"FWS":
        data = raw
    elif signature == b"CWS":
        data = b"FWS" + raw[3:8] + zlib.decompress(raw[8:])
    else:
        raise SwfError(f"unsupported SWF signature {signature!r}")

    if len(data) != declared:
        raise SwfError("decoded SWF length does not match declared length")

    bits = BitReader(data, 8 * 8)
    nbits = bits.u(5)
    for _ in range(4):
        bits.s(nbits)
    bits.align()
    return data, bits.off + 4


def iter_tags(data: bytes, offset: int):
    cursor = offset
    while cursor + 2 <= len(data):
        record = struct.unpack_from("<H", data, cursor)[0]
        cursor += 2
        code = record >> 6
        length = record & 0x3F
        if length == 0x3F:
            length = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
        end = cursor + length
        if end > len(data):
            raise SwfError(f"tag {code} extends beyond end of file")
        yield code, data[cursor:end]
        cursor = end
        if code == 0:
            return


def read_rect(payload: bytes, offset: int = 0) -> tuple[int, list[int]]:
    bits = BitReader(payload, offset * 8)
    nbits = bits.u(5)
    values = [bits.s(nbits) for _ in range(4)]
    bits.align()
    return bits.off, values


def read_matrix(payload: bytes, offset: int) -> tuple[int, tuple[float, ...]]:
    bits = BitReader(payload, offset * 8)
    sx = sy = 1.0
    rotate_skew_0 = rotate_skew_1 = 0.0

    if bits.u(1):
        nbits = bits.u(5)
        sx = bits.s(nbits) / 65536.0
        sy = bits.s(nbits) / 65536.0
    if bits.u(1):
        nbits = bits.u(5)
        rotate_skew_0 = bits.s(nbits) / 65536.0
        rotate_skew_1 = bits.s(nbits) / 65536.0

    nbits = bits.u(5)
    tx = bits.s(nbits) / 20.0
    ty = bits.s(nbits) / 20.0
    bits.align()
    return bits.off, (sx, rotate_skew_1, rotate_skew_0, sy, tx, ty)


def read_color(payload: bytes, offset: int, alpha: bool):
    count = 4 if alpha else 3
    if offset + count > len(payload):
        raise SwfError("truncated colour")
    values = list(payload[offset : offset + count])
    if not alpha:
        values.append(255)
    return offset + count, tuple(values)


def color_css(rgba: tuple[int, int, int, int]) -> tuple[str, float]:
    red, green, blue, alpha = rgba
    return f"#{red:02x}{green:02x}{blue:02x}", alpha / 255.0


@dataclass
class Fill:
    kind: str
    color: tuple[int, int, int, int] | None = None
    gradient: list[tuple[float, tuple[int, int, int, int]]] | None = None
    matrix: tuple[float, ...] | None = None
    radial: bool = False


@dataclass
class Line:
    width: float
    color: tuple[int, int, int, int]


@dataclass
class Edge:
    start: tuple[float, float]
    control: tuple[float, float] | None
    end: tuple[float, float]


def read_fill_array(payload: bytes, offset: int, shape_version: int):
    count = payload[offset]
    offset += 1
    if count == 255:
        count = struct.unpack_from("<H", payload, offset)[0]
        offset += 2

    fills: list[Fill] = []
    alpha = shape_version >= 3
    for _ in range(count):
        fill_type = payload[offset]
        offset += 1
        if fill_type == 0:
            offset, color = read_color(payload, offset, alpha)
            fills.append(Fill("solid", color=color))
        elif fill_type in (0x10, 0x12, 0x13):
            offset, matrix = read_matrix(payload, offset)
            flags_and_count = payload[offset]
            offset += 1
            stop_count = flags_and_count & 0x0F
            stops = []
            for _ in range(stop_count):
                ratio = payload[offset]
                offset += 1
                offset, color = read_color(payload, offset, alpha)
                stops.append((ratio / 255.0, color))
            if fill_type == 0x13:
                offset += 2  # focal point
            fills.append(
                Fill(
                    "gradient",
                    gradient=stops,
                    matrix=matrix,
                    radial=fill_type != 0x10,
                )
            )
        elif fill_type in (0x40, 0x41, 0x42, 0x43):
            bitmap_id = struct.unpack_from("<H", payload, offset)[0]
            raise SwfError(
                f"bitmap fill {fill_type:#x} references character {bitmap_id}; "
                "Mujaffa reference unexpectedly changed"
            )
        else:
            raise SwfError(f"unsupported fill style {fill_type:#x}")
    return offset, fills


def read_line_array(payload: bytes, offset: int, shape_version: int):
    count = payload[offset]
    offset += 1
    if count == 255:
        count = struct.unpack_from("<H", payload, offset)[0]
        offset += 2

    alpha = shape_version >= 3
    lines: list[Line] = []
    for _ in range(count):
        width = struct.unpack_from("<H", payload, offset)[0] / 20.0
        offset += 2
        offset, color = read_color(payload, offset, alpha)
        lines.append(Line(width, color))
    return offset, lines


def parse_shape(code: int, payload: bytes):
    shape_version = {2: 1, 22: 2, 32: 3}[code]
    character_id = struct.unpack_from("<H", payload, 0)[0]
    offset, bounds_twips = read_rect(payload, 2)
    bounds = tuple(value / 20.0 for value in bounds_twips)

    offset, fills = read_fill_array(payload, offset, shape_version)
    offset, lines = read_line_array(payload, offset, shape_version)

    bits = BitReader(payload, offset * 8)
    fill_bits = bits.u(4)
    line_bits = bits.u(4)
    x = y = 0
    fill0 = fill1 = line = 0
    # A style-change record carrying new styles *replaces* the style arrays, and
    # every index after it is 1-based into the replacement rather than into
    # everything defined so far. Appending and indexing from the front instead
    # is why a multi-part character used to come out wearing the colours of
    # whatever was drawn before its last style reset.
    fill_base = line_base = 0
    fill_edges: dict[int, list[Edge]] = {}
    line_edges: dict[int, list[Edge]] = {}

    while True:
        if bits.u(1):
            straight = bits.u(1)
            nbits = bits.u(4) + 2
            start = (x / 20.0, y / 20.0)
            if straight:
                if bits.u(1):
                    dx, dy = bits.s(nbits), bits.s(nbits)
                elif bits.u(1):
                    dx, dy = 0, bits.s(nbits)
                else:
                    dx, dy = bits.s(nbits), 0
                x += dx
                y += dy
                edge = Edge(start, None, (x / 20.0, y / 20.0))
            else:
                control_dx, control_dy = bits.s(nbits), bits.s(nbits)
                anchor_dx, anchor_dy = bits.s(nbits), bits.s(nbits)
                control_x, control_y = x + control_dx, y + control_dy
                x, y = control_x + anchor_dx, control_y + anchor_dy
                edge = Edge(
                    start,
                    (control_x / 20.0, control_y / 20.0),
                    (x / 20.0, y / 20.0),
                )

            if fill1:
                fill_edges.setdefault(fill_base + fill1, []).append(edge)
            if fill0:
                fill_edges.setdefault(fill_base + fill0, []).append(
                    Edge(edge.end, edge.control, edge.start)
                )
            if line:
                line_edges.setdefault(line_base + line, []).append(edge)
            continue

        flags = bits.u(5)
        if flags == 0:
            break
        if flags & 1:
            nbits = bits.u(5)
            x, y = bits.s(nbits), bits.s(nbits)
        if flags & 2:
            fill0 = bits.u(fill_bits)
        if flags & 4:
            fill1 = bits.u(fill_bits)
        if flags & 8:
            line = bits.u(line_bits)
        if flags & 16:
            bits.align()
            offset = bits.off
            offset, new_fills = read_fill_array(payload, offset, shape_version)
            offset, new_lines = read_line_array(payload, offset, shape_version)
            fill_base, line_base = len(fills), len(lines)
            fills.extend(new_fills)
            lines.extend(new_lines)
            bits = BitReader(payload, offset * 8)
            fill_bits = bits.u(4)
            line_bits = bits.u(4)

    return character_id, bounds, fills, lines, fill_edges, line_edges


def point_key(point: tuple[float, float]):
    return round(point[0], 5), round(point[1], 5)


def chain_edges(edges: list[Edge]) -> list[list[Edge]]:
    unused = list(edges)
    paths: list[list[Edge]] = []
    while unused:
        path = [unused.pop(0)]
        while unused:
            end = point_key(path[-1].end)
            found = next((i for i, edge in enumerate(unused) if point_key(edge.start) == end), None)
            if found is None:
                break
            path.append(unused.pop(found))
            if point_key(path[-1].end) == point_key(path[0].start):
                break
        paths.append(path)
    return paths


def edge_path(chain: list[Edge]) -> str:
    if not chain:
        return ""
    start = chain[0].start
    commands = [f"M {start[0]:.4f} {start[1]:.4f}"]
    for edge in chain:
        if edge.control is None:
            commands.append(f"L {edge.end[0]:.4f} {edge.end[1]:.4f}")
        else:
            commands.append(
                f"Q {edge.control[0]:.4f} {edge.control[1]:.4f} "
                f"{edge.end[0]:.4f} {edge.end[1]:.4f}"
            )
    if point_key(chain[-1].end) == point_key(chain[0].start):
        commands.append("Z")
    return " ".join(commands)


def svg_for_shape(bounds, fills, lines, fill_edges, line_edges, padding: float = 2.0):
    xmin, xmax, ymin, ymax = bounds
    width = max(0.05, xmax - xmin)
    height = max(0.05, ymax - ymin)
    defs: list[str] = []
    body: list[str] = []

    for index, edges in fill_edges.items():
        if not 1 <= index <= len(fills):
            continue
        fill = fills[index - 1]
        path = " ".join(edge_path(chain) for chain in chain_edges(edges))
        if not path:
            continue

        if fill.kind == "solid":
            color, opacity = color_css(fill.color)
            body.append(
                f'<path d="{path}" fill="{color}" fill-opacity="{opacity:.5f}" '
                'fill-rule="evenodd" stroke="none"/>'
            )
            continue

        gradient_id = f"g{index}"
        a, b, c, d, tx, ty = fill.matrix
        transform = f"matrix({a:.8g} {b:.8g} {c:.8g} {d:.8g} {tx:.8g} {ty:.8g})"
        if fill.radial:
            gradient = (
                f'<radialGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" '
                f'cx="0" cy="0" r="819.2" gradientTransform="{transform}">'
            )
            end_tag = "</radialGradient>"
        else:
            gradient = (
                f'<linearGradient id="{gradient_id}" gradientUnits="userSpaceOnUse" '
                f'x1="-819.2" y1="0" x2="819.2" y2="0" gradientTransform="{transform}">'
            )
            end_tag = "</linearGradient>"
        for ratio, rgba in fill.gradient:
            color, opacity = color_css(rgba)
            gradient += (
                f'<stop offset="{ratio:.6f}" stop-color="{color}" '
                f'stop-opacity="{opacity:.5f}"/>'
            )
        defs.append(gradient + end_tag)
        body.append(
            f'<path d="{path}" fill="url(#{gradient_id})" '
            'fill-rule="evenodd" stroke="none"/>'
        )

    for index, edges in line_edges.items():
        if not 1 <= index <= len(lines):
            continue
        line = lines[index - 1]
        color, opacity = color_css(line.color)
        for chain in chain_edges(edges):
            body.append(
                f'<path d="{edge_path(chain)}" fill="none" stroke="{color}" '
                f'stroke-opacity="{opacity:.5f}" stroke-width="{line.width:.4f}" '
                'stroke-linecap="round" stroke-linejoin="round"/>'
            )

    view_box = (
        xmin - padding,
        ymin - padding,
        width + padding * 2.0,
        height + padding * 2.0,
    )
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{view_box[0]:.4f} {view_box[1]:.4f} {view_box[2]:.4f} {view_box[3]:.4f}">'
        f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>'
    )
    return svg, width, height


def extract(swf: Path, output: Path, scale: float, max_size: int) -> dict[str, object]:
    try:
        import cairosvg
    except ImportError:
        cairosvg = None

    data, offset = parse_swf(swf)
    svg_dir = output / "svg"
    png_dir = output / "png"
    svg_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)

    items = []
    for code, payload in iter_tags(data, offset):
        if code not in (2, 22, 32):
            continue

        character_id, bounds, fills, lines, fill_edges, line_edges = parse_shape(code, payload)
        svg, width, height = svg_for_shape(bounds, fills, lines, fill_edges, line_edges)
        svg_path = svg_dir / f"shape-{character_id:04d}.svg"
        png_path = png_dir / f"shape-{character_id:04d}.png"
        svg_path.write_text(svg, encoding="utf-8")

        output_width = max(1, min(max_size, math.ceil((width + 4.0) * scale)))
        output_height = max(1, min(max_size, math.ceil((height + 4.0) * scale)))
        png_relative = None
        if cairosvg is not None:
            cairosvg.svg2png(
                bytestring=svg.encode("utf-8"),
                write_to=str(png_path),
                output_width=output_width,
                output_height=output_height,
            )
            png_relative = str(png_path.relative_to(output))

        items.append(
            {
                "character_id": character_id,
                "tag": code,
                "bounds": bounds,
                "fills": len(fills),
                "lines": len(lines),
                "width": output_width,
                "height": output_height,
                "svg": str(svg_path.relative_to(output)),
                "png": png_relative,
            }
        )

    manifest = {
        "source": swf.name,
        "shape_count": len(items),
        "scale": scale,
        "max_size": max_size,
        "items": items,
    }
    (output / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--max-size", type=int, default=2048)
    args = parser.parse_args()

    manifest = extract(args.swf, args.output, args.scale, args.max_size)
    print(f"extracted {manifest['shape_count']} vector shapes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
