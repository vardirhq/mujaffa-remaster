#!/usr/bin/env python3
"""Recover the original workshop's economy from the SWF, button by button.

Every upgrade in the 2003 game is a button whose script does the same four
things: refuse the sale unless `penge` clears a threshold, subtract the price,
move the car's `bil_cool` by the difference between the new part's coolness and
the old part's, and record the new part. That shape is the whole economy, so
this reads it back out rather than trusting a transcription:

    penge > 7999            -- the check, strict, so the price is threshold + 1
    penge = penge - 8000    -- the price
    bil_cool = bil_cool + (0.3 - daek_cool)
    daek_cool = 0.3         -- this part's contribution, replacing the old one
    daek = 3                -- the part itself

This is a symbolic reader, not a Flash VM. An action it does not model discards
the stack rather than guessing, so a site it cannot follow is reported as
unrecovered instead of quietly producing a wrong number.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

from swf_actions import action_records
from swf_inventory import SwfError, iter_tags, parse_header
from swf_script_sites import action_sites
from swf_variables import push_values

CONSTANT_POOL = 0x88
PUSH = 0x96
GET_VARIABLE = 0x1C
SET_VARIABLE = 0x1D
SUBTRACT = 0x0B
ADD2 = 0x47
GREATER = 0x67
LESS2 = 0x48
TO_NUMBER = 0x4A
NOT = 0x12


class Unknown:
    """A value the reader could not follow. Poisons anything computed from it."""

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return "<unknown>"


@dataclass
class Purchase:
    """One button's economic effect, as recovered from its script."""

    character: int | None
    origin: str
    threshold: int | None = None
    price: int | None = None
    assignments: list[tuple[str, object]] = field(default_factory=list)

    @property
    def state_variable(self) -> str | None:
        """The part this button sets, ignoring money and coolness bookkeeping."""
        for name, _ in self.assignments:
            if name != "penge" and not name.endswith("_cool"):
                return name
        return None

    @property
    def cool(self) -> tuple[str, float] | None:
        for name, value in self.assignments:
            if name.endswith("_cool") and name != "bil_cool" and isinstance(value, (int, float)):
                return name, float(value)
        return None

    @property
    def cool_delta(self) -> float | None:
        """A flat move on `bil_cool`, which is how the stereo is priced.

        Most categories keep a per-part `*_cool` and subtract the old
        contribution before adding the new one. The speakers have no such
        variable: each button adds a fixed amount, sized by how many levels the
        purchase jumps, so upgrading front speakers from 1 to 3 adds what 1 to 2
        and 2 to 3 would have added separately.
        """
        for name, value in self.assignments:
            if name != "bil_cool" or not isinstance(value, tuple):
                continue
            if value[0] == "add" and value[1] == ("var", "bil_cool") and isinstance(value[2], (int, float)):
                return float(value[2])
        return None


def _name(value: object) -> object:
    """`../../:penge` and `penge` are the same variable seen from two depths."""
    if isinstance(value, str) and ":" in value:
        return value.rsplit(":", 1)[1]
    return value


def _decode(payload: bytes) -> list[tuple[int, object]]:
    pool: list[str] = []
    decoded: list[tuple[int, object]] = []
    try:
        records = action_records(payload)
    except SwfError:
        return decoded
    for code, body, _offset in records:
        if code == CONSTANT_POOL:
            pool = _constant_pool(body)
            decoded.append((code, None))
        elif code == PUSH:
            try:
                decoded.append((code, push_values(body, pool)))
            except (SwfError, struct.error, IndexError):
                decoded.append((code, None))
        else:
            decoded.append((code, None))
    return decoded


def _constant_pool(body: bytes) -> list[str]:
    try:
        count = struct.unpack_from("<H", body)[0]
    except struct.error:
        return []
    pool, cursor = [], 2
    for _ in range(count):
        end = body.find(b"\0", cursor)
        if end < 0:
            break
        pool.append(body[cursor:end].decode("utf-8", errors="replace"))
        cursor = end + 1
    return pool


def read_purchase(site) -> Purchase:
    """Walk one action block, recording what it charges and what it sets."""
    purchase = Purchase(character=site.character, origin=site.origin)
    stack: list[object] = []

    for code, argument in _decode(site.payload):
        if code == PUSH:
            if argument is None:
                stack.clear()
                continue
            stack.extend(_name(value) for value in argument)
        elif code == GET_VARIABLE:
            if not stack:
                continue
            name = stack.pop()
            stack.append(("var", name) if isinstance(name, str) else Unknown())
        elif code == TO_NUMBER:
            pass                                   # numeric coercion, not a value change
        elif code == SUBTRACT:
            if len(stack) < 2:
                stack.clear()
                continue
            right, left = stack.pop(), stack.pop()
            stack.append(("sub", left, right))
        elif code == ADD2:
            if len(stack) < 2:
                stack.clear()
                continue
            right, left = stack.pop(), stack.pop()
            stack.append(("add", left, right))
        elif code in (GREATER, LESS2):
            if len(stack) < 2:
                stack.clear()
                continue
            right, left = stack.pop(), stack.pop()
            subject, limit = (left, right) if code == GREATER else (right, left)
            if subject == ("var", "penge") and isinstance(limit, (int, float)):
                purchase.threshold = int(limit)
            stack.append(Unknown())
        elif code == SET_VARIABLE:
            if len(stack) < 2:
                stack.clear()
                continue
            value, name = stack.pop(), stack.pop()
            if not isinstance(name, str):
                continue
            if name == "penge" and isinstance(value, tuple) and value[0] == "sub":
                _, left, right = value
                if left == ("var", "penge") and isinstance(right, (int, float)):
                    purchase.price = int(right)
            purchase.assignments.append((name, value))
        elif code == NOT:
            if stack:
                stack.pop()
            stack.append(Unknown())
        else:
            # Anything unmodelled invalidates what we thought we knew.
            stack.clear()

    return purchase


def purchases(raw: bytes) -> list[Purchase]:
    data, header = parse_header(raw)
    found = []
    for site in action_sites(iter_tags(data, header.tags_offset), header.version):
        if b"penge" not in site.payload:
            continue
        purchase = read_purchase(site)
        if purchase.price is not None:
            found.append(purchase)
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("swf", type=Path, nargs="?", default=Path("mujaffa_3juni_2003.swf"))
    parser.add_argument("--json", action="store_true", help="emit the recovered rows as JSON")
    args = parser.parse_args()

    found = purchases(args.swf.read_bytes())
    rows = [
        {
            "character": p.character,
            "state": p.state_variable,
            "price": p.price,
            "price_check": None if p.threshold is None else f"money > {p.threshold}",
            "cool_variable": p.cool[0] if p.cool else None,
            "cool_value": p.cool[1] if p.cool else None,
            "cool_delta": p.cool_delta,
            "sets": {n: v for n, v in p.assignments if not isinstance(v, tuple) and n != "penge"},
        }
        for p in found
    ]
    if args.json:
        json.dump(rows, sys.stdout, indent=2, ensure_ascii=False, sort_keys=True)
        print()
    else:
        print(f"recovered {len(rows)} priced buttons from {args.swf.name}")
        for row in sorted(rows, key=lambda r: (r["state"] or "", r["price"])):
            print(f"  {str(row['state']):24} {row['price']:>6}  {row['price_check'] or '':16} "
                  f"{row['cool_variable'] or '':20} {row['cool_value']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
