#!/usr/bin/env python3
"""Disassemble enough SWF ActionScript 1/2 metadata to map original behaviour.

This is deliberately not an ActionScript VM. It walks DoAction records on the
main timeline *and inside DefineSprite timelines*, recording their location,
opcode mix, branch targets and literal strings. Mujaffa keeps much of its live
gameplay inside movie clips, so looking only at the root timeline misses most of
the program.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from collections import Counter
from pathlib import Path
from typing import Iterator

from swf_inventory import SwfError, Tag, _cstring, iter_tags, parse_header

ACTION_NAMES = {
    0x04: "NextFrame",
    0x05: "PreviousFrame",
    0x06: "Play",
    0x07: "Stop",
    0x08: "ToggleQuality",
    0x09: "StopSounds",
    0x0A: "Add",
    0x0B: "Subtract",
    0x0C: "Multiply",
    0x0D: "Divide",
    0x0E: "Equals",
    0x0F: "Less",
    0x10: "And",
    0x11: "Or",
    0x12: "Not",
    0x13: "StringEquals",
    0x14: "StringLength",
    0x15: "StringExtract",
    0x17: "Pop",
    0x18: "ToInteger",
    0x1C: "GetVariable",
    0x1D: "SetVariable",
    0x20: "SetTarget2",
    0x21: "StringAdd",
    0x22: "GetProperty",
    0x23: "SetProperty",
    0x24: "CloneSprite",
    0x25: "RemoveSprite",
    0x26: "Trace",
    0x27: "StartDrag",
    0x28: "EndDrag",
    0x29: "StringLess",
    0x30: "RandomNumber",
    0x31: "MBStringLength",
    0x32: "CharToAscii",
    0x33: "AsciiToChar",
    0x34: "GetTime",
    0x35: "MBStringExtract",
    0x36: "MBCharToAscii",
    0x37: "MBAsciiToChar",
    0x3A: "Delete",
    0x3B: "Delete2",
    0x3C: "DefineLocal",
    0x3D: "CallFunction",
    0x3E: "Return",
    0x3F: "Modulo",
    0x40: "NewObject",
    0x41: "DefineLocal2",
    0x42: "InitArray",
    0x43: "InitObject",
    0x44: "TypeOf",
    0x45: "TargetPath",
    0x46: "Enumerate",
    0x47: "Add2",
    0x48: "Less2",
    0x49: "Equals2",
    0x4A: "ToNumber",
    0x4B: "ToString",
    0x4C: "PushDuplicate",
    0x4D: "StackSwap",
    0x4E: "GetMember",
    0x4F: "SetMember",
    0x50: "Increment",
    0x51: "Decrement",
    0x52: "CallMethod",
    0x53: "NewMethod",
    0x54: "InstanceOf",
    0x55: "Enumerate2",
    0x60: "BitAnd",
    0x61: "BitOr",
    0x62: "BitXor",
    0x63: "BitLShift",
    0x64: "BitRShift",
    0x65: "BitURShift",
    0x66: "StrictEquals",
    0x67: "Greater",
    0x68: "StringGreater",
    0x69: "Extends",
    0x81: "GotoFrame",
    0x83: "GetURL",
    0x87: "StoreRegister",
    0x88: "ConstantPool",
    0x8A: "WaitForFrame",
    0x8B: "SetTarget",
    0x8C: "GoToLabel",
    0x8D: "WaitForFrame2",
    0x8E: "DefineFunction2",
    0x8F: "Try",
    0x94: "With",
    0x96: "Push",
    0x99: "Jump",
    0x9A: "GetURL2",
    0x9B: "DefineFunction",
    0x9D: "If",
    0x9E: "Call",
    0x9F: "GotoFrame2",
}


def action_records(payload: bytes) -> list[tuple[int, bytes, int]]:
    records: list[tuple[int, bytes, int]] = []
    cursor = 0
    while cursor < len(payload):
        offset = cursor
        code = payload[cursor]
        cursor += 1
        if code == 0:
            break
        length = 0
        if code >= 0x80:
            if cursor + 2 > len(payload):
                raise SwfError("truncated ActionScript action length")
            length = struct.unpack_from("<H", payload, cursor)[0]
            cursor += 2
        end = cursor + length
        if end > len(payload):
            raise SwfError(f"ActionScript action 0x{code:02x} extends beyond block")
        records.append((code, payload[cursor:end], offset))
        cursor = end
    return records


def strings_from_push(payload: bytes) -> list[str]:
    strings: list[str] = []
    cursor = 0
    while cursor < len(payload):
        kind = payload[cursor]
        cursor += 1
        if kind == 0:  # String
            end = payload.find(b"\0", cursor)
            if end < 0:
                raise SwfError("unterminated string in ActionPush")
            strings.append(payload[cursor:end].decode("utf-8", errors="replace"))
            cursor = end + 1
        elif kind == 1:  # Float
            cursor += 4
        elif kind in (2, 3):  # Null, Undefined
            pass
        elif kind in (4, 5, 8):  # Register, Boolean, Constant8
            cursor += 1
        elif kind == 6:  # Double
            cursor += 8
        elif kind == 7:  # Integer
            cursor += 4
        elif kind == 9:  # Constant16
            cursor += 2
        else:
            raise SwfError(f"unknown ActionPush value type {kind}")
        if cursor > len(payload):
            raise SwfError("truncated ActionPush value")
    return strings


def strings_from_constant_pool(payload: bytes) -> list[str]:
    if len(payload) < 2:
        raise SwfError("truncated ActionConstantPool")
    count = struct.unpack_from("<H", payload)[0]
    cursor = 2
    strings: list[str] = []
    for _ in range(count):
        end = payload.find(b"\0", cursor)
        if end < 0:
            raise SwfError("unterminated ActionConstantPool string")
        strings.append(payload[cursor:end].decode("utf-8", errors="replace"))
        cursor = end + 1
    return strings


def direct_strings(code: int, payload: bytes) -> list[str]:
    if code == 0x96:
        return strings_from_push(payload)
    if code == 0x88:
        return strings_from_constant_pool(payload)
    if code in (0x8B, 0x8C):
        return [_cstring(payload)]
    if code == 0x83:
        first_end = payload.find(b"\0")
        if first_end < 0:
            raise SwfError("unterminated ActionGetURL url")
        second = payload[first_end + 1 :]
        return [
            payload[:first_end].decode("utf-8", errors="replace"),
            _cstring(second),
        ]
    return []


def branch_detail(code: int, payload: bytes, action_offset: int) -> dict[str, object]:
    if code == 0x81 and len(payload) >= 2:
        return {"frame": struct.unpack_from("<H", payload)[0]}
    if code in (0x99, 0x9D) and len(payload) >= 2:
        delta = struct.unpack_from("<h", payload)[0]
        return {
            "branch_delta": delta,
            "branch_target_offset": action_offset + 3 + len(payload) + delta,
        }
    if code == 0x8A and len(payload) >= 3:
        frame, skip = struct.unpack_from("<HB", payload)
        return {"frame": frame, "skip_actions": skip}
    if code == 0x8D and payload:
        return {"skip_actions": payload[0]}
    return {}


def iter_timeline_action_blocks(
    tags: list[Tag],
    *,
    timeline: str = "main",
    depth: int = 0,
    sprite_id: int | None = None,
    declared_frames: int | None = None,
) -> Iterator[dict[str, object]]:
    """Yield every DoAction block, recursively descending into DefineSprite.

    A DefineSprite payload starts with UI16 SpriteId + UI16 FrameCount followed
    by an ordinary SWF tag stream. Each sprite owns its own frame counter and
    labels, so the context is tracked independently rather than pretending its
    actions occur on a main-timeline frame.
    """

    frame = 1
    label: str | None = None
    for tag in tags:
        if tag.code == 43:
            label = _cstring(tag.payload)
        elif tag.code == 12:
            yield {
                "timeline": timeline,
                "depth": depth,
                "sprite_id": sprite_id,
                "declared_frames": declared_frames,
                "frame": frame,
                "label": label,
                "payload": tag.payload,
            }
        elif tag.code == 39:
            if len(tag.payload) < 4:
                raise SwfError("truncated DefineSprite payload")
            child_id, child_frames = struct.unpack_from("<HH", tag.payload, 0)
            child_timeline = f"{timeline}/sprite:{child_id}"
            child_tags = iter_tags(tag.payload, 4)
            yield from iter_timeline_action_blocks(
                child_tags,
                timeline=child_timeline,
                depth=depth + 1,
                sprite_id=child_id,
                declared_frames=child_frames,
            )
        elif tag.code == 1:
            frame += 1
            label = None


def inspect(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    data, header = parse_header(raw)
    tags = iter_tags(data, header.tags_offset)

    blocks: list[dict[str, object]] = []
    opcode_counts: Counter[str] = Counter()
    all_strings: set[str] = set()
    sprites_with_actions: set[int] = set()
    max_depth = 0

    for located in iter_timeline_action_blocks(tags):
        records = action_records(located["payload"])
        actions = []
        block_strings: set[str] = set()
        for code, action_payload, action_offset in records:
            name = ACTION_NAMES.get(code, f"Action0x{code:02X}")
            opcode_counts[name] += 1
            literals = direct_strings(code, action_payload)
            block_strings.update(literals)
            all_strings.update(literals)
            action = {
                "offset": action_offset,
                "code": code,
                "name": name,
            }
            action.update(branch_detail(code, action_payload, action_offset))
            if literals:
                action["strings"] = literals
            actions.append(action)

        sprite_id = located["sprite_id"]
        if isinstance(sprite_id, int):
            sprites_with_actions.add(sprite_id)
        max_depth = max(max_depth, int(located["depth"]))
        blocks.append(
            {
                "timeline": located["timeline"],
                "depth": located["depth"],
                "sprite_id": sprite_id,
                "declared_frames": located["declared_frames"],
                "frame": located["frame"],
                "label": located["label"],
                "action_count": len(actions),
                "strings": sorted(block_strings, key=str.casefold),
                "actions": actions,
            }
        )

    main_blocks = sum(1 for block in blocks if block["timeline"] == "main")
    return {
        "source": path.name,
        "summary": {
            "action_blocks": len(blocks),
            "main_timeline_action_blocks": main_blocks,
            "sprite_action_blocks": len(blocks) - main_blocks,
            "sprites_with_actions": len(sprites_with_actions),
            "max_timeline_depth": max_depth,
            "actions": sum(block["action_count"] for block in blocks),
            "unique_literal_strings": len(all_strings),
        },
        "opcode_counts": dict(sorted(opcode_counts.items())),
        "literal_strings": sorted(all_strings, key=str.casefold),
        "blocks": blocks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        report = inspect(args.swf)
    except (OSError, SwfError) as exc:
        print(f"swf_actions: {exc}", file=sys.stderr)
        return 2

    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(encoded, encoding="utf-8")
    else:
        sys.stdout.write(encoded)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
