#!/usr/bin/env python3
"""Recover simple variable reads/writes from main-timeline ActionScript 1/2.

This is intentionally a symbolic stack walker, not a Flash VM. It resolves
ActionPush constants, follows simple arithmetic/comparison expressions and
records SetVariable/GetVariable operations. Unsupported actions invalidate the
symbolic stack rather than pretending we understood them.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

from swf_actions import action_records, strings_from_constant_pool
from swf_inventory import SwfError, _cstring, iter_tags, parse_header


def push_values(payload: bytes, pool: list[str]) -> list[object]:
    values: list[object] = []
    cursor = 0
    while cursor < len(payload):
        kind = payload[cursor]
        cursor += 1
        if kind == 0:
            end = payload.find(b"\0", cursor)
            if end < 0:
                raise SwfError("unterminated string in ActionPush")
            values.append(payload[cursor:end].decode("utf-8", errors="replace"))
            cursor = end + 1
        elif kind == 1:
            values.append(struct.unpack_from("<f", payload, cursor)[0])
            cursor += 4
        elif kind == 2:
            values.append(None)
        elif kind == 3:
            values.append({"undefined": True})
        elif kind == 4:
            values.append({"register": payload[cursor]})
            cursor += 1
        elif kind == 5:
            values.append(bool(payload[cursor]))
            cursor += 1
        elif kind == 6:
            raw = payload[cursor : cursor + 8]
            if len(raw) != 8:
                raise SwfError("truncated double in ActionPush")
            # SWF stores the two 32-bit words of a double in swapped order.
            values.append(struct.unpack("<d", raw[4:8] + raw[0:4])[0])
            cursor += 8
        elif kind == 7:
            values.append(struct.unpack_from("<i", payload, cursor)[0])
            cursor += 4
        elif kind == 8:
            index = payload[cursor]
            cursor += 1
            values.append(pool[index] if index < len(pool) else {"constant8": index})
        elif kind == 9:
            index = struct.unpack_from("<H", payload, cursor)[0]
            cursor += 2
            values.append(pool[index] if index < len(pool) else {"constant16": index})
        else:
            raise SwfError(f"unknown ActionPush value type {kind}")
        if cursor > len(payload):
            raise SwfError("truncated ActionPush value")
    return values


def render(value: object) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if value is None or isinstance(value, (bool, int, float)):
        return json.dumps(value)
    if isinstance(value, dict):
        if "var" in value:
            return f"var({value['var']})"
        if "expr" in value:
            return str(value["expr"])
        if "undefined" in value:
            return "undefined"
        if "register" in value:
            return f"register({value['register']})"
    return "?"


def pop(stack: list[object]) -> object:
    return stack.pop() if stack else {"expr": "?"}


def binary(stack: list[object], operator: str) -> None:
    right = pop(stack)
    left = pop(stack)
    stack.append({"expr": f"({render(left)} {operator} {render(right)})"})


def analyze(payload: bytes) -> dict[str, object]:
    pool: list[str] = []
    stack: list[object] = []
    reads: list[str] = []
    writes: list[dict[str, object]] = []
    conditions: list[dict[str, object]] = []
    random_expressions: list[str] = []
    gotos: list[dict[str, object]] = []

    for code, action_payload, offset in action_records(payload):
        if code == 0x88:
            pool = strings_from_constant_pool(action_payload)
        elif code == 0x96:
            stack.extend(push_values(action_payload, pool))
        elif code == 0x1C:  # GetVariable
            name = pop(stack)
            name_text = name if isinstance(name, str) else render(name)
            reads.append(name_text)
            stack.append({"var": name_text})
        elif code == 0x1D:  # SetVariable
            value = pop(stack)
            name = pop(stack)
            name_text = name if isinstance(name, str) else render(name)
            writes.append({"name": name_text, "value": render(value), "offset": offset})
        elif code == 0x30:  # RandomNumber
            maximum = pop(stack)
            expression = f"random({render(maximum)})"
            random_expressions.append(expression)
            stack.append({"expr": expression})
        elif code in (0x0A, 0x47):
            binary(stack, "+")
        elif code == 0x0B:
            binary(stack, "-")
        elif code == 0x0C:
            binary(stack, "*")
        elif code == 0x0D:
            binary(stack, "/")
        elif code == 0x21:
            binary(stack, "++")
        elif code in (0x0E, 0x13, 0x49):
            binary(stack, "==")
        elif code in (0x0F, 0x48):
            binary(stack, "<")
        elif code == 0x67:
            binary(stack, ">")
        elif code == 0x12:
            value = pop(stack)
            stack.append({"expr": f"!{render(value)}"})
        elif code in (0x18, 0x4A, 0x4B):
            # Conversion keeps enough identity for parity discovery.
            value = pop(stack)
            stack.append(value)
        elif code == 0x9D:
            condition = pop(stack)
            delta = struct.unpack_from("<h", action_payload)[0] if len(action_payload) >= 2 else 0
            conditions.append(
                {
                    "condition": render(condition),
                    "target_offset": offset + 3 + len(action_payload) + delta,
                }
            )
        elif code == 0x81 and len(action_payload) >= 2:
            gotos.append({"frame": struct.unpack_from("<H", action_payload)[0], "offset": offset})
        elif code == 0x8C:
            gotos.append({"label": _cstring(action_payload), "offset": offset})
        elif code == 0x17:
            pop(stack)
        elif code in (0x06, 0x07, 0x09, 0x99):
            # These do not consume the expression stack for the facts we keep.
            pass
        else:
            # A Flash opcode we do not model may have arbitrary stack effects.
            # Forgetting the stack is safer than manufacturing an assignment.
            stack.clear()

    return {
        "reads": sorted(set(reads), key=str.casefold),
        "writes": writes,
        "conditions": conditions,
        "random_expressions": random_expressions,
        "gotos": gotos,
    }


def inspect(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    data, header = parse_header(raw)
    tags = iter_tags(data, header.tags_offset)

    frame = 1
    label: str | None = None
    blocks: list[dict[str, object]] = []
    for tag in tags:
        if tag.code == 43:
            label = _cstring(tag.payload)
        elif tag.code == 12:
            block = analyze(tag.payload)
            block.update({"frame": frame, "label": label})
            blocks.append(block)
        elif tag.code == 1:
            frame += 1
            label = None

    return {"source": path.name, "blocks": blocks}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()

    try:
        report = inspect(args.swf)
    except (OSError, SwfError) as exc:
        print(f"swf_variables: {exc}", file=sys.stderr)
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
