#!/usr/bin/env python3
"""Display-list helpers that preserve Flash CXFORMWITHALPHA opacity."""
from __future__ import annotations
import struct
import swf_car_extract as base

IDENT = base.IDENT
mul = base.mul
transform_bounds = base.transform_bounds


def read_cxform_alpha(data: bytes, offset: int):
    b = base.Bits(data, offset * 8)
    has_add = b.u(1); has_mult = b.u(1); n = b.u(4)
    mult = [256, 256, 256, 256]; add = [0, 0, 0, 0]
    if has_mult: mult = [b.s(n) for _ in range(4)]
    if has_add: add = [b.s(n) for _ in range(4)]
    b.align()
    return b.off, {"mult": mult, "add": add}


def place2(payload: bytes):
    o = 0; flags = payload[o]; o += 1
    depth = struct.unpack_from("<H", payload, o)[0]; o += 2
    item = {"depth": depth, "move": bool(flags & 1)}
    if flags & 2: item["character"] = struct.unpack_from("<H", payload, o)[0]; o += 2
    if flags & 4: o, item["matrix"] = base.read_matrix(payload, o)
    if flags & 8: o, item["cxform"] = read_cxform_alpha(payload, o)
    if flags & 0x10: o += 2
    if flags & 0x20: item["name"], o = base.cstr(payload, o)
    if flags & 0x40: item["clip_depth"] = struct.unpack_from("<H", payload, o)[0]; o += 2
    return item

base.place2 = place2


def combine_alpha(parent: float, cxform) -> float:
    if not cxform: return parent
    mult = cxform["mult"][3] / 256.0
    add = cxform["add"][3]
    return max(0.0, min(1.0, parent * mult + add / 255.0))


class Movie(base.Movie):
    def leaves(self, cid: int, frame: int = 1, matrix=IDENT, path=(), overrides=None,
               skip_names=frozenset(), only_name=None, seen=(), masks=(), alpha=1.0):
        overrides = overrides or {}
        if cid in seen: return []
        kind = self.types.get(cid)
        if kind in base.SHAPE_TAGS:
            return [{"shape": cid, "matrix": matrix, "path": path, "masks": masks, "alpha": alpha}]
        if kind != 39 or cid not in self.sprites: return []
        out = []; display = self.display(cid, overrides.get(cid, frame))
        local_masks = [i for i in display if "clip_depth" in i and i.get("character") is not None]
        for item in display:
            child = item.get("character")
            if child is None or "clip_depth" in item: continue
            name = item.get("name")
            if name in skip_names or (only_name is not None and name != only_name): continue
            child_matrix = mul(matrix, item.get("matrix", IDENT))
            child_alpha = combine_alpha(alpha, item.get("cxform"))
            active = list(masks)
            for mask_item in local_masks:
                if mask_item["depth"] < item["depth"] <= mask_item["clip_depth"]:
                    active.append((mask_item["character"], mul(matrix, mask_item.get("matrix", IDENT))))
            child_path = path + ((name if name else f'#{item["depth"]}:{child}'),)
            out.extend(self.leaves(child, 1, child_matrix, child_path, overrides, skip_names,
                                   None, seen + (cid,), tuple(active), child_alpha))
        return out
