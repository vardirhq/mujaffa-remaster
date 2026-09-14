#!/usr/bin/env python3
"""Map main-timeline SWF frames into reconstructable display-list compositions.

This deliberately produces metadata first.  It lets us identify the exact
original garage/showroom composition before inventing any more replacement UI.
"""
from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path

from swf_car_extract import IDENT, iter_tags, place2, swf_tags


def main_timeline(path: Path):
    data, offset = swf_tags(path)
    frame = 1
    display: dict[int, dict] = {}
    labels: dict[int, list[str]] = {}
    snapshots: dict[int, list[dict]] = {}
    for code, payload in iter_tags(data, offset):
        if code == 26:  # PlaceObject2
            item = place2(payload)
            depth = item['depth']
            previous = display.get(depth, {}).copy() if item.get('move') else {}
            previous.update({k: v for k, v in item.items() if k not in ('depth', 'move')})
            previous['depth'] = depth
            display[depth] = previous
        elif code == 28:  # RemoveObject2
            display.pop(struct.unpack_from('<H', payload, 0)[0], None)
        elif code == 43:  # FrameLabel
            label = payload.split(b'\0', 1)[0].decode('utf-8', 'replace')
            labels.setdefault(frame, []).append(label)
        elif code == 1:  # ShowFrame
            snapshots[frame] = [display[d].copy() for d in sorted(display)]
            frame += 1
    return labels, snapshots


def serial(item: dict) -> dict:
    return {
        'depth': item['depth'],
        'character_id': item.get('character'),
        'name': item.get('name'),
        'matrix': list(item.get('matrix', IDENT)),
        'clip_depth': item.get('clip_depth'),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('swf', type=Path)
    parser.add_argument('out', type=Path)
    parser.add_argument('--from-frame', type=int, default=700)
    parser.add_argument('--to-frame', type=int, default=810)
    args = parser.parse_args()

    labels, snapshots = main_timeline(args.swf)
    frames = []
    for frame in range(args.from_frame, args.to_frame + 1):
        if frame not in snapshots:
            continue
        frames.append({
            'frame': frame,
            'labels': labels.get(frame, []),
            'display': [serial(item) for item in snapshots[frame]],
        })

    payload = {
        'purpose': 'Original SWF scene-composition reference. No remaster layout guesses.',
        'range': [args.from_frame, args.to_frame],
        'labelled_frames': [
            {'frame': frame, 'labels': names}
            for frame, names in sorted(labels.items())
            if args.from_frame <= frame <= args.to_frame
        ],
        'frames': frames,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
