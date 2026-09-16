#!/usr/bin/env python3
"""Where the original put things, read from the SWF's placement matrices.

A placement is only half the story: its matrix carries a scale as well as a
translation, and a parent's scale multiplies everything inside it. Comparing two
raw offsets under the same parent is safe, but comparing them across parents, or
reading one as a stage distance, is not -- the workshop panel is drawn at
0.9388, so a 26.4 step inside it is 24.8 on the stage.

`resolve` composes an explicit chain of placements and answers in stage units.
The chain has to be given rather than searched for: a character is placed more
than once (the speaker rows appear in two different panels), so there is no such
thing as "the" position of a character, only its position along a path.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

from swf_inventory import BitReader, iter_tags

PLACE_OBJECT2 = 26
DEFINE_SPRITE = 39
TWIPS = 20.0


@dataclass(frozen=True)
class Placement:
    parent: int | None          # the sprite that placed it, or None for the root
    character: int
    depth: int
    x: float | None
    y: float | None
    scale_x: float = 1.0
    scale_y: float = 1.0


def _matrix(payload: bytes, cursor: int) -> tuple[float, float, float, float]:
    """Scale and translation. A MATRIX stores scale in 16.16 and offsets in twips."""
    reader = BitReader(payload, cursor)
    scale_x = scale_y = 1.0
    if reader.read_unsigned(1):
        bits = reader.read_unsigned(5)
        scale_x = reader.read_signed(bits) / 65536.0
        scale_y = reader.read_signed(bits) / 65536.0
    if reader.read_unsigned(1):                       # rotate/skew, not modelled
        bits = reader.read_unsigned(5)
        reader.read_unsigned(bits * 2)
    bits = reader.read_unsigned(5)
    return scale_x, scale_y, reader.read_signed(bits) / TWIPS, reader.read_signed(bits) / TWIPS


def placements(tags, parent: int | None = None) -> list[Placement]:
    """Every character placement, tagged with the sprite that placed it."""
    found: list[Placement] = []
    for tag in tags:
        payload = tag.payload
        if tag.code == PLACE_OBJECT2 and len(payload) > 3:
            flags = payload[0]
            if not flags & 0x02:                      # a move, not a placement
                continue
            depth = struct.unpack_from("<H", payload, 1)[0]
            character = struct.unpack_from("<H", payload, 3)[0]
            x = y = None
            scale_x = scale_y = 1.0
            if flags & 0x04:
                try:
                    scale_x, scale_y, x, y = _matrix(payload, 5)
                except Exception:
                    x = y = None
            found.append(Placement(parent, character, depth, x, y, scale_x, scale_y))
        elif tag.code == DEFINE_SPRITE and len(payload) >= 4:
            sprite = struct.unpack_from("<H", payload, 0)[0]
            found.extend(placements(iter_tags(payload, 4), sprite))
    return found


def resolve(found: list[Placement], chain: list[tuple[int | None, int]]) -> tuple[float, float, float]:
    """Compose a named path of placements into stage x, y and scale.

    `chain` is read outermost first, as (parent, character) pairs -- the root's
    placement of the panel, then the panel's placement of a row, and so on. Each
    step is scaled by everything above it, which is the part a raw offset misses.
    """
    x = y = 0.0
    scale = 1.0
    for parent, character in chain:
        matches = [p for p in found if p.parent == parent and p.character == character and p.x is not None]
        if not matches:
            raise LookupError(f"{character} is not placed in {parent}")
        if len({(p.x, p.y, p.scale_x) for p in matches}) != 1:
            raise LookupError(f"{character} is placed in {parent} more than once, at different offsets")
        step = matches[0]
        x += scale * step.x
        y += scale * step.y
        scale *= step.scale_x
    return x, y, scale


def spacing(found: list[Placement], chain: list[tuple[int | None, int]], characters: list[int], axis: str = "y") -> list[float]:
    """Stage-space gaps between sibling characters, in the order they appear."""
    x, y, scale = resolve(found, chain)
    parent = chain[-1][1]
    offsets = []
    for character in characters:
        matches = [p for p in found if p.parent == parent and p.character == character and p.x is not None]
        if not matches:
            raise LookupError(f"{character} is not placed in {parent}")
        offsets.append((matches[0].x if axis == "x" else matches[0].y) * scale)
    offsets.sort()
    return [round(later - earlier, 3) for earlier, later in zip(offsets, offsets[1:])]
