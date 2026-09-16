#!/usr/bin/env python3
"""Compose the original Mujaffa title screens from recovered SWF evidence.

`swf_title_reference.py` recovers *what* the opening timeline places.  This tool
turns that evidence into something a scene can render: it walks the main
timeline to each settled opening screen, flattens every placed character
(shapes, nested sprites, button states and static text) into stage-space vector
geometry, applies the original colour transforms, and writes one SVG/PNG per
layer plus a manifest registering each layer to the original 500x500 stage.

Two properties of the output matter more than the pixels.

*Screens are separated from controls.*  Each screen's artwork is one backdrop
layer, and every original button on it is emitted separately with its own
up/over/down renders.  That is what lets the remaster drive real hover/press
feedback and real navigation instead of shipping a screenshot with dead paint
on it.

*Navigation is recovered, not assumed.*  A control's action comes from
disassembling the button's own release handler, so `start_game`, `instructions`,
`next_page` and `previous_page` are claims the SWF makes rather than ones this
tool invents.

This file deliberately knows nothing about the workshop economy.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import struct
from pathlib import Path

from swf_car_extract import IDENT, Bits, iter_tags, mul, read_matrix, swf_tags

SHAPE_TAGS = {2, 22, 32}
TEXT_TAGS = {11, 33}
EDIT_TEXT_TAG = 37
BUTTON_TAGS = {7, 34}
FONT_TAGS = {10, 48, 75}

# An identity colour transform: multiply by one, add nothing.
NO_TINT = ((1.0, 1.0, 1.0, 1.0), (0.0, 0.0, 0.0, 0.0))

# The opening's settled states, as the main timeline's own labels and the
# frame-330 instruction run define them.
#
# `speakDone` (frame 188) is the title proper: frames 187-189 loop there
# forever, so it is where the original waits for the player. Its preloader
# sprite has to be advanced to its `done` label by hand, because the SWF
# advances it from ActionScript once loading finishes rather than from the
# timeline -- and `done` is the frame that places the two menu buttons.
#
# The instruction run is five frames deep. Frame 330 stops, and each page is
# reached by its own NextFrame/PreviousFrame button, so every frame in the run
# is a settled screen in its own right.
PRELOADER_SPRITE = 58
PRELOADER_DONE_FRAME = 5
TITLE_LABEL = "speakDone"
INSTRUCTION_FRAMES = (330, 331, 332, 333, 334)

# The title is not a still. Frames 10 to 188 are Mujaffa's welcome: the main
# timeline swaps his mouth and his gesturing arm frame by frame until the
# `speakDone` loop settles. Inside the preloader, the "TRYKK PÅ EN KNAPP"
# prompt fades out and back in forever on its own 21-frame clip.
#
# Both are recovered as animation rather than flattened into the backdrop,
# because a title screen that has stopped moving is the one thing every player
# of the original would notice.
OPENING_RANGE = (10, 188)
PROMPT_PATH = (PRELOADER_SPRITE, 57)

# How a button's recovered release handler maps onto a semantic action the
# remaster can implement without reproducing Flash's timeline.
ACTION_BY_CALL = {"gotoGame": "start_game", "gotoInstruktioner": "instructions"}


class TitleError(ValueError):
    pass


def _cstring(payload: bytes, offset: int = 0) -> str:
    end = payload.find(b"\0", offset)
    return payload[offset : end if end >= 0 else len(payload)].decode("utf-8", "replace")


def _read_cxform(payload: bytes, offset: int, alpha: bool):
    bits = Bits(payload, offset * 8)
    has_add = bits.u(1)
    has_mult = bits.u(1)
    nbits = bits.u(4)
    count = 4 if alpha else 3
    mult = [bits.s(nbits) / 256.0 for _ in range(count)] if has_mult else [1.0] * count
    add = [float(bits.s(nbits)) for _ in range(count)] if has_add else [0.0] * count
    if not alpha:
        mult.append(1.0)
        add.append(0.0)
    bits.align()
    return bits.off, (tuple(mult), tuple(add))


def tint(outer, inner):
    """Compose two colour transforms, outer applied to inner's result."""
    (om, oa), (im, ia) = outer, inner
    return (
        tuple(o * i for o, i in zip(om, im)),
        tuple(o * i + a for o, i, a in zip(om, ia, oa)),
    )


def _apply_tint(channels, transform):
    mult, add = transform
    out = []
    for value, m, a in zip(channels, mult, add):
        out.append(max(0.0, min(255.0, value * m + a)))
    return out


def _place(payload: bytes) -> dict:
    offset = 0
    flags = payload[offset]
    offset += 1
    depth = struct.unpack_from("<H", payload, offset)[0]
    offset += 2
    item: dict = {"depth": depth, "move": bool(flags & 1)}
    if flags & 2:
        item["character"] = struct.unpack_from("<H", payload, offset)[0]
        offset += 2
    if flags & 4:
        offset, item["matrix"] = read_matrix(payload, offset)
    if flags & 8:
        offset, item["cxform"] = _read_cxform(payload, offset, True)
    if flags & 0x10:
        offset += 2
    if flags & 0x20:
        item["name"] = _cstring(payload, offset)
        offset += len(item["name"].encode("utf-8")) + 1
    if flags & 0x40:
        item["clip_depth"] = struct.unpack_from("<H", payload, offset)[0]
        offset += 2
    return item


def _button_records(payload: bytes, offset: int, version: int):
    records = []
    while True:
        if offset >= len(payload):
            raise TitleError("unterminated button records")
        flags = payload[offset]
        offset += 1
        if flags == 0:
            return records
        character_id, depth = struct.unpack_from("<HH", payload, offset)
        offset += 4
        offset, matrix = read_matrix(payload, offset)
        record = {
            "character": character_id,
            "depth": depth,
            "matrix": matrix,
            "cxform": NO_TINT,
            "up": bool(flags & 1),
            "over": bool(flags & 2),
            "down": bool(flags & 4),
            "hit": bool(flags & 8),
        }
        if version == 2:
            offset, record["cxform"] = _read_cxform(payload, offset, True)
            if flags & 0x10:
                raise TitleError("button filter lists are not supported")
            if flags & 0x20:
                offset += 1
        records.append(record)


def _button_action(payload: bytes, offset: int) -> str | None:
    """Classify a button's release handler into a semantic navigation action."""
    if offset is None or offset >= len(payload):
        return None
    actions = payload[offset:]
    cursor = 0
    while cursor + 4 <= len(actions):
        size = struct.unpack_from("<H", actions, cursor)[0]
        end = cursor + size if size else len(actions)
        body = actions[cursor + 4 : end]
        action = _classify(body)
        if action is not None:
            return action
        if not size:
            break
        cursor += size
    return None


def _classify(body: bytes) -> str | None:
    pool: list[str] = []
    pushed: list[str] = []
    offset = 0
    while offset < len(body):
        code = body[offset]
        offset += 1
        if code == 0:
            break
        payload = b""
        if code >= 0x80:
            length = struct.unpack_from("<H", body, offset)[0]
            offset += 2
            payload = body[offset : offset + length]
            offset += length
        if code == 0x88:
            count = struct.unpack_from("<H", payload, 0)[0]
            cursor = 2
            pool = []
            for _ in range(count):
                value = _cstring(payload, cursor)
                pool.append(value)
                cursor += len(value.encode("utf-8")) + 1
        elif code == 0x96:
            cursor = 0
            while cursor < len(payload):
                kind = payload[cursor]
                cursor += 1
                if kind == 0:
                    value = _cstring(payload, cursor)
                    pushed.append(value)
                    cursor += len(value.encode("utf-8")) + 1
                elif kind == 8:
                    index = payload[cursor]
                    cursor += 1
                    pushed.append(pool[index] if index < len(pool) else "")
                elif kind == 9:
                    index = struct.unpack_from("<H", payload, cursor)[0]
                    cursor += 2
                    pushed.append(pool[index] if index < len(pool) else "")
                else:
                    cursor += {1: 4, 2: 0, 3: 0, 4: 1, 5: 1, 6: 8, 7: 4}.get(kind, len(payload))
        elif code == 0x9E:  # Call
            for value in reversed(pushed):
                if value in ACTION_BY_CALL:
                    return ACTION_BY_CALL[value]
        elif code == 0x04:  # NextFrame
            return "next_page"
        elif code == 0x05:  # PreviousFrame
            return "previous_page"
    return None


def _edit_text(payload: bytes) -> dict:
    """Decode a DefineEditText's layout, style and the text it starts with."""
    bits = Bits(payload, 2 * 8)
    nbits = bits.u(5)
    edges = [bits.s(nbits) / 20.0 for _ in range(4)]
    bits.align()
    offset = bits.off
    first, second = payload[offset], payload[offset + 1]
    offset += 2
    field: dict = {
        "bounds": (edges[0], edges[1], edges[2], edges[3]),
        "font_id": None,
        "height": 12.0,
        "color": (0, 0, 0, 255),
        "align": 0,
        "left_margin": 0.0,
        "right_margin": 0.0,
        "indent": 0.0,
        "leading": 0.0,
        "text": "",
        "variable": "",
    }
    if first & 0x01:  # HasFont
        field["font_id"] = struct.unpack_from("<H", payload, offset)[0]
        field["height"] = struct.unpack_from("<H", payload, offset + 2)[0] / 20.0
        offset += 4
    if first & 0x04:  # HasTextColor
        field["color"] = tuple(payload[offset : offset + 4])
        offset += 4
    if first & 0x02:  # HasMaxLength
        offset += 2
    if second & 0x20:  # HasLayout
        field["align"] = payload[offset]
        field["left_margin"] = struct.unpack_from("<H", payload, offset + 1)[0] / 20.0
        field["right_margin"] = struct.unpack_from("<H", payload, offset + 3)[0] / 20.0
        field["indent"] = struct.unpack_from("<H", payload, offset + 5)[0] / 20.0
        field["leading"] = struct.unpack_from("<h", payload, offset + 7)[0] / 20.0
        offset += 9
    field["variable"] = _cstring(payload, offset)
    offset += len(field["variable"].encode("utf-8")) + 1
    if first & 0x80:  # HasText
        field["text"] = _cstring(payload, offset)
    return field


def _string_variables(payload: bytes) -> dict[str, str]:
    """Recover `variable = "literal"` assignments from a timeline action block.

    A dynamic field shows what the movie put in it, not what it was authored
    with: the opening's version stamp is authored as 1.5 and set to 1.6 on the
    first frame. Reading the assignment is how the recovered title shows what a
    player of the original sees.
    """
    found: dict[str, str] = {}
    pool: list[str] = []
    pushed: list[str] = []
    offset = 0
    while offset < len(payload):
        code = payload[offset]
        offset += 1
        if code == 0:
            break
        body = b""
        if code >= 0x80:
            length = struct.unpack_from("<H", payload, offset)[0]
            offset += 2
            body = payload[offset : offset + length]
            offset += length
        if code == 0x88:
            count = struct.unpack_from("<H", body, 0)[0]
            cursor = 2
            pool = []
            for _ in range(count):
                value = _cstring(body, cursor)
                pool.append(value)
                cursor += len(value.encode("utf-8")) + 1
        elif code == 0x96:
            cursor = 0
            while cursor < len(body):
                kind = body[cursor]
                cursor += 1
                if kind == 0:
                    value = _cstring(body, cursor)
                    pushed.append(value)
                    cursor += len(value.encode("utf-8")) + 1
                elif kind in (8, 9):
                    width = 1 if kind == 8 else 2
                    index = body[cursor] if kind == 8 else struct.unpack_from("<H", body, cursor)[0]
                    cursor += width
                    pushed.append(pool[index] if index < len(pool) else "")
                else:
                    cursor += {1: 4, 2: 0, 3: 0, 4: 1, 5: 1, 6: 8, 7: 4}.get(kind, len(body))
                    pushed.append(None)
        elif code == 0x1D:  # SetVariable
            if len(pushed) >= 2 and isinstance(pushed[-2], str) and isinstance(pushed[-1], str):
                found[pushed[-2]] = pushed[-1]
            pushed = pushed[:-2]
        else:
            pushed = []
    return found


def _glyph_path(records, scale: float) -> str:
    commands: list[str] = []
    for record in records:
        if record["type"] == "style":
            move = record.get("move_to")
            if move is not None:
                commands.append(f"M {move[0] * scale:.4f} {move[1] * scale:.4f}")
        elif record["type"] == "line":
            to = record["to"]
            commands.append(f"L {to[0] * scale:.4f} {to[1] * scale:.4f}")
        else:
            control, to = record["control"], record["to"]
            commands.append(
                f"Q {control[0] * scale:.4f} {control[1] * scale:.4f} "
                f"{to[0] * scale:.4f} {to[1] * scale:.4f}"
            )
    return " ".join(commands)


class TitleMovie:
    """The original movie, read for everything the opening screens need."""

    def __init__(self, path: Path) -> None:
        from swf_font_reference import decode_define_font, decode_define_font2
        from swf_text_reference import decode_text_records

        data, offset = swf_tags(path)
        self.types: dict[int, int] = {}
        self.sprites: dict[int, bytes] = {}
        self.buttons: dict[int, dict] = {}
        self.texts: dict[int, dict] = {}
        self.fonts: dict[int, dict] = {}
        self.main: list[tuple[int, int, bytes]] = []
        self.labels: dict[str, int] = {}

        self.edit_texts: dict[int, dict] = {}
        self.variables: dict[str, str] = {}
        self.background = (255, 255, 255)

        frame = 1
        for code, payload in iter_tags(data, offset):
            if code == 1:
                frame += 1
                continue
            if code == 43:
                self.labels[_cstring(payload)] = frame
                continue
            if code == 9 and len(payload) >= 3:
                self.background = tuple(payload[:3])
                continue
            if code == 12:
                self.variables.update(_string_variables(payload))
                continue
            if code in (26, 28):
                self.main.append((frame, code, payload))
                continue
            if len(payload) < 2:
                continue
            character_id = struct.unpack_from("<H", payload, 0)[0]
            if code == 39:
                self.types[character_id] = code
                self.sprites[character_id] = payload[4:]
            elif code in BUTTON_TAGS:
                self.types[character_id] = code
                records = _button_records(payload, 2 if code == 7 else 5, 1 if code == 7 else 2)
                if code == 7:
                    action_offset = None
                else:
                    relative = struct.unpack_from("<H", payload, 3)[0]
                    action_offset = 3 + relative if relative else None
                self.buttons[character_id] = {
                    "records": records,
                    "action": _button_action(payload, action_offset),
                }
            elif code in TEXT_TAGS:
                self.types[character_id] = code
                bits = Bits(payload, 2 * 8)
                nbits = bits.u(5)
                edges = [bits.s(nbits) / 20.0 for _ in range(4)]
                bits.align()
                cursor, matrix = read_matrix(payload, bits.off)
                self.texts[character_id] = {
                    "bounds": (edges[0], edges[1], edges[2], edges[3]),
                    "matrix": matrix,
                    **decode_text_records(payload, cursor, 1 if code == 11 else 2),
                }
            elif code in FONT_TAGS:
                if code == 10:
                    self.fonts[character_id] = decode_define_font(payload)
                else:
                    self.fonts[character_id] = decode_define_font2(payload, code)
            elif code == EDIT_TEXT_TAG:
                self.types[character_id] = code
                self.edit_texts[character_id] = _edit_text(payload)
            elif code in SHAPE_TAGS:
                self.types[character_id] = code

    def _display(self, tags, frame: int) -> list[dict]:
        display: dict[int, dict] = {}
        current = 1
        for code, payload in tags:
            if current > frame:
                break
            if code == 1:
                current += 1
            elif code == 26:
                item = _place(payload)
                depth = item["depth"]
                merged = display.get(depth, {}).copy() if item.get("move") else {}
                merged.update({k: v for k, v in item.items() if k not in ("depth", "move")})
                merged["depth"] = depth
                display[depth] = merged
            elif code == 28:
                display.pop(struct.unpack_from("<H", payload, 0)[0], None)
        return [display[depth] for depth in sorted(display)]

    def main_display(self, frame: int) -> list[dict]:
        display: dict[int, dict] = {}
        for at, code, payload in self.main:
            if at > frame:
                break
            if code == 26:
                item = _place(payload)
                depth = item["depth"]
                merged = display.get(depth, {}).copy() if item.get("move") else {}
                merged.update({k: v for k, v in item.items() if k not in ("depth", "move")})
                merged["depth"] = depth
                display[depth] = merged
            else:
                display.pop(struct.unpack_from("<H", payload, 0)[0], None)
        return [display[depth] for depth in sorted(display)]

    def sprite_display(self, character_id: int, frame: int) -> list[dict]:
        return self._display(iter_tags(self.sprites[character_id]), frame)

    def drawables(self, character_id, matrix=IDENT, cxform=NO_TINT, state="up",
                  overrides=None, seen=(), skip=frozenset()) -> list[dict]:
        """Flatten one character into stage-space shape and text draw calls.

        `skip` leaves out characters the caller is rendering separately, which is
        how a screen's backdrop is drawn without the controls painted into it --
        including the two menu buttons, which live inside the preloader sprite
        rather than on the main timeline.
        """
        overrides = overrides or {}
        if character_id in seen or character_id in skip:
            return []
        tag = self.types.get(character_id)
        if tag in SHAPE_TAGS:
            return [{"kind": "shape", "character": character_id, "matrix": matrix, "cxform": cxform}]
        if tag in TEXT_TAGS:
            return [{"kind": "text", "character": character_id, "matrix": matrix, "cxform": cxform}]
        if tag == EDIT_TEXT_TAG:
            return [{"kind": "field", "character": character_id, "matrix": matrix, "cxform": cxform}]
        if tag in BUTTON_TAGS:
            records = self.buttons[character_id]["records"]
            wanted = [r for r in records if r.get(state)] or [r for r in records if r.get("up")]
            out = []
            for record in sorted(wanted, key=lambda r: r["depth"]):
                out.extend(
                    self.drawables(
                        record["character"],
                        mul(matrix, record["matrix"]),
                        tint(cxform, record["cxform"]),
                        state,
                        overrides,
                        seen + (character_id,),
                        skip,
                    )
                )
            return out
        if tag != 39:
            return []
        out = []
        for item in self.sprite_display(character_id, overrides.get(character_id, 1)):
            child = item.get("character")
            if child is None or "clip_depth" in item:
                continue
            out.extend(
                self.drawables(
                    child,
                    mul(matrix, item.get("matrix", IDENT)),
                    tint(cxform, item.get("cxform", NO_TINT)),
                    state,
                    overrides,
                    seen + (character_id,),
                    skip,
                )
            )
        return out

    def controls(self, display, matrix=IDENT, overrides=None, seen=()) -> list[dict]:
        """Find every actionable original button reachable from a display list."""
        overrides = overrides or {}
        found = []
        for item in display:
            child = item.get("character")
            if child is None or "clip_depth" in item:
                continue
            composed = mul(matrix, item.get("matrix", IDENT))
            tag = self.types.get(child)
            if tag in BUTTON_TAGS:
                action = self.buttons[child]["action"]
                if action is not None:
                    found.append({"character": child, "action": action, "matrix": composed})
            elif tag == 39 and child not in seen:
                found.extend(
                    self.controls(
                        self.sprite_display(child, overrides.get(child, 1)),
                        composed,
                        overrides,
                        seen + (child,),
                    )
                )
        return found

    @property
    def extents(self) -> dict:
        """Bounds for the characters that carry their own, not a shape's."""
        return {**self.texts, **self.edit_texts}

    def field_svg(self, character_id: int, matrix, cxform) -> str:
        """Draw a dynamic text field with the value the movie gives it."""
        field = self.edit_texts[character_id]
        font = self.fonts.get(field["font_id"])
        value = self.variables.get(field["variable"], field["text"])
        if font is None or not value:
            return ""
        units = float(font.get("units_per_em", 1024))
        # Glyph outlines arrive divided by 20, so they take the twip-scaled
        # factor; ascent and advances are raw EM units and take the plain one.
        scale = field["height"] * 20.0 / units
        em_to_px = field["height"] / units
        by_code = {glyph.get("code"): glyph for glyph in font["glyphs"]}
        advances = font.get("advances") or []
        x0, x1, y0, _ = field["bounds"]
        # Flash lays the first line out from the top of the field: down by the
        # leading and then by the font's ascent, and in from the left margin.
        pen_x = x0 + field["left_margin"] + field["indent"]
        pen_y = y0 + field["leading"] + font.get("ascent", units) * em_to_px

        widths = []
        for character in value:
            glyph = by_code.get(ord(character))
            index = font["glyphs"].index(glyph) if glyph is not None else None
            widths.append(
                advances[index] * em_to_px
                if index is not None and index < len(advances)
                else 0.0
            )
        if field["align"] == 1:
            pen_x = x1 - field["right_margin"] - sum(widths)
        elif field["align"] == 2:
            pen_x = (x0 + x1 - sum(widths)) / 2.0

        red, green, blue, alpha = _apply_tint([float(v) for v in field["color"]], cxform)
        fill = f"#{int(red):02x}{int(green):02x}{int(blue):02x}"
        body = []
        for character, width in zip(value, widths):
            glyph = by_code.get(ord(character))
            if glyph is not None:
                path = _glyph_path(glyph["shape_records"], scale)
                if path:
                    body.append(
                        f'<path transform="translate({pen_x:.4f} {pen_y:.4f})" d="{path}" '
                        f'fill="{fill}" fill-opacity="{alpha / 255.0:.4f}" fill-rule="evenodd"/>'
                    )
            pen_x += width
        if not body:
            return ""
        values = " ".join(f"{v:.8g}" for v in matrix)
        return f'<g transform="matrix({values})">{"".join(body)}</g>'

    def text_svg(self, character_id: int, matrix, cxform) -> str:
        text = self.texts[character_id]
        body: list[str] = []
        pen_x = pen_y = 0.0
        font_id = None
        height = 12.0
        color = [0.0, 0.0, 0.0, 255.0]
        for record in text["records"]:
            if "font_id" in record:
                font_id = record["font_id"]
                height = float(record["height"])
            if "color" in record:
                rgba = record["color"]
                color = [float(rgba["r"]), float(rgba["g"]), float(rgba["b"]), float(rgba["a"])]
            if "x_offset" in record:
                pen_x = float(record["x_offset"])
            if "y_offset" in record:
                pen_y = float(record["y_offset"])
            font = self.fonts.get(font_id)
            if font is None:
                continue
            red, green, blue, alpha = _apply_tint(color, cxform)
            fill = f"#{int(red):02x}{int(green):02x}{int(blue):02x}"
            scale = height * 20.0 / float(font.get("units_per_em", 1024))
            for glyph in record["glyphs"]:
                index = glyph["index"]
                if 0 <= index < len(font["glyphs"]):
                    path = _glyph_path(font["glyphs"][index]["shape_records"], scale)
                    if path:
                        body.append(
                            f'<path transform="translate({pen_x:.4f} {pen_y:.4f})" d="{path}" '
                            f'fill="{fill}" fill-opacity="{alpha / 255.0:.4f}" fill-rule="evenodd"/>'
                        )
                pen_x += float(glyph["advance"])
        if not body:
            return ""
        values = " ".join(f"{v:.8g}" for v in mul(matrix, text["matrix"]))
        return f'<g transform="matrix({values})">{"".join(body)}</g>'


def _tint_svg(inner: str, cxform) -> str:
    """Bake a colour transform into an already-generated shape document.

    CairoSVG's filter support is too thin to lean on `feColorMatrix`, and every
    colour in these documents is an explicit literal, so the transform is
    applied to the literals instead. That is exact for solid fills, strokes and
    gradient stops alike, which is all this SWF uses.
    """
    if cxform == NO_TINT:
        return inner

    def colour(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2)
        channels = [float(int(value[i : i + 2], 16)) for i in (0, 2, 4)] + [255.0]
        red, green, blue, _ = _apply_tint(channels, cxform)
        return f'{name}="#{int(red):02x}{int(green):02x}{int(blue):02x}"'

    def opacity(match: re.Match[str]) -> str:
        name, value = match.group(1), match.group(2)
        _, _, _, alpha = _apply_tint([0.0, 0.0, 0.0, float(value) * 255.0], cxform)
        return f'{name}="{alpha / 255.0:.5f}"'

    inner = re.sub(r'\b(fill|stroke|stop-color)="#([0-9a-fA-F]{6})"', colour, inner)
    inner = re.sub(r'\b(fill-opacity|stroke-opacity|stop-opacity)="([0-9.]+)"', opacity, inner)
    return inner


def _inline_shape(reference_art: Path, info: dict, matrix, cxform, serial: int) -> str:
    svg = (reference_art / info["svg"]).read_text(encoding="utf-8")
    view = re.search(r'viewBox="([^"]+)"', svg)
    if not view:
        raise TitleError(f"shape {info['character_id']} SVG is missing a viewBox")
    vx, vy, vw, vh = (float(value) for value in view.group(1).split())
    inner = svg[svg.find(">") + 1 : svg.rfind("</svg>")]
    prefix = f"t{info['character_id']}_{serial}_"
    for old in re.findall(r'id="([^"]+)"', inner):
        inner = inner.replace(f'id="{old}"', f'id="{prefix}{old}"')
        inner = inner.replace(f"url(#{old})", f"url(#{prefix}{old})")
    inner = _tint_svg(inner, cxform)
    values = " ".join(f"{v:.8g}" for v in matrix)
    return (
        f'<g transform="matrix({values})"><svg x="{vx:.8g}" y="{vy:.8g}" width="{vw:.8g}" '
        f'height="{vh:.8g}" viewBox="{vx:.8g} {vy:.8g} {vw:.8g} {vh:.8g}" '
        f'overflow="visible">{inner}</svg></g>'
    )


def _bounds(draws, shapes: dict, texts: dict | None = None):
    box = None
    for draw in draws:
        if draw["kind"] in ("text", "field"):
            extent = texts.get(draw["character"], {}).get("bounds") if texts else None
        else:
            info = shapes.get(draw["character"])
            extent = info["bounds"] if info else None
        if extent is None:
            continue
        x0, x1, y0, y1 = extent
        a, b, c, d, e, f = draw["matrix"]
        corners = ((x0, y0), (x0, y1), (x1, y0), (x1, y1))
        xs = [a * x + c * y + e for x, y in corners]
        ys = [b * x + d * y + f for x, y in corners]
        here = (min(xs), max(xs), min(ys), max(ys))
        box = here if box is None else (
            min(box[0], here[0]), max(box[1], here[1]),
            min(box[2], here[2]), max(box[3], here[3]),
        )
    return box


def _render(draws, movie: TitleMovie, reference_art: Path, shapes: dict, view, background=None):
    body: list[str] = []
    unresolved: list[int] = []
    if background is not None:
        red, green, blue = background
        body.append(
            f'<rect x="{view[0]:.4f}" y="{view[1]:.4f}" width="{view[2]:.4f}" '
            f'height="{view[3]:.4f}" fill="#{red:02x}{green:02x}{blue:02x}"/>'
        )
    for serial, draw in enumerate(draws, start=1):
        if draw["kind"] == "text":
            body.append(movie.text_svg(draw["character"], draw["matrix"], draw["cxform"]))
            continue
        if draw["kind"] == "field":
            body.append(movie.field_svg(draw["character"], draw["matrix"], draw["cxform"]))
            continue
        info = shapes.get(draw["character"])
        if info is None:
            unresolved.append(draw["character"])
            continue
        body.append(_inline_shape(reference_art, info, draw["matrix"], draw["cxform"], serial))
    x, y, width, height = view
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{x:.4f} {y:.4f} {width:.4f} {height:.4f}">{"".join(body)}</svg>'
    )
    return svg, sorted(set(unresolved))


def _write(svg: str, out: Path, name: str, view, scale: float) -> dict:
    (out / "svg").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    svg_path = out / "svg" / f"{name}.svg"
    png_path = out / "png" / f"{name}.png"
    svg_path.write_text(svg, encoding="utf-8")
    import cairosvg

    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(png_path),
        output_width=max(1, math.ceil(view[2] * scale)),
        output_height=max(1, math.ceil(view[3] * scale)),
    )
    return {
        "svg": str(svg_path.relative_to(out)),
        "png": str(png_path.relative_to(out)),
        "stage_rect": [round(value, 4) for value in view],
    }


def _union(boxes):
    box = None
    for here in boxes:
        if here is None:
            continue
        box = here if box is None else (
            min(box[0], here[0]), max(box[1], here[1]),
            min(box[2], here[2]), max(box[3], here[3]),
        )
    return box


def _overlaps(a, b, slack=8.0):
    return not (
        a[1] + slack < b[0] or b[1] + slack < a[0]
        or a[3] + slack < b[2] or b[3] + slack < a[2]
    )


def _changing_depths(movie: TitleMovie, start: int, end: int) -> set[int]:
    depths: set[int] = set()
    for frame, code, payload in movie.main:
        if not start < frame <= end:
            continue
        depths.add(_place(payload)["depth"] if code == 26 else struct.unpack_from("<H", payload, 0)[0])
    return depths


def _opening_tracks(movie: TitleMovie, shapes: dict, painted: set[int]):
    """Split the welcome performance into independently animated regions.

    Mujaffa's mouth and his arm move on their own schedules and never overlap
    on the stage, so baking them as one sheet would mean a cell for every
    combination of the two and a sheet the size of the character. Grouping the
    changing depths by whether their artwork ever overlaps recovers the two
    regions the original animates, without this tool being told what a mouth is.
    """
    start, end = OPENING_RANGE
    depths = _changing_depths(movie, start, end)
    per_frame: dict[int, dict[int, dict]] = {}
    extents: dict[int, list] = {}
    for frame in range(start, end + 1):
        display = {item["depth"]: item for item in movie.main_display(frame)}
        placed = {}
        for depth in depths:
            item = display.get(depth)
            character = item.get("character") if item else None
            if character is None or character in painted or "clip_depth" in item:
                continue
            # A button is a control, not a performance, and the opening parks a
            # spare one off the left edge of the stage. Neither is animation.
            if movie.types.get(character) in BUTTON_TAGS:
                continue
            draws = movie.drawables(
                character, item.get("matrix", IDENT), item.get("cxform", NO_TINT)
            )
            box = _bounds(draws, shapes, movie.extents)
            if box is None or box[1] <= 0.0 or box[0] >= 500.0 or box[3] <= 0.0 or box[2] >= 500.0:
                continue
            placed[depth] = {"draws": draws, "box": box}
            extents.setdefault(depth, []).append(box)
        per_frame[frame] = placed

    groups: list[dict] = []
    for depth in sorted(extents):
        box = _union(extents[depth])
        joined = [g for g in groups if _overlaps(g["box"], box)]
        merged = {"depths": {depth}, "box": box}
        for group in joined:
            merged["depths"] |= group["depths"]
            merged["box"] = _union([merged["box"], group["box"]])
        groups = [g for g in groups if g not in joined] + [merged]

    tracks = []
    for index, group in enumerate(sorted(groups, key=lambda g: sorted(g["depths"])), start=1):
        frames = []
        for frame in range(start, end + 1):
            draws = []
            for depth in sorted(group["depths"]):
                found = per_frame[frame].get(depth)
                if found is not None:
                    draws.extend(found["draws"])
            frames.append(draws)
        tracks.append(
            {
                "name": f"opening-{index}",
                "box": group["box"],
                "frames": frames,
                "looping": False,
                "depths": sorted(group["depths"]),
            }
        )
    return tracks


def _prompt_track(movie: TitleMovie, shapes: dict):
    """The looping "TRYKK PÅ EN KNAPP" prompt, found through the preloader."""
    outer, inner = PROMPT_PATH
    stage_matrix = None
    for item in movie.main_display(movie.labels[TITLE_LABEL]):
        if item.get("character") != outer:
            continue
        for child in movie.sprite_display(outer, PRELOADER_DONE_FRAME):
            if child.get("character") == inner:
                stage_matrix = mul(item.get("matrix", IDENT), child.get("matrix", IDENT))
    if stage_matrix is None:
        raise TitleError(f"the title places no prompt clip {inner} inside sprite {outer}")

    count = len(list(iter_tags(movie.sprites[inner])))
    frames = []
    boxes = []
    frame = 1
    while True:
        display = movie.sprite_display(inner, frame)
        draws = []
        for item in display:
            character = item.get("character")
            if character is None or "clip_depth" in item:
                continue
            draws.extend(
                movie.drawables(
                    character,
                    mul(stage_matrix, item.get("matrix", IDENT)),
                    item.get("cxform", NO_TINT),
                )
            )
        frames.append(draws)
        boxes.append(_bounds(draws, shapes, movie.extents))
        if frame >= count:
            break
        after = movie.sprite_display(inner, frame + 1)
        if after == display and frame > 1:
            break
        frame += 1
        if frame > 240:
            break
    box = _union(boxes)
    if box is None:
        raise TitleError("the prompt clip has no renderable geometry")
    return {
        "name": "prompt",
        "box": box,
        "frames": frames,
        "looping": True,
        "depths": [],
        "character_id": inner,
    }


def _write_sheet(track, movie, reference_art, shapes, out, scale, frame_rate):
    """Bake one track into a sprite sheet, a slice document and a clip.

    Cells are deduplicated by the geometry they draw, because the original holds
    a pose for several frames at a time and a sheet with one cell per timeline
    frame would be mostly copies. The clip still names a cell per frame, so the
    original's irregular timing survives exactly.
    """
    pad = 1.0
    box = track["box"]
    rect = (box[0] - pad, box[2] - pad, box[1] - box[0] + 2 * pad, box[3] - box[2] + 2 * pad)
    cell_width = max(1, math.ceil(rect[2] * scale))
    cell_height = max(1, math.ceil(rect[3] * scale))

    cells: dict[str, str] = {}
    order: list[str] = []
    sequence: list[str] = []
    for draws in track["frames"]:
        key = json.dumps(
            [[d["kind"], d["character"], [round(v, 4) for v in d["matrix"]]] for d in draws],
            sort_keys=True,
        )
        name = cells.get(key)
        if name is None:
            name = f"cell-{len(order):03d}"
            cells[key] = name
            body, unresolved = _render(draws, movie, reference_art, shapes, rect)
            if unresolved:
                raise TitleError(f"{track['name']} has unresolved shapes: {unresolved}")
            order.append(body[body.index(">") + 1 : body.rindex("</svg>")])
        sequence.append(name)

    columns = max(1, math.ceil(math.sqrt(len(order))))
    rows = max(1, math.ceil(len(order) / columns))
    tiles = []
    for index, body in enumerate(order):
        column, row = index % columns, index // columns
        tiles.append(
            f'<svg x="{column * cell_width}" y="{row * cell_height}" '
            f'width="{cell_width}" height="{cell_height}" '
            f'viewBox="{rect[0]:.4f} {rect[1]:.4f} {rect[2]:.4f} {rect[3]:.4f}" '
            f'overflow="hidden">{body}</svg>'
        )
    sheet_svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" '
        f'width="{columns * cell_width}" height="{rows * cell_height}" '
        f'viewBox="0 0 {columns * cell_width} {rows * cell_height}">{"".join(tiles)}</svg>'
    )

    (out / "svg").mkdir(parents=True, exist_ok=True)
    (out / "png").mkdir(parents=True, exist_ok=True)
    name = f"title-{track['name']}"
    (out / "svg" / f"{name}.svg").write_text(sheet_svg, encoding="utf-8")
    png_path = out / "png" / f"{name}.png"
    import cairosvg

    cairosvg.svg2png(
        bytestring=sheet_svg.encode("utf-8"),
        write_to=str(png_path),
        output_width=columns * cell_width,
        output_height=rows * cell_height,
    )
    sheet = {
        "format_version": 1,
        "anchor": "center",
        "grid": {
            "columns": columns,
            "rows": rows,
            "size": [columns * cell_width, rows * cell_height],
            "names": order and [f"cell-{index:03d}" for index in range(len(order))],
        },
    }
    (out / "png" / f"{name}.sheet.json").write_text(
        json.dumps(sheet, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "id": track["name"],
        "png": f"png/{name}.png",
        "sheet": f"png/{name}.sheet.json",
        "svg": f"svg/{name}.svg",
        "stage_rect": [round(value, 4) for value in rect],
        "cells": len(order),
        "depths": track["depths"],
        "clip": {
            "frames": sequence,
            "seconds_per_frame": round(1.0 / frame_rate, 6),
            "looping": track["looping"],
        },
    }


def _control_id(screen: str, action: str) -> str:
    family = "title" if screen == "title" else "instructions"
    return f"{family}-{action.replace('_', '-')}"


def _collect_controls(movie: TitleMovie, screens: dict) -> dict:
    """Gather every actionable control, shared across the screens that show it.

    The instruction run reaches its pages through one Next and one Previous
    button rather than a fresh pair per page, so the same original character
    appears on several frames. Keeping one control per character -- and
    recording which screens it belongs to -- is what the original display list
    actually says, and it keeps the runtime scene from carrying five identical
    copies of the same button.
    """
    controls: dict[str, dict] = {}
    for name, screen in screens.items():
        for found in movie.controls(screen["display"], overrides=screen["overrides"]):
            control_id = _control_id(name, found["action"])
            existing = controls.get(control_id)
            if existing is None:
                controls[control_id] = {
                    "id": control_id,
                    "action": found["action"],
                    "character_id": found["character"],
                    "matrix": found["matrix"],
                    "screens": [name],
                }
            elif existing["character_id"] == found["character"]:
                existing["screens"].append(name)
            else:
                raise TitleError(
                    f"{control_id} is character {existing['character_id']} on "
                    f"{existing['screens'][0]} but {found['character']} on {name}"
                )
    return controls


def _hit_rect(movie: TitleMovie, control: dict, shapes: dict):
    """The rect the original button actually responds to.

    A control's artwork is wider than its hit area whenever the over state
    carries one of the original's red hover captions, and on the title those
    captions overlap the neighbouring button. Hit testing follows the button's
    own hit-test records, so hovering START SPILLET cannot be swallowed by the
    caption belonging to INSTRUKSJONER.
    """
    records = movie.buttons[control["character_id"]]["records"]
    wanted = [r for r in records if r["hit"]] or [r for r in records if r["up"]]
    draws: list[dict] = []
    for record in wanted:
        draws.extend(
            movie.drawables(
                record["character"], mul(control["matrix"], record["matrix"]), NO_TINT
            )
        )
    box = _bounds(draws, shapes, movie.extents)
    if box is None:
        raise TitleError(f"control {control['id']} has no hit geometry")
    return [round(box[0], 4), round(box[2], 4), round(box[1] - box[0], 4), round(box[3] - box[2], 4)]


def extract(swf: Path, reference_art: Path, out: Path, scale: float) -> dict:
    movie = TitleMovie(swf)
    if TITLE_LABEL not in movie.labels:
        raise TitleError(f"main timeline has no {TITLE_LABEL!r} label")
    art = json.loads((reference_art / "manifest.json").read_text(encoding="utf-8"))
    shapes = {item["character_id"]: item for item in art["items"]}
    stage = (0.0, 0.0, 500.0, 500.0)

    title_frame = movie.labels[TITLE_LABEL]
    screens = {
        "title": {
            "frame": title_frame,
            "label": TITLE_LABEL,
            "page": None,
            "overrides": {PRELOADER_SPRITE: PRELOADER_DONE_FRAME},
            "sprite_frames": {str(PRELOADER_SPRITE): PRELOADER_DONE_FRAME},
        }
    }
    for page, frame in enumerate(INSTRUCTION_FRAMES, start=1):
        screens[f"instructions-{page}"] = {
            "frame": frame,
            "label": None,
            "page": page,
            "overrides": {},
            "sprite_frames": {},
        }
    for screen in screens.values():
        screen["display"] = movie.main_display(screen["frame"])

    controls = _collect_controls(movie, screens)
    painted = {control["character_id"] for control in controls.values()}

    # The preloader sprite stops being backdrop the moment its prompt animates,
    # and Mujaffa's own 66-frame clip is held at its setup frame because the
    # main timeline draws the moving mouth and arm over the top of it.
    tracks = _opening_tracks(movie, shapes, painted)
    tracks.append(_prompt_track(movie, shapes))
    animated = {track["character_id"] for track in tracks if "character_id" in track}
    for track in tracks:
        for draws in track["frames"]:
            for draw in draws:
                animated.add(draw["character"])
    painted_in_backdrop = painted | animated

    for name, screen in screens.items():
        draws: list[dict] = []
        for item in screen["display"]:
            character = item.get("character")
            if character is None or "clip_depth" in item:
                continue
            draws.extend(
                movie.drawables(
                    character,
                    item.get("matrix", IDENT),
                    item.get("cxform", NO_TINT),
                    overrides=screen["overrides"],
                    skip=painted_in_backdrop if name == "title" else painted,
                )
            )
        svg, unresolved = _render(
            draws, movie, reference_art, shapes, stage, background=movie.background
        )
        if unresolved:
            raise TitleError(f"{name} backdrop has unresolved shapes: {unresolved}")
        screen["backdrop"] = _write(svg, out, f"{name}-backdrop", stage, scale)
        screen["backdrop"]["draw_count"] = len(draws)
        del screen["display"], screen["overrides"]

    emitted = []
    for control in controls.values():
        states = {
            state: movie.drawables(control["character_id"], control["matrix"], NO_TINT, state)
            for state in ("up", "over", "down")
        }
        box = _bounds([d for draws in states.values() for d in draws], shapes, movie.extents)
        if box is None:
            raise TitleError(f"control {control['id']} has no geometry")
        pad = 1.0
        view = (box[0] - pad, box[2] - pad, box[1] - box[0] + 2 * pad, box[3] - box[2] + 2 * pad)
        rendered = {}
        for state, draws in states.items():
            svg, unresolved = _render(draws, movie, reference_art, shapes, view)
            if unresolved:
                raise TitleError(f"{control['id']} {state} has unresolved shapes: {unresolved}")
            rendered[state] = _write(svg, out, f"{control['id']}-{state}", view, scale)
        emitted.append(
            {
                "id": control["id"],
                "action": control["action"],
                "character_id": control["character_id"],
                "screens": control["screens"],
                "art_rect": rendered["up"]["stage_rect"],
                "hit_rect": _hit_rect(movie, control, shapes),
                "states": {state: layer["png"] for state, layer in rendered.items()},
            }
        )

    animations = [
        _write_sheet(track, movie, reference_art, shapes, out, scale, 12.0) for track in tracks
    ]

    title_actions = {
        control["action"] for control in emitted if "title" in control["screens"]
    }
    for required in ("start_game", "instructions"):
        if required not in title_actions:
            raise TitleError(f"title screen recovered no {required!r} control")

    manifest = {
        "source": swf.name,
        "stage": [500.0, 500.0],
        "frame_rate": 12.0,
        "scale": scale,
        "screens": screens,
        "controls": emitted,
        "animations": animations,
        "actions": sorted({control["action"] for control in emitted}),
        "notes": [
            "Every stage_rect is in original 500x500 stage pixels, y down.",
            "A control's action is recovered from the original button's own release handler.",
            "art_rect covers every state so the three renders are registered to one rect;"
            " hit_rect is the original button's own hit-test area.",
            "An animation's clip names one cell per original 12fps frame, so repeated"
            " cells reproduce the original's irregular hold times exactly.",
            "This file deliberately contains no workshop economy data.",
        ],
    }
    out.mkdir(parents=True, exist_ok=True)
    (out / "title-manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("swf", type=Path)
    parser.add_argument("reference_art", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("--scale", type=float, default=4.0)
    args = parser.parse_args()
    manifest = extract(args.swf, args.reference_art, args.out, args.scale)
    print(
        f"composed {len(manifest['screens'])} original opening screens with "
        f"{len(manifest['controls'])} recovered controls and "
        f"{len(manifest['animations'])} recovered animations"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
