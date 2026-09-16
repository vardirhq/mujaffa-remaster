#!/usr/bin/env python3
"""Extract the original Mujaffa opening/title timeline landmarks from the SWF.

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


def _cstring(payload: bytes, offset: int = 0) -> str:
    end = payload.find(b"\0", offset)
    if end < 0:
        end = len(payload)
    return payload[offset:end].decode("latin-1")


def extract(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    header = parse_header(raw)
    frame = 0
    labels: list[dict[str, object]] = []

    for tag in iter_tags(raw, header.tags_offset):
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
    return {
        "schema_version": 1,
        "source": path.name,
        "stage": [header.width, header.height],
        "frame_rate": header.frame_rate,
        "opening_labels": labels,
        "notes": [
            "Frame numbers are recovered from the main SWF timeline.",
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
