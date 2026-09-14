#!/usr/bin/env python3
"""Corrected Mujaffa SWF vector extractor.

The legacy extractor appended StateNewStyles fill/line arrays but kept treating
subsequent style indices as if they still started at the original array.  In
DefineShape2/3 the indices after StateNewStyles are relative to the newly added
style block.  Complex artwork such as Mujaffa character shape 21 therefore
collapsed all 167 fill blocks onto fill #1 and looked like pale line art.

Keep the original extractor as the shared implementation and replace only the
shape-record parser here so the fix stays small and easy to audit.
"""
from __future__ import annotations

import argparse
import struct
from pathlib import Path

import swf_art_extract as base


def parse_shape(code: int, payload: bytes):
    shape_version = {2: 1, 22: 2, 32: 3}[code]
    character_id = struct.unpack_from("<H", payload, 0)[0]
    offset, bounds_twips = base.read_rect(payload, 2)
    bounds = tuple(value / 20.0 for value in bounds_twips)

    offset, fills = base.read_fill_array(payload, offset, shape_version)
    offset, lines = base.read_line_array(payload, offset, shape_version)

    bits = base.BitReader(payload, offset * 8)
    fill_bits = bits.u(4)
    line_bits = bits.u(4)
    x = y = 0
    fill0 = fill1 = line = 0
    # StateNewStyles creates a new local style-index namespace.  Store the
    # offset at which that namespace begins in our flattened arrays.
    fill_base = 0
    line_base = 0
    fill_edges: dict[int, list[base.Edge]] = {}
    line_edges: dict[int, list[base.Edge]] = {}

    def fill_index(raw: int) -> int:
        return 0 if raw == 0 else fill_base + raw

    def line_index(raw: int) -> int:
        return 0 if raw == 0 else line_base + raw

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
                edge = base.Edge(start, None, (x / 20.0, y / 20.0))
            else:
                control_dx, control_dy = bits.s(nbits), bits.s(nbits)
                anchor_dx, anchor_dy = bits.s(nbits), bits.s(nbits)
                control_x, control_y = x + control_dx, y + control_dy
                x, y = control_x + anchor_dx, control_y + anchor_dy
                edge = base.Edge(
                    start,
                    (control_x / 20.0, control_y / 20.0),
                    (x / 20.0, y / 20.0),
                )

            if fill1:
                fill_edges.setdefault(fill1, []).append(edge)
            if fill0:
                fill_edges.setdefault(fill0, []).append(base.Edge(edge.end, edge.control, edge.start))
            if line:
                line_edges.setdefault(line, []).append(edge)
            continue

        flags = bits.u(5)
        if flags == 0:
            break
        if flags & 1:
            nbits = bits.u(5)
            x, y = bits.s(nbits), bits.s(nbits)
        if flags & 2:
            fill0 = fill_index(bits.u(fill_bits))
        if flags & 4:
            fill1 = fill_index(bits.u(fill_bits))
        if flags & 8:
            line = line_index(bits.u(line_bits))
        if flags & 16:
            bits.align()
            offset = bits.off
            # The new indices start at 1 again, but refer to styles appended
            # after everything that existed before this record.
            next_fill_base = len(fills)
            next_line_base = len(lines)
            offset, new_fills = base.read_fill_array(payload, offset, shape_version)
            offset, new_lines = base.read_line_array(payload, offset, shape_version)
            fills.extend(new_fills)
            lines.extend(new_lines)
            fill_base = next_fill_base
            line_base = next_line_base
            bits = base.BitReader(payload, offset * 8)
            fill_bits = bits.u(4)
            line_bits = bits.u(4)

    return character_id, bounds, fills, lines, fill_edges, line_edges


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--scale", type=float, default=4.0)
    parser.add_argument("--max-size", type=int, default=2048)
    args = parser.parse_args()

    base.parse_shape = parse_shape
    manifest = base.extract(args.swf, args.output, args.scale, args.max_size)
    print(f"extracted {manifest['shape_count']} corrected vector shapes to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
