#!/usr/bin/env python3
"""Where the original put things, read from the SWF's placement matrices.

Only relative geometry is trustworthy here. Two characters placed by the same
parent can be compared directly -- whatever scale or offset the parent carries
applies to both and cancels. An absolute stage position does not follow from
this, because a character can be placed more than once and a parent chain can
scale; resolving that is a separate problem and this module does not pretend to
have solved it.
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


def _translation(payload: bytes, cursor: int) -> tuple[float, float]:
    reader = BitReader(payload, cursor)
    if reader.read_unsigned(1):                       # scale
        bits = reader.read_unsigned(5)
        reader.read_unsigned(bits * 2)
    if reader.read_unsigned(1):                       # rotate/skew
        bits = reader.read_unsigned(5)
        reader.read_unsigned(bits * 2)
    bits = reader.read_unsigned(5)
    return reader.read_signed(bits) / TWIPS, reader.read_signed(bits) / TWIPS


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
            if flags & 0x04:
                try:
                    x, y = _translation(payload, 5)
                except Exception:
                    x = y = None
            found.append(Placement(parent, character, depth, x, y))
        elif tag.code == DEFINE_SPRITE and len(payload) >= 4:
            sprite = struct.unpack_from("<H", payload, 0)[0]
            found.extend(placements(iter_tags(payload, 4), sprite))
    return found
