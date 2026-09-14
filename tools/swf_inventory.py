#!/usr/bin/env python3
"""Inspect the original Mujaffa SWF without executing Flash code.

The remaster needs a reproducible reference inventory before any gameplay or
art is rebuilt. This parser intentionally sticks to SWF container structure:
movie dimensions, timing, tag counts, character definitions and frame labels.
It does not execute ActionScript and it does not export copyrighted assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

TAG_NAMES = {
    0: "End",
    1: "ShowFrame",
    2: "DefineShape",
    4: "PlaceObject",
    5: "RemoveObject",
    6: "DefineBits",
    7: "DefineButton",
    8: "JPEGTables",
    9: "SetBackgroundColor",
    10: "DefineFont",
    11: "DefineText",
    12: "DoAction",
    13: "DefineFontInfo",
    14: "DefineSound",
    15: "StartSound",
    17: "DefineButtonSound",
    18: "SoundStreamHead",
    19: "SoundStreamBlock",
    20: "DefineBitsLossless",
    21: "DefineBitsJPEG2",
    22: "DefineShape2",
    23: "DefineButtonCxform",
    24: "Protect",
    26: "PlaceObject2",
    28: "RemoveObject2",
    32: "DefineShape3",
    33: "DefineText2",
    34: "DefineButton2",
    35: "DefineBitsJPEG3",
    36: "DefineBitsLossless2",
    37: "DefineEditText",
    39: "DefineSprite",
    43: "FrameLabel",
    45: "SoundStreamHead2",
    46: "DefineMorphShape",
    48: "DefineFont2",
    56: "ExportAssets",
    57: "ImportAssets",
    58: "EnableDebugger",
    59: "DoInitAction",
    60: "DefineVideoStream",
    61: "VideoFrame",
    62: "DefineFontInfo2",
    64: "EnableDebugger2",
    65: "ScriptLimits",
    66: "SetTabIndex",
    69: "FileAttributes",
    70: "PlaceObject3",
    73: "DefineFontAlignZones",
    74: "CSMTextSettings",
    75: "DefineFont3",
    76: "SymbolClass",
    77: "Metadata",
    78: "DefineScalingGrid",
    82: "DoABC",
    83: "DefineShape4",
    84: "DefineMorphShape2",
    86: "DefineSceneAndFrameLabelData",
    87: "DefineBinaryData",
    88: "DefineFontName",
    89: "StartSound2",
    90: "DefineBitsJPEG4",
    91: "DefineFont4",
}

# SWF tags whose payload begins with a UI16 character ID.
CHARACTER_TAGS = {
    2, 6, 7, 10, 11, 14, 20, 21, 22, 32, 33, 34, 35, 36, 37, 39, 46,
    48, 60, 75, 83, 84, 87, 90, 91,
}

BITMAP_TAGS = {6, 20, 21, 35, 36, 90}
SHAPE_TAGS = {2, 22, 32, 83}
TEXT_TAGS = {11, 33, 37}
BUTTON_TAGS = {7, 34}
SOUND_TAGS = {14}
SCRIPT_TAGS = {12, 59, 82}


class SwfError(ValueError):
    pass


class BitReader:
    def __init__(self, data: bytes, offset: int = 0) -> None:
        self.data = data
        self.bit = offset * 8

    def read_unsigned(self, count: int) -> int:
        value = 0
        for _ in range(count):
            byte_index, bit_index = divmod(self.bit, 8)
            if byte_index >= len(self.data):
                raise SwfError("unexpected end of bit stream")
            value = (value << 1) | ((self.data[byte_index] >> (7 - bit_index)) & 1)
            self.bit += 1
        return value

    def read_signed(self, count: int) -> int:
        value = self.read_unsigned(count)
        sign = 1 << (count - 1)
        return value - (1 << count) if value & sign else value

    @property
    def byte_offset(self) -> int:
        return (self.bit + 7) // 8


@dataclass(frozen=True)
class Tag:
    code: int
    payload: bytes


@dataclass(frozen=True)
class MovieHeader:
    signature: str
    version: int
    declared_length: int
    width: float
    height: float
    fps: float
    frame_count: int
    tags_offset: int


def _decompress(raw: bytes) -> tuple[bytes, str, int, int]:
    if len(raw) < 8:
        raise SwfError("file is too short to be an SWF")
    signature = raw[:3].decode("ascii", errors="replace")
    version = raw[3]
    declared_length = struct.unpack_from("<I", raw, 4)[0]

    if signature == "FWS":
        data = raw
    elif signature == "CWS":
        data = b"FWS" + raw[3:8] + zlib.decompress(raw[8:])
    elif signature == "ZWS":
        raise SwfError("LZMA-compressed ZWS files are not supported yet")
    else:
        raise SwfError(f"unsupported SWF signature {signature!r}")

    if len(data) != declared_length:
        raise SwfError(
            f"declared SWF length is {declared_length} bytes but decoded length is {len(data)}"
        )
    return data, signature, version, declared_length


def parse_header(raw: bytes) -> tuple[bytes, MovieHeader]:
    data, signature, version, declared_length = _decompress(raw)
    bits = BitReader(data, 8)
    nbits = bits.read_unsigned(5)
    xmin = bits.read_signed(nbits)
    xmax = bits.read_signed(nbits)
    ymin = bits.read_signed(nbits)
    ymax = bits.read_signed(nbits)
    offset = bits.byte_offset
    if offset + 4 > len(data):
        raise SwfError("movie header is truncated")

    frame_rate_raw, frame_count = struct.unpack_from("<HH", data, offset)
    offset += 4
    header = MovieHeader(
        signature=signature,
        version=version,
        declared_length=declared_length,
        width=(xmax - xmin) / 20.0,
        height=(ymax - ymin) / 20.0,
        fps=frame_rate_raw / 256.0,
        frame_count=frame_count,
        tags_offset=offset,
    )
    return data, header


def iter_tags(data: bytes, offset: int) -> list[Tag]:
    tags: list[Tag] = []
    cursor = offset
    while cursor + 2 <= len(data):
        record = struct.unpack_from("<H", data, cursor)[0]
        cursor += 2
        code = record >> 6
        length = record & 0x3F
        if length == 0x3F:
            if cursor + 4 > len(data):
                raise SwfError("truncated long tag header")
            length = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
        end = cursor + length
        if end > len(data):
            raise SwfError(f"tag {code} extends beyond end of file")
        tags.append(Tag(code, data[cursor:end]))
        cursor = end
        if code == 0:
            break
    return tags


def _cstring(payload: bytes) -> str:
    text = payload.split(b"\0", 1)[0]
    return text.decode("utf-8", errors="replace")


def _category_count(tags: list[Tag], codes: set[int]) -> int:
    return sum(1 for tag in tags if tag.code in codes)


def inventory(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    data, header = parse_header(raw)
    tags = iter_tags(data, header.tags_offset)

    counts = Counter(tag.code for tag in tags)
    payload_bytes = Counter()
    character_ids: dict[int, list[int]] = {}
    frame_labels: list[str] = []

    for tag in tags:
        payload_bytes[tag.code] += len(tag.payload)
        if tag.code in CHARACTER_TAGS and len(tag.payload) >= 2:
            character_ids.setdefault(tag.code, []).append(struct.unpack_from("<H", tag.payload)[0])
        if tag.code == 43:
            frame_labels.append(_cstring(tag.payload))

    tags_summary = []
    for code in sorted(counts):
        tags_summary.append(
            {
                "code": code,
                "name": TAG_NAMES.get(code, f"Tag{code}"),
                "count": counts[code],
                "payload_bytes": payload_bytes[code],
            }
        )

    return {
        "source": {
            "file": path.name,
            "sha256": hashlib.sha256(raw).hexdigest(),
            "encoded_bytes": len(raw),
            "decoded_bytes": len(data),
        },
        "movie": {
            "signature": header.signature,
            "version": header.version,
            "width": header.width,
            "height": header.height,
            "fps": header.fps,
            "frame_count": header.frame_count,
        },
        "summary": {
            "tag_count": len(tags),
            "defined_characters": sum(len(ids) for ids in character_ids.values()),
            "shapes": _category_count(tags, SHAPE_TAGS),
            "sprites": counts[39],
            "text_fields": _category_count(tags, TEXT_TAGS),
            "buttons": _category_count(tags, BUTTON_TAGS),
            "sounds": _category_count(tags, SOUND_TAGS),
            "script_blocks": _category_count(tags, SCRIPT_TAGS),
            "bitmap_definitions": _category_count(tags, BITMAP_TAGS),
            "frame_labels": len(frame_labels),
        },
        "frame_labels": frame_labels,
        "tags": tags_summary,
        "character_ids": {
            f"{code}:{TAG_NAMES.get(code, f'Tag{code}')}": ids
            for code, ids in sorted(character_ids.items())
        },
    }


def verify_mujaffa_reference(report: dict[str, object]) -> list[str]:
    """Return invariant failures for the known Norwegian reference movie."""
    movie = report["movie"]
    summary = report["summary"]
    assert isinstance(movie, dict)
    assert isinstance(summary, dict)

    expected = {
        "version": 6,
        "width": 500.0,
        "height": 500.0,
        "fps": 12.0,
        "frame_count": 811,
    }
    failures = []
    for key, value in expected.items():
        if movie.get(key) != value:
            failures.append(f"movie.{key}: expected {value!r}, got {movie.get(key)!r}")

    if summary.get("bitmap_definitions") != 0:
        failures.append(
            "summary.bitmap_definitions: expected 0 standard bitmap definitions "
            f"but found {summary.get('bitmap_definitions')}"
        )
    if int(summary.get("shapes", 0)) < 500:
        failures.append("summary.shapes: expected at least 500 vector shape definitions")
    if int(summary.get("sprites", 0)) < 250:
        failures.append("summary.sprites: expected at least 250 sprite definitions")
    if int(summary.get("script_blocks", 0)) < 60:
        failures.append("summary.script_blocks: expected at least 60 script blocks")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument(
        "--verify-reference",
        action="store_true",
        help="fail if the file no longer matches the known Mujaffa reference invariants",
    )
    args = parser.parse_args()

    try:
        report = inventory(args.swf)
    except (OSError, SwfError) as exc:
        print(f"swf_inventory: {exc}", file=sys.stderr)
        return 2

    encoded = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)

    if args.verify_reference:
        failures = verify_mujaffa_reference(report)
        if failures:
            for failure in failures:
                print(f"reference mismatch: {failure}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
