#!/usr/bin/env python3
"""Find every ActionScript 1/2 block in a SWF, wherever it hides.

`swf_actions` walks main-timeline `DoAction` only, which is the right scope for
mapping frame flow. The original workshop's economy is not there: a price lives
in the button the player clicks, and those actions sit in `DefineButton2`
records and in the clip actions attached to placed sprites, nested arbitrarily
deep inside `DefineSprite`.

This module is the missing half -- it yields the action payloads themselves,
tagged with where they came from, and leaves interpretation to its callers.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Iterator

from swf_inventory import BitReader, SwfError, iter_tags

DO_ACTION = 12
DO_INIT_ACTION = 59
DEFINE_BUTTON = 7
DEFINE_BUTTON2 = 34
DEFINE_SPRITE = 39
PLACE_OBJECT2 = 26
PLACE_OBJECT3 = 70


@dataclass(frozen=True)
class ActionSite:
    """One block of ActionScript and the path through the file that reached it."""

    origin: str
    payload: bytes
    character: int | None = None


def _skip_matrix(reader: BitReader) -> None:
    if reader.read_unsigned(1):
        bits = reader.read_unsigned(5)
        reader.read_unsigned(bits * 2)
    if reader.read_unsigned(1):
        bits = reader.read_unsigned(5)
        reader.read_unsigned(bits * 2)
    bits = reader.read_unsigned(5)
    reader.read_unsigned(bits * 2)


def _skip_cxform(reader: BitReader, with_alpha: bool) -> None:
    has_add = reader.read_unsigned(1)
    has_mult = reader.read_unsigned(1)
    bits = reader.read_unsigned(4)
    terms = 4 if with_alpha else 3
    if has_mult:
        reader.read_unsigned(bits * terms)
    if has_add:
        reader.read_unsigned(bits * terms)


def _button2_actions(payload: bytes) -> Iterator[ActionSite]:
    """BUTTONCONDACTIONs, whose offset is relative to the offset field itself."""
    if len(payload) < 5:
        return
    character = struct.unpack_from("<H", payload, 0)[0]
    action_offset = struct.unpack_from("<H", payload, 3)[0]
    if action_offset == 0:          # a button with no script at all
        return
    cursor = 3 + action_offset
    while cursor + 4 <= len(payload):
        size = struct.unpack_from("<H", payload, cursor)[0]
        end = len(payload) if size == 0 else cursor + size
        yield ActionSite("DefineButton2", payload[cursor + 4 : end], character)
        if size == 0:
            return
        cursor = end


def _button_actions(payload: bytes) -> Iterator[ActionSite]:
    if len(payload) < 3:
        return
    character = struct.unpack_from("<H", payload, 0)[0]
    cursor = 2
    # BUTTONRECORDs, terminated by a zero byte.
    while cursor < len(payload) and payload[cursor] != 0:
        cursor += 1                                   # flags
        cursor += 2 + 2                               # character, depth
        reader = BitReader(payload, cursor)
        _skip_matrix(reader)
        cursor = reader.byte_offset
    yield ActionSite("DefineButton", payload[cursor + 1 :], character)


def _place_clip_actions(payload: bytes, version: int) -> Iterator[ActionSite]:
    if len(payload) < 3:
        return
    flags = payload[0]
    if not flags & 0x80:                              # PlaceFlagHasClipActions
        return
    cursor = 3                                        # flags, depth
    character = None
    if flags & 0x02:
        character = struct.unpack_from("<H", payload, cursor)[0]
        cursor += 2
    if flags & 0x04:
        reader = BitReader(payload, cursor)
        _skip_matrix(reader)
        cursor = reader.byte_offset
    if flags & 0x08:
        reader = BitReader(payload, cursor)
        _skip_cxform(reader, with_alpha=True)
        cursor = reader.byte_offset
    if flags & 0x10:
        cursor += 2                                   # ratio
    if flags & 0x20:
        cursor = payload.index(b"\0", cursor) + 1     # name
    if flags & 0x40:
        cursor += 2                                   # clip depth

    width = 4 if version >= 6 else 2
    cursor += 2 + width                               # reserved, AllEventFlags
    while cursor + width + 4 <= len(payload):
        event_flags = int.from_bytes(payload[cursor : cursor + width], "little")
        cursor += width
        if event_flags == 0:
            return
        size = struct.unpack_from("<I", payload, cursor)[0]
        cursor += 4
        body = payload[cursor : cursor + size]
        if event_flags & 0x00020000:                  # ClipEventKeyPress
            body = body[1:]
        yield ActionSite("ClipEvent", body, character)
        cursor += size


def action_sites(tags, version: int, origin: str = "") -> Iterator[ActionSite]:
    """Every action payload reachable from these tags, sprites included."""
    for tag in tags:
        payload = tag.payload
        where = origin or "root"
        if tag.code == DO_ACTION:
            yield ActionSite(f"{where}/DoAction", payload)
        elif tag.code == DO_INIT_ACTION and len(payload) >= 2:
            character = struct.unpack_from("<H", payload, 0)[0]
            yield ActionSite(f"{where}/DoInitAction", payload[2:], character)
        elif tag.code == DEFINE_BUTTON2:
            for site in _button2_actions(payload):
                yield ActionSite(f"{where}/{site.origin}", site.payload, site.character)
        elif tag.code == DEFINE_BUTTON:
            for site in _button_actions(payload):
                yield ActionSite(f"{where}/{site.origin}", site.payload, site.character)
        elif tag.code in (PLACE_OBJECT2, PLACE_OBJECT3):
            try:
                sites = list(_place_clip_actions(payload, version))
            except (SwfError, struct.error, IndexError):
                sites = []
            for site in sites:
                yield ActionSite(f"{where}/{site.origin}", site.payload, site.character)
        elif tag.code == DEFINE_SPRITE and len(payload) >= 4:
            sprite = struct.unpack_from("<H", payload, 0)[0]
            yield from action_sites(
                iter_tags(payload, 4), version, f"{where}/Sprite{sprite}"
            )
