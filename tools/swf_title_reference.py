#!/usr/bin/env python3
"""Extract original Mujaffa opening/title timeline landmarks from the SWF.

This intentionally owns only title/navigation evidence. Workshop economy recovery
lives elsewhere so both reverse-engineering tracks can evolve independently.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from swf_inventory import iter_tags, parse_header

OPENING_LABELS = {
    "start",
    "velkommen",
    "speakDone",
    "gotoInstruktioner",
    "gotoGame",
    "initGame",
}


def _cstring(payload: bytes) -> str:
    return payload.split(b"\0", 1)[0].decode("utf-8", errors="replace")


def _u16(payload: bytes, offset: int = 0) -> int:
    return struct.unpack_from("<H", payload, offset)[0]


def _named_characters(data: bytes, tags_offset: int) -> list[dict[str, object]]:
    """Recover SWF SymbolClass/ExportAssets names without interpreting artwork."""
    found: dict[tuple[int, str], set[str]] = {}
    for tag in iter_tags(data, tags_offset):
        if tag.code not in {56, 76} or len(tag.payload) < 2:
            continue
        count = _u16(tag.payload)
        offset = 2
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
            found.setdefault((character_id, name), set()).add(
                "SymbolClass" if tag.code == 76 else "ExportAssets"
            )
    return [
        {"character_id": character_id, "name": name, "sources": sorted(sources)}
        for (character_id, name), sources in sorted(found.items())
    ]


def _tag_counts(data: bytes, tags_offset: int) -> dict[str, int]:
    """Record title-relevant definition/display tag counts as extraction guardrails."""
    relevant = {
        2: "DefineShape",
        22: "DefineShape2",
        32: "DefineShape3",
        83: "DefineShape4",
        7: "DefineButton",
        34: "DefineButton2",
        11: "DefineText",
        33: "DefineText2",
        37: "DefineEditText",
        39: "DefineSprite",
        4: "PlaceObject",
        26: "PlaceObject2",
        70: "PlaceObject3",
        5: "RemoveObject",
        28: "RemoveObject2",
    }
    counts = {name: 0 for name in relevant.values()}
    for tag in iter_tags(data, tags_offset):
        name = relevant.get(tag.code)
        if name is not None:
            counts[name] += 1
    return {name: count for name, count in counts.items() if count}


def _opening_tag_trace(data: bytes, tags_offset: int, end_frame: int) -> list[dict[str, object]]:
    """Trace main-timeline display mutations through the opening navigation range.

    Payload decoding comes next. Keeping the raw tag family, frame and payload
    size first makes that decoder auditable and prevents accidental inclusion of
    workshop timeline activity after the title flow.
    """
    names = {
        4: "PlaceObject",
        26: "PlaceObject2",
        70: "PlaceObject3",
        5: "RemoveObject",
        28: "RemoveObject2",
        43: "FrameLabel",
    }
    frame = 1
    trace: list[dict[str, object]] = []
    for tag in iter_tags(data, tags_offset):
        if frame > end_frame:
            break
        if tag.code == 1:
            frame += 1
            continue
        name = names.get(tag.code)
        if name is None:
            continue
        entry: dict[str, object] = {
            "frame": frame,
            "tag": name,
            "payload_bytes": len(tag.payload),
        }
        if tag.code == 43:
            entry["label"] = _cstring(tag.payload)
        trace.append(entry)
    return trace


def extract(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    data, header = parse_header(raw)
    frame = 0
    labels: list[dict[str, object]] = []

    for tag in iter_tags(data, header.tags_offset):
        if tag.code == 1:  # ShowFrame
            frame += 1
            continue
        if tag.code != 43:  # FrameLabel
            continue
        label = _cstring(tag.payload)
        if label in OPENING_LABELS:
            labels.append({"label": label, "frame": frame + 1})

    missing = sorted(OPENING_LABELS - {entry["label"] for entry in labels})
    if missing:
        raise ValueError(f"opening labels missing from SWF: {', '.join(missing)}")

    labels.sort(key=lambda entry: int(entry["frame"]))
    opening_end = max(int(entry["frame"]) for entry in labels)
    return {
        "schema_version": 4,
        "source": path.name,
        "stage": [header.width, header.height],
        "frame_rate": header.fps,
        "opening_labels": labels,
        "named_characters": _named_characters(data, header.tags_offset),
        "title_relevant_tag_counts": _tag_counts(data, header.tags_offset),
        "opening_display_trace": _opening_tag_trace(data, header.tags_offset, opening_end),
        "notes": [
            "Frame numbers are recovered from the main SWF timeline.",
            "Named characters come from SymbolClass and ExportAssets tags and are evidence, not inferred title membership.",
            "Tag counts are extraction guardrails, not evidence that every definition belongs to the opening title.",
            "Opening display trace is limited to the main timeline through the last opening navigation label; placement payload decoding is intentionally a separate step.",
            "This file deliberately contains no workshop economy data.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    result = extract(args.swf)
    encoded = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    else:
        print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
