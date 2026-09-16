#!/usr/bin/env python3
"""Extract original Mujaffa opening/title timeline evidence from the SWF."""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from swf_inventory import BitReader, SwfError, iter_tags, parse_header

OPENING_LABELS = {"start", "velkommen", "speakDone", "gotoInstruktioner", "gotoGame", "initGame"}


def _cstring(payload: bytes) -> str:
    return payload.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def _u16(payload: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<H", payload, offset)[0]


def _matrix(payload: bytes, offset: int) -> tuple[dict[str, float], int]:
    bits = BitReader(payload, offset)
    scale_x = scale_y = 1.0
    rotate_skew_0 = rotate_skew_1 = 0.0
    if bits.read_unsigned(1):
        count = bits.read_unsigned(5)
        scale_x = bits.read_signed(count) / 65536.0
        scale_y = bits.read_signed(count) / 65536.0
    if bits.read_unsigned(1):
        count = bits.read_unsigned(5)
        rotate_skew_0 = bits.read_signed(count) / 65536.0
        rotate_skew_1 = bits.read_signed(count) / 65536.0
    count = bits.read_unsigned(5)
    tx = bits.read_signed(count) / 20.0 if count else 0.0
    ty = bits.read_signed(count) / 20.0 if count else 0.0
    return {
        "scale_x": scale_x,
        "scale_y": scale_y,
        "rotate_skew_0": rotate_skew_0,
        "rotate_skew_1": rotate_skew_1,
        "translate_x": tx,
        "translate_y": ty,
    }, bits.byte_offset


def _place_object(tag_code: int, payload: bytes) -> dict[str, object]:
    if tag_code == 4:
        if len(payload) < 4:
            raise SwfError("truncated PlaceObject")
        character_id, depth = struct.unpack_from("<HH", payload, 0)
        matrix, _ = _matrix(payload, 4)
        return {"character_id": character_id, "depth": depth, "move": False, "matrix": matrix}

    if tag_code != 26:
        raise SwfError(f"unsupported placement tag {tag_code}")
    if len(payload) < 3:
        raise SwfError("truncated PlaceObject2")
    flags = payload[0]
    offset = 1
    depth = _u16(payload, offset)
    offset += 2
    entry: dict[str, object] = {"depth": depth, "move": bool(flags & 0x01)}
    if flags & 0x02:
        if offset + 2 > len(payload):
            raise SwfError("truncated PlaceObject2 character id")
        entry["character_id"] = _u16(payload, offset)
        offset += 2
    if flags & 0x04:
        matrix, offset = _matrix(payload, offset)
        entry["matrix"] = matrix
    if flags & 0x20:
        end = payload.find(b"\0", offset)
        if end < 0:
            raise SwfError("unterminated PlaceObject2 name")
        entry["name"] = payload[offset:end].decode("utf-8", errors="replace")
    return entry


def _named_characters(data: bytes, tags_offset: int) -> list[dict[str, object]]:
    found: dict[tuple[int, str], set[str]] = {}
    for tag in iter_tags(data, tags_offset):
        if tag.code not in {56, 76} or len(tag.payload) < 2:
            continue
        count, offset = _u16(tag.payload), 2
        for _ in range(count):
            if offset + 2 > len(tag.payload):
                break
            character_id = _u16(tag.payload, offset)
            offset += 2
            end = tag.payload.find(b"\0", offset)
            if end < 0:
                break
            name = tag.payload[offset:end].decode("utf-8", errors="replace")
            offset = end + 1
            found.setdefault((character_id, name), set()).add("SymbolClass" if tag.code == 76 else "ExportAssets")
    return [{"character_id": cid, "name": name, "sources": sorted(sources)} for (cid, name), sources in sorted(found.items())]


def _tag_counts(data: bytes, tags_offset: int) -> dict[str, int]:
    relevant = {2:"DefineShape",22:"DefineShape2",32:"DefineShape3",83:"DefineShape4",7:"DefineButton",34:"DefineButton2",11:"DefineText",33:"DefineText2",37:"DefineEditText",39:"DefineSprite",4:"PlaceObject",26:"PlaceObject2",70:"PlaceObject3",5:"RemoveObject",28:"RemoveObject2"}
    counts = {name: 0 for name in relevant.values()}
    for tag in iter_tags(data, tags_offset):
        if tag.code in relevant:
            counts[relevant[tag.code]] += 1
    return {name: count for name, count in counts.items() if count}


def _opening_display_trace(data: bytes, tags_offset: int, end_frame: int) -> list[dict[str, object]]:
    frame = 1
    trace: list[dict[str, object]] = []
    for tag in iter_tags(data, tags_offset):
        if frame > end_frame:
            break
        if tag.code == 1:
            frame += 1
            continue
        if tag.code in {4, 26}:
            entry = {"frame": frame, "tag": "PlaceObject" if tag.code == 4 else "PlaceObject2"}
            entry.update(_place_object(tag.code, tag.payload))
            trace.append(entry)
        elif tag.code == 5 and len(tag.payload) >= 4:
            character_id, depth = struct.unpack_from("<HH", tag.payload)
            trace.append({"frame": frame, "tag": "RemoveObject", "character_id": character_id, "depth": depth})
        elif tag.code == 28 and len(tag.payload) >= 2:
            trace.append({"frame": frame, "tag": "RemoveObject2", "depth": _u16(tag.payload)})
        elif tag.code == 43:
            trace.append({"frame": frame, "tag": "FrameLabel", "label": _cstring(tag.payload)})
    return trace


def extract(path: Path) -> dict[str, object]:
    data, header = parse_header(path.read_bytes())
    frame = 0
    labels: list[dict[str, object]] = []
    for tag in iter_tags(data, header.tags_offset):
        if tag.code == 1:
            frame += 1
        elif tag.code == 43:
            label = _cstring(tag.payload)
            if label in OPENING_LABELS:
                labels.append({"label": label, "frame": frame + 1})
    missing = sorted(OPENING_LABELS - {entry["label"] for entry in labels})
    if missing:
        raise ValueError(f"opening labels missing from SWF: {', '.join(missing)}")
    labels.sort(key=lambda entry: int(entry["frame"]))
    opening_end = max(int(entry["frame"]) for entry in labels)
    return {
        "schema_version": 5,
        "source": path.name,
        "stage": [header.width, header.height],
        "frame_rate": header.fps,
        "opening_labels": labels,
        "named_characters": _named_characters(data, header.tags_offset),
        "title_relevant_tag_counts": _tag_counts(data, header.tags_offset),
        "opening_display_trace": _opening_display_trace(data, header.tags_offset, opening_end),
        "notes": [
            "Placement matrices use SWF coordinates converted from twips to pixels.",
            "PlaceObject2 color transforms, ratios, clip depths and clip actions are not yet decoded.",
            "PlaceObject3 is inventoried but not decoded until evidence shows it occurs in the opening range.",
            "This file deliberately contains no workshop economy data.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    encoded = json.dumps(extract(args.swf), indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
