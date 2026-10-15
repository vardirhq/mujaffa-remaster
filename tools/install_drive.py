#!/usr/bin/env python3
"""Add the original KJØR! trip: the cruise dialog, the Oslo map, the drive and its ends.

The original's drive is main-timeline frames 740 to 810 plus the map at
368-502 and the end screens at 523-549. `docs/drive.md` is the behaviour map
this installer and the two scripts it wires up are built from.

Everything here is cut from the SWF the way the title and the workshop are:

- whole screens (the map states, the cruise dialog, the end screens) are
  rendered as fixed 500x500 stage layers;
- everything that moves on the road is rendered on its own, at the scale it is
  placed with, around its own registration point, so a script can put that
  point where the original's `_x` and `_y` would be;
- frame-by-frame clips (the cousin, the girl) become sprite sheets with one
  cell per distinct pose.

Edit-text fields bound to live variables (money, cred, the district name) are
left out of the pictures and become `sindri.text` entities a script fills.

Run after `install_showroom.py`; it needs `reference-art/` from
`swf_art_extract.py`.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

import swf_title_extract as T  # noqa: E402
from swf_car_extract import IDENT  # noqa: E402

PX = 10.0 / 500.0
SCALE = 2.0
FONT = "fonts/ChakraPetch-Regular.ttf"
# The page background (the runtime's clear colour), and a sprite layer above
# every drive and trip layer.
MATTE = "assets/generated/drive/png/matte.png"
MATTE_RGB = "#242c3c"
MATTE_LAYER = 250

# Field variables a script writes. The picture leaves them empty.
LIVE_VARIABLES = {
    "../:bil_cool", "../:cool", "../:penge", "../:tilbane", "../:level",
    "../../:penge", "../../:cool", "myStatus", "kort_rolllevel", "kort_rollstatus",
}

# Map states: main-timeline frame -> (district button, next state, district, level).
# The three level-3 rows marked FIXED differ from the v1.6 bytes, which send
# `bane3_grønland` to frame 368, Holmenkollen's button back to Frogner and the
# Sinsen button back into level 2; as shipped, level 3 cannot be finished.
ROUTE = {
    368: (566, 373, "GRØNLAND", 1),
    373: (610, 378, "GRUNERLØKKA", 1),
    378: (611, 383, "SINSEN", 1),
    383: (615, 483, "TVEITA", 1),
    404: (618, 409, "GRØNLAND", 2),
    409: (619, 414, "RÅDHUSPLASSEN", 2),
    414: (621, 419, "BISLETT", 2),
    419: (624, 424, "SINSEN", 2),
    424: (627, 492, "TVEITA", 2),
    443: (628, 448, "GRØNLAND", 3),       # FIXED: v1.6 dispatches its result to 368
    448: (629, 453, "RÅDHUSPLASSEN", 3),
    453: (631, 458, "FROGNER", 3),
    458: (633, 463, "HOLMENKOLLEN", 3),   # FIXED: v1.6 button 633 sets Frogner again
    463: (624, 469, "SINSEN", 3),         # FIXED: v1.6 reuses 624, which goes to level 2
    469: (636, 502, "TVEITA", 3),
}
# Level-complete screens and the button that leaves each.
LEVEL_COMPLETE = {483: 640, 492: 643, 502: 646}
GAME_OVER = 523
GAME_OVER_BUTTON = 656
STATUS = {1: 530, 2: 534, 3: 539, 4: 544, 5: 549}
STATUS_BUTTONS = (659, 660)

# Frame 740: sprite 300 (`afslut`) holds the "Skal vi cruise?" dialog.
CRUISE_FRAME = 740
CRUISE_DIALOG = 300
CRUISE_BUTTONS = {"ja": 293, "nei": 294, "lukk": 295}

DRIVE_FRAME = 806
ROAD = 951
HUD = 1231
HUD_PARTS = {"en": 1214, "di": 1226, "kondom": 1230}
# The ENERGI bar's inside, stage x from left to right (measured on the cut).
HUD_BAR = (167.5, 253.5)
INTRO = 1204

# Which sprite each district's other cars and pedestrians come from: the frame
# labels of 1197 (`dyr`) and 1072 (`person`). 1197 spells Bislett "BISLET", so
# in the original Bislett never finds its label and keeps frame 1, the
# Grünerløkka cars; that stays.
DISTRICTS = ["GRUNERLØKKA", "GRØNLAND", "SINSEN", "RÅDHUSPLASSEN", "BISLETT", "HOLMENKOLLEN", "TVEITA", "FROGNER"]
CAR_LABELS = {"GRUNERLØKKA": 1, "FROGNER": 2, "RÅDHUSPLASSEN": 3, "SINSEN": 4, "TØYEN": 5, "GRØNLAND": 6, "BISLET": 7, "TVEITA": 8, "HOLMENKOLLEN": 9}
PERSON_LABELS = {name: index + 1 for index, name in enumerate(["GRUNERLØKKA", "GRØNLAND", "SINSEN", "RÅDHUSPLASSEN", "BISLETT", "HOLMENKOLLEN", "TVEITA", "FROGNER"])}


class Art:
    def __init__(self, project: Path) -> None:
        self.project = project
        self.reference = project / "reference-art"
        manifest = json.loads((self.reference / "manifest.json").read_text(encoding="utf-8"))
        self.shapes = {item["character_id"]: item for item in manifest["items"]}
        self.movie = T.TitleMovie(project / "mujaffa_3juni_2003.swf")
        for field in self.movie.edit_texts.values():
            if field["variable"] in LIVE_VARIABLES:
                field["text"] = ""
                self.movie.variables[field["variable"]] = ""
        self.out = project / "assets" / "generated" / "drive"
        self.manifest: dict = {"source": "mujaffa_3juni_2003.swf", "stage": [500, 500], "layers": {}, "objects": {}, "sheets": {}, "fields": {}, "buttons": {}}

    # --- flattening -----------------------------------------------------
    def draws(self, character: int, matrix=IDENT, overrides=None, skip=frozenset(), cxform=T.NO_TINT):
        return self.movie.drawables(character, matrix, cxform, "up", overrides or {}, (), frozenset(skip))

    def stage_draws(self, frame: int, skip=frozenset(), only=None, overrides=None):
        out = []
        for item in self.movie.main_display(frame):
            character = item.get("character")
            if character is None or "clip_depth" in item or character in skip:
                continue
            if only is not None and character not in only:
                continue
            out.extend(self.draws(character, item.get("matrix", IDENT), overrides, skip, item.get("cxform", T.NO_TINT)))
        return out

    def placement(self, frame: int, character: int):
        for item in self.movie.main_display(frame):
            if item.get("character") == character:
                return item.get("matrix", IDENT)
        raise SystemExit(f"character {character} is not on frame {frame}")

    # --- output ---------------------------------------------------------
    def _png(self, body_draws, view, name: str) -> dict:
        svg, unresolved = T._render(body_draws, self.movie, self.reference, self.shapes, view)
        if unresolved:
            raise SystemExit(f"{name} has unresolved shapes: {unresolved}")
        result = T._write(svg, self.out, name, view, SCALE)
        return {"png": f"assets/generated/drive/{result['png']}", "rect": [round(v, 4) for v in view]}

    def stage(self, name: str, draws) -> dict:
        entry = self._png(draws, (0.0, 0.0, 500.0, 500.0), name)
        self.manifest["layers"][name] = entry
        self.collect_fields(name, draws)
        return entry

    def object(self, name: str, draws, pad: float = 1.0) -> dict:
        box = T._bounds(draws, self.shapes, self.movie.extents)
        if box is None:
            raise SystemExit(f"{name} draws nothing")
        view = (box[0] - pad, box[2] - pad, box[1] - box[0] + 2 * pad, box[3] - box[2] + 2 * pad)
        entry = self._png(draws, view, name)
        self.manifest["objects"][name] = entry
        return entry

    def sheet(self, name: str, frames: list[list[dict]], pad: float = 1.0) -> dict:
        box = None
        for draws in frames:
            here = T._bounds(draws, self.shapes, self.movie.extents)
            box = T._union([box, here])
        rect = (box[0] - pad, box[2] - pad, box[1] - box[0] + 2 * pad, box[3] - box[2] + 2 * pad)
        width = max(1, math.ceil(rect[2] * SCALE))
        height = max(1, math.ceil(rect[3] * SCALE))
        cells: dict[str, str] = {}
        bodies: list[str] = []
        sequence: list[str] = []
        for draws in frames:
            key = json.dumps([[d["kind"], d["character"], [round(v, 4) for v in d["matrix"]]] for d in draws])
            cell = cells.get(key)
            if cell is None:
                cell = f"cell-{len(bodies):03d}"
                cells[key] = cell
                svg, unresolved = T._render(draws, self.movie, self.reference, self.shapes, rect)
                if unresolved:
                    raise SystemExit(f"{name} has unresolved shapes: {unresolved}")
                bodies.append(svg[svg.index(">") + 1 : svg.rindex("</svg>")])
            sequence.append(cell)
        columns = max(1, math.ceil(math.sqrt(len(bodies))))
        rows = max(1, math.ceil(len(bodies) / columns))
        tiles = "".join(
            f'<svg x="{(i % columns) * width}" y="{(i // columns) * height}" width="{width}" height="{height}" '
            f'viewBox="{rect[0]:.4f} {rect[1]:.4f} {rect[2]:.4f} {rect[3]:.4f}" overflow="hidden">{body}</svg>'
            for i, body in enumerate(bodies)
        )
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{columns * width}" height="{rows * height}" '
            f'viewBox="0 0 {columns * width} {rows * height}">{tiles}</svg>'
        )
        (self.out / "svg").mkdir(parents=True, exist_ok=True)
        (self.out / "png").mkdir(parents=True, exist_ok=True)
        (self.out / "svg" / f"{name}.svg").write_text(svg, encoding="utf-8")
        import cairosvg

        cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(self.out / "png" / f"{name}.png"),
                         output_width=columns * width, output_height=rows * height)
        names = [f"cell-{i:03d}" for i in range(len(bodies))]
        document = {"format_version": 1, "anchor": "center", "grid": {"columns": columns, "rows": rows, "size": [columns * width, rows * height], "names": names}}
        (self.out / "png" / f"{name}.sheet").write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        entry = {"png": f"assets/generated/drive/png/{name}.png", "rect": [round(v, 4) for v in rect], "frames": sequence}
        self.manifest["sheets"][name] = entry
        return entry

    def collect_fields(self, layer: str, draws) -> None:
        found = []
        for draw in draws:
            if draw["kind"] != "field":
                continue
            field = self.movie.edit_texts[draw["character"]]
            if field["variable"] not in LIVE_VARIABLES:
                continue
            a, b, c, d, e, f = draw["matrix"]
            x0, x1, y0, y1 = field["bounds"]
            font = self.movie.fonts.get(field["font_id"]) or {}
            units = float(font.get("units_per_em", 1024))
            ascent = font.get("ascent", units) / units * field["height"]
            found.append({
                "variable": field["variable"],
                "character": draw["character"],
                "left": round(e + a * (x0 + field["left_margin"]), 3),
                "right": round(e + a * (x1 - field["right_margin"]), 3),
                "top": round(f + d * (y0 + field["leading"]), 3),
                "baseline": round(f + d * (y0 + field["leading"] + ascent), 3),
                "size": round(field["height"] * d, 3),
                "align": field["align"],
                "color": [round(v / 255.0, 4) for v in T._apply_tint([float(v) for v in field["color"]], draw["cxform"])],
            })
        if found:
            self.manifest["fields"][layer] = found

    def button_rect(self, frame: int, button: int, display=None, matrix=IDENT):
        """The stage rectangle of a button wherever it sits on a frame, nested or not."""
        display = display if display is not None else self.movie.main_display(frame)
        found = self._find(display, button, matrix, ())
        if found is None:
            raise SystemExit(f"button {button} is not reachable on frame {frame}")
        draws = self.draws(button, found)
        box = T._bounds(draws, self.shapes, self.movie.extents)
        return [round(box[0], 3), round(box[2], 3), round(box[1] - box[0], 3), round(box[3] - box[2], 3)]

    def _find(self, display, button, matrix, seen):
        for item in display:
            child = item.get("character")
            if child is None or "clip_depth" in item:
                continue
            composed = T.mul(matrix, item.get("matrix", IDENT))
            if child == button:
                return composed
            if self.movie.types.get(child) == 39 and child not in seen:
                hit = self._find(self.movie.sprite_display(child, 1), button, composed, seen + (child,))
                if hit is not None:
                    return hit
        return None


def linear(matrix):
    a, b, c, d, _, _ = matrix
    return (a, b, c, d, 0.0, 0.0)


def sprite_frames(movie, character: int) -> int:
    from swf_car_extract import iter_tags
    return sum(1 for code, _ in iter_tags(movie.sprites[character]) if code == 1)


def render_all(art: Art) -> None:
    movie = art.movie
    stage_skip = {7}  # the invisible full-stage click shield

    # The cruise dialog over the workshop at frame 740.
    art.stage("cruise-dialog", art.draws(CRUISE_DIALOG, art.placement(CRUISE_FRAME, CRUISE_DIALOG)))
    dialog = [{"character": CRUISE_DIALOG, "matrix": art.placement(CRUISE_FRAME, CRUISE_DIALOG)}]
    for key, button in CRUISE_BUTTONS.items():
        art.manifest["buttons"][f"cruise-{key}"] = art.button_rect(CRUISE_FRAME, button, dialog)

    # The map, one picture per state, and the button that drives on from it.
    for frame, (button, _next, _district, _level) in ROUTE.items():
        art.stage(f"map-{frame}", art.stage_draws(frame, stage_skip))
        art.manifest["buttons"][f"map-{frame}"] = art.button_rect(frame, button)
    for frame, button in LEVEL_COMPLETE.items():
        art.stage(f"map-{frame}", art.stage_draws(frame, stage_skip))
        art.manifest["buttons"][f"map-{frame}"] = art.button_rect(frame, button)

    art.stage("game-over", art.stage_draws(GAME_OVER, stage_skip))
    art.manifest["buttons"]["game-over"] = art.button_rect(GAME_OVER, GAME_OVER_BUTTON)
    for tier, frame in STATUS.items():
        art.stage(f"status-{tier}", art.stage_draws(frame, stage_skip))
    for index, button in enumerate(STATUS_BUTTONS):
        art.manifest["buttons"][f"status-{index}"] = art.button_rect(STATUS[1], button)

    # The road and the HUD.
    art.stage("road", art.stage_draws(DRIVE_FRAME, only={ROAD}))
    hud = art.placement(DRIVE_FRAME, HUD)
    art.stage("hud", art.draws(HUD, hud, skip=set(HUD_PARTS.values())))
    for name, character in HUD_PARTS.items():
        for item in movie.sprite_display(HUD, 1):
            if item.get("character") == character:
                local = T.mul(hud, item.get("matrix", IDENT))
                art.manifest["objects"].setdefault("hud-anchors", {})[name] = [round(local[4], 3), round(local[5], 3)]
                frames = sprite_frames(movie, character)
                art.sheet(f"hud-{name}", [art.draws(character, linear(local), {character: n}) for n in range(1, frames + 1)])

    # The intro panel: the district title alone, then the key help, then the
    # blinking "GET READY" (frames 40-88 of sprite 1204).
    intro = art.placement(794, INTRO)
    for frame in (7, 21, 41):
        art.stage(f"intro-{frame}", art.draws(INTRO, intro, {INTRO: frame}))

    # Road objects, each at its placed scale around its own origin.
    def placed(character):
        return linear(art.placement(DRIVE_FRAME, character))

    art.object("stripes", art.draws(955, placed(955)))
    art.object("crossing", art.draws(957, placed(957)))
    art.object("junction", art.draws(959, placed(959)))
    art.object("condom", art.draws(975, placed(975)))
    art.object("gold", art.draws(436, placed(1306)))

    # The cousin (1081) and the girl (1090): every frame, so the walk, the
    # greeting, the "hej" variant and the splat play as authored.
    for name, character in (("cousin", 1081), ("girl", 1090)):
        frames = sprite_frames(movie, character)
        art.sheet(name, [art.draws(character, placed(character), {character: n}) for n in range(1, frames + 1)])

    # The player's BMW (1150), one layer per depth so options can switch.
    car = placed(1150)
    for item in movie.sprite_display(1150, 1):
        child = item.get("character")
        name = item.get("name")
        local = T.mul(car, item.get("matrix", IDENT))
        if name in ("volla", "pige"):
            # The greeting shout (1133) and the girl climbing in (1149): clips.
            frames = sprite_frames(movie, child)
            art.sheet(f"car-{name}", [art.draws(child, local, {child: n}) for n in range(1, frames + 1)])
            continue
        if name == "farve":
            # `c.setRGB(colorHEX)` paints the body one flat colour, so the body
            # is cut white and the sprite tint is the paint.
            art.object("car-farve-1", art.draws(child, local, cxform=((0.0, 0.0, 0.0, 1.0), (255.0, 255.0, 255.0, 0.0))))
            continue
        if movie.types.get(child) == 39 and name:
            for n in range(1, sprite_frames(movie, child) + 1):
                draws = art.draws(child, local, {child: n})
                if T._bounds(draws, art.shapes, movie.extents) is not None:
                    art.object(f"car-{name}-{n}", draws)
        else:
            art.object(f"car-depth-{item['depth']}", art.draws(child, local))
    art.object("car-boom", art.draws(1150, car, {1150: 4}))
    art.manifest["car_depths"] = [
        {"depth": item["depth"], "name": item.get("name"), "character": item.get("character")}
        for item in movie.sprite_display(1150, 1)
        if item.get("name") not in ("volla", "pige")
    ]

    # Mopeds (1159 > 1157, three looks) and the district cars and people.
    domi = placed(1159)
    for look in (1, 2, 3):
        art.object(f"moped-{look}", art.draws(1159, domi, {1157: look}))
    for district, label in CAR_LABELS.items():
        cars = [item for item in movie.sprite_display(1197, label) if item.get("character")]
        child = cars[0]["character"]
        local = T.mul(placed(1197), cars[0].get("matrix", IDENT))
        boom = [int(f) for f, names in _labels(movie, child).items() if "boom" in names][0]
        looks = [n for n in range(1, boom) if n % 2 == 1]
        for n in looks + list(range(boom, boom + 5)):
            draws = art.draws(child, local, {child: n})
            if T._bounds(draws, art.shapes, movie.extents) is not None:
                art.object(f"traffic-{_slug(district)}-{n}", draws)
        art.manifest.setdefault("traffic", {})[district] = {"sprite": child, "looks": looks, "boom": boom}
    for district, label in PERSON_LABELS.items():
        people = [item for item in movie.sprite_display(1072, label) if item.get("character")]
        local = T.mul(placed(1072), people[0].get("matrix", IDENT))
        art.object(f"person-{_slug(district)}", art.draws(people[0]["character"], local))


def _labels(movie, character: int) -> dict:
    from swf_car_extract import iter_tags
    labels: dict = {}
    frame = 1
    for code, payload in iter_tags(movie.sprites[character]):
        if code == 1:
            frame += 1
        elif code == 43:
            labels.setdefault(str(frame), []).append(T._cstring(payload))
    return labels


def _slug(name: str) -> str:
    return (name.lower().replace("ø", "o").replace("å", "a").replace("æ", "ae"))


# --- scene ------------------------------------------------------------------

def world_x(px: float) -> float:
    return round((px - 250.0) * PX, 4)


def world_y(px: float) -> float:
    return round((250.0 - px) * PX, 4)


def transform(position=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)) -> dict:
    return {"position": list(position), "rotation": [0.0, 0.0, 0.0, 1.0], "scale": list(scale)}


def stage_layer(entity_id, name, texture, layer, parent, disabled=False):
    entity = {"id": entity_id, "name": name, "parent": parent, "transform_3d": transform((0, 0, 0), (10.0, 10.0, 1.0)),
              "components": {"sindri.sprite": {"texture": texture, "tint": [1, 1, 1, 1], "layer": layer}}}
    if disabled:
        entity["disabled"] = True
    return entity


def child_sprite(entity_id, name, entry, layer, parent, disabled=False, texture=None):
    """A sprite whose parent is the original's registration point."""
    x, y, w, h = entry["rect"]
    entity = {"id": entity_id, "name": name, "parent": parent,
              "transform_3d": transform((round((x + w / 2) * PX, 4), round(-(y + h / 2) * PX, 4), 0.0), (round(w * PX, 4), round(h * PX, 4), 1.0)),
              "components": {"sindri.sprite": {"texture": texture or entry["png"], "tint": [1, 1, 1, 1], "layer": layer}}}
    if disabled:
        entity["disabled"] = True
    return entity


def anchor(entity_id, name, parent, x=-1000.0, y=-1000.0, disabled=False):
    entity = {"id": entity_id, "name": name, "parent": parent, "transform_3d": transform((world_x(x), world_y(y), 0.0))}
    if disabled:
        entity["disabled"] = True
    return entity


def sheet_sprite(entity_id, name, entry, layer, parent, clips: dict):
    x, y, w, h = entry["rect"]
    first = entry["frames"][0]
    return {"id": entity_id, "name": name, "parent": parent,
            "transform_3d": transform((round((x + w / 2) * PX, 4), round(-(y + h / 2) * PX, 4), 0.0), (round(w * PX, 4), round(h * PX, 4), 1.0)),
            "components": {
                "sindri.sprite": {"texture": f"{entry['png']}#{first}", "tint": [1, 1, 1, 1], "layer": layer},
                "sindri.animation.sprite": {
                    "clips": {clip: {"frames": [entry["frames"][n - 1] for n in frames], "seconds_per_frame": 1.0 / 12.0, "looping": looping}
                              for clip, (frames, looping) in clips.items()},
                    "playing": next(iter(clips)), "speed": 1.0}}}


def text(entity_id, name, parent, x, y, size, color, layer, anchor_name="top_left", value="", template=None, bounds=None):
    component = {"text": template if template is not None else value, "font": FONT, "font_size": round(size * PX, 4),
                 "line_height": round(size * 1.2 * PX, 4), "color": color, "anchor": anchor_name, "layer": layer}
    if template is not None:
        component["values"] = [0.0]
    if bounds is not None:
        component["bounds"] = [round(bounds[0] * PX, 4), round(bounds[1] * PX, 4)]
        component["wrap"] = "word"
    return {"id": entity_id, "name": name, "parent": parent, "transform_3d": transform((world_x(x), world_y(y), 0.0)),
            "components": {"sindri.text": component}}


def field_text(entity_id, name, parent, field, layer, template=None):
    align = {0: "top_left", 1: "top_right", 2: "top"}[field["align"]]
    x = {0: field["left"], 1: field["right"], 2: (field["left"] + field["right"]) / 2}[field["align"]]
    return text(entity_id, name, parent, x, field["top"] + 1.0, field["size"], field["color"], layer, align, template=template)


def hit_button(entity_id, name, label, parent):
    # A hit area laid out each frame by the trip controller; the art is behind it.
    return {"id": entity_id, "name": name, "parent": parent, "transform_3d": transform((0, 0, 0), (0.001, 0.001, 1.0)),
            "components": {"sindri.ui.shape": {"kind": "rect", "fill": [0.0, 0.0, 0.0, 0.001], "anchor": "center", "layer": 230},
                           "sindri.ui.button": {"label": label}}}


FIELD_NAMES = {
    "../:bil_cool": "BMW", "../:cool": "Cred", "../:penge": "Penger", "../:tilbane": "Bane", "../:level": "Level",
    "../../:penge": "Penger", "../../:cool": "Cred", "myStatus": "Status",
}


def build_entities(art: Art) -> list[dict]:
    m = art.manifest
    layers, objects, sheets = m["layers"], m["objects"], m["sheets"]
    out: list[dict] = []
    out.append({"id": "trip", "name": "Trip", "transform_3d": transform()})

    # The original is a 500x500 movie; Flash never drew outside it. A screen
    # that is taller or wider than square would otherwise show the road
    # scrolling past the stage and the actors parked off it, so four mattes in
    # the page's colour sit over everything outside the square.
    for side, (x, y) in {"top": (0.0, 10.0), "bottom": (0.0, -10.0), "left": (-10.0, 0.0), "right": (10.0, 0.0)}.items():
        width = 30.0 if side in ("top", "bottom") else 10.0
        out.append({"id": f"trip-matte-{side}", "name": f"Trip Matte {side.capitalize()}", "parent": "trip",
                    "transform_3d": transform((x, y, 0.0), (width, 10.0, 1.0)),
                    "components": {"sindri.sprite": {"texture": MATTE, "tint": [1, 1, 1, 1], "layer": MATTE_LAYER}}})

    # The cruise dialog (frame 740), over the workshop.
    out.append({"id": "trip-cruise", "name": "Trip Cruise", "parent": "trip", "disabled": True, "transform_3d": transform()})
    out.append(stage_layer("trip-cruise-art", "Trip Cruise Dialog", layers["cruise-dialog"]["png"], 200, "trip-cruise"))
    for key in CRUISE_BUTTONS:
        out.append(hit_button(f"trip-cruise-{key}", f"Cruise {key.capitalize()}", key.upper(), "trip-cruise"))

    # The map: one picture per state, shown one at a time.
    out.append({"id": "trip-map", "name": "Trip Map", "parent": "trip", "disabled": True, "transform_3d": transform()})
    for frame in list(ROUTE) + list(LEVEL_COMPLETE):
        out.append(stage_layer(f"trip-map-{frame}", f"Map {frame}", layers[f"map-{frame}"]["png"], 1, "trip-map", disabled=True))
    out.append(hit_button("trip-map-go", "Map Go", "KJØR", "trip-map"))
    for index, field in enumerate(m["fields"].get("map-368", [])):
        name = FIELD_NAMES.get(field["variable"])
        if name:
            template = "{}" if name in ("BMW", "Cred", "Penger", "Level") else None
            out.append(field_text(f"trip-map-field-{index}", f"Map {name}", "trip-map", field, 5, template))

    # The end screens.
    out.append({"id": "trip-over", "name": "Trip Game Over", "parent": "trip", "disabled": True, "transform_3d": transform()})
    out.append(stage_layer("trip-over-art", "Game Over Art", layers["game-over"]["png"], 1, "trip-over"))
    out.append(hit_button("trip-over-go", "Game Over Go", "OK", "trip-over"))
    out.append({"id": "trip-status", "name": "Trip Status", "parent": "trip", "disabled": True, "transform_3d": transform()})
    for tier in STATUS:
        # "Status N" is already taken by the GameState prototype's markers.
        out.append(stage_layer(f"trip-status-{tier}", f"Trip Status {tier}", layers[f"status-{tier}"]["png"], 1, "trip-status", disabled=True))
    status_field = next(f for f in m["fields"].get("status-1", []) if f["variable"] == "myStatus")
    # Frame 529: myStatus = "Du fikk " add cool add " street cred points."
    out.append(field_text("trip-status-text", "Status Text", "trip-status", status_field, 5,
                          template="Du fikk {} street cred points."))
    out.append(hit_button("trip-status-go", "Status Go", "OK", "trip-status"))

    # The drive.
    out.append({"id": "drive", "name": "Drive", "parent": "trip", "disabled": True, "transform_3d": transform()})
    out.append(stage_layer("drive-road", "Drive Road", layers["road"]["png"], 1, "drive"))
    stripes = art.placement(DRIVE_FRAME, 955)
    out.append(anchor("drive-stripes", "Drive Stripes", "drive", stripes[4], stripes[5]))
    out.append(child_sprite("drive-stripes-art", "Drive Stripes Art", objects["stripes"], 2, "drive-stripes"))
    out.append(anchor("drive-crossing", "Drive Crossing", "drive"))
    out.append(child_sprite("drive-crossing-art", "Drive Crossing Art", objects["crossing"], 3, "drive-crossing"))
    out.append(anchor("drive-junction", "Drive Junction", "drive"))
    out.append(child_sprite("drive-junction-art", "Drive Junction Art", objects["junction"], 4, "drive-junction"))
    out.append(anchor("drive-condom", "Drive Condom", "drive"))
    out.append(child_sprite("drive-condom-art", "Drive Condom Art", objects["condom"], 6, "drive-condom"))
    out.append(anchor("drive-person", "Drive Person", "drive"))
    for district in DISTRICTS:
        out.append(child_sprite(f"drive-person-{_slug(district)}", f"Drive Person {district}", objects[f"person-{_slug(district)}"], 7, "drive-person", disabled=True))
    out.append(anchor("drive-cousin", "Drive Cousin", "drive"))
    out.append(sheet_sprite("drive-cousin-art", "Drive Cousin Art", sheets["cousin"], 8, "drive-cousin",
                            {"walk": (list(range(1, 12)), True), "greet": (list(range(14, 42)), False),
                             "hej": (list(range(44, 71)), False), "splat": ([73], False)}))
    out.append(anchor("drive-girl", "Drive Girl", "drive"))
    out.append(sheet_sprite("drive-girl-art", "Drive Girl Art", sheets["girl"], 9, "drive-girl",
                            {"walk": (list(range(1, 10)), True), "stand": ([10], False), "splat": ([13], False)}))

    # The BMW: its parts in the original's depth order, options as siblings.
    out.append(anchor("drive-car", "Drive Car", "drive", 314.55, 358.7))
    layer = 10
    for item in m["car_depths"]:
        name = item["name"]
        if name:
            for key in sorted(k for k in objects if k.startswith(f"car-{name}-")):
                n = int(key.rsplit("-", 1)[1])
                out.append(child_sprite(f"drive-{key}", f"Drive Car {name} {n}", objects[key], layer, "drive-car", disabled=n != 1))
        else:
            out.append(child_sprite(f"drive-car-depth-{item['depth']}", f"Drive Car Depth {item['depth']}", objects[f"car-depth-{item['depth']}"], layer, "drive-car"))
        layer += 1
    volla = len(sheets["car-volla"]["frames"])
    out.append(sheet_sprite("drive-car-volla", "Drive Car Volla", sheets["car-volla"], layer, "drive-car",
                            {"idle": ([1], False), "shout": (list(range(1, volla + 1)), False)}))
    out.append(sheet_sprite("drive-car-girl", "Drive Car Girl", sheets["car-pige"], layer + 1, "drive-car",
                            {"idle": ([1], False), "ok": (list(range(2, 126)), False), "ok2": (list(range(28, 126)), False),
                             "flipper": (list(range(206, 222)), False)}))
    out.append(child_sprite("drive-car-boom", "Drive Car Boom", objects["car-boom"], layer + 2, "drive-car", disabled=True))

    for name, layer_index in (("gold", 22), ("gold-2", 23)):
        out.append(anchor(f"drive-{name}", f"Drive {name.capitalize()}", "drive"))
        out.append(child_sprite(f"drive-{name}-art", f"Drive {name.capitalize()} Art", objects["gold"], layer_index, f"drive-{name}"))
    out.append(anchor("drive-moped", "Drive Moped", "drive"))
    for look in (1, 2, 3):
        out.append(child_sprite(f"drive-moped-{look}", f"Drive Moped {look}", objects[f"moped-{look}"], 24, "drive-moped", disabled=look != 1))
    out.append(anchor("drive-traffic", "Drive Traffic", "drive"))
    for district, info in m["traffic"].items():
        for n in info["looks"] + list(range(info["boom"], info["boom"] + 5)):
            key = f"traffic-{_slug(district)}-{n}"
            if key in objects:
                out.append(child_sprite(f"drive-{key}", f"Drive Traffic {district} {n}", objects[key], 25, "drive-traffic", disabled=True))

    # Pop-up numbers: +N for the cousin and the girl, -25, and gold money.
    for key in ("cool", "girl-cool", "kill", "gold", "gold-2"):
        out.append(text(f"drive-pop-{key}", f"Drive Pop {key}", "drive", -1000, -1000, 22, [1.0, 1.0, 0.2, 1.0], 27, "center", template="{}"))

    out.append(stage_layer("drive-hud", "Drive HUD", layers["hud"]["png"], 30, "drive"))
    anchors = objects["hud-anchors"]
    # The ENERGI cover (1214) slides right over the bar under a mask, which
    # the cut ignores; the drive controller stretches it over the bar instead.
    en_x, en_y = anchors["en"]
    ex, ey, ew, eh = sheets["hud-en"]["rect"]
    out.append({"id": "drive-hud-en", "name": "Drive HUD en", "parent": "drive",
                "transform_3d": transform((world_x(HUD_BAR[0]), world_y(en_y + ey + eh / 2), 0.0), (0.0, round(eh * PX, 4), 1.0)),
                "components": {"sindri.sprite": {"texture": sheets["hud-en"]["png"], "tint": [1, 1, 1, 1], "layer": 31}}})
    for name in ("di", "kondom"):
        x, y = anchors[name]
        out.append(anchor(f"drive-hud-{name}", f"Drive HUD {name}", "drive", x, y))
        clips = {f"f{n}": ([n], False) for n in range(1, len(sheets[f"hud-{name}"]["frames"]) + 1)}
        out.append(sheet_sprite(f"drive-hud-{name}-art", f"Drive HUD {name} Art", sheets[f"hud-{name}"], 31, f"drive-hud-{name}", clips))
    for index, field in enumerate(m["fields"].get("hud", [])):
        name = FIELD_NAMES.get(field["variable"])
        if name:
            template = "{}" if name in ("Cred", "Penger", "Level") else ("{.1}" if name == "BMW" else None)
            out.append(field_text(f"drive-hud-field-{index}", f"Drive HUD {name}", "drive", field, 32, template))
    for frame in (7, 21, 41):
        out.append(stage_layer(f"drive-intro-{frame}", f"Drive Intro {frame}", layers[f"intro-{frame}"]["png"], 40, "drive", disabled=True))
    intro_field = next((f for f in m["fields"].get("intro-21", []) if f["variable"] == "../:tilbane"), None)
    if intro_field:
        out.append(field_text("drive-intro-district", "Drive Intro District", "drive", intro_field, 41))

    for script, source, name in (
        ("trip-controller", "scripts/trip_controller.decay", "TripController"),
        ("drive-controller", "scripts/drive_controller.decay", "DriveController"),
    ):
        out.append({"id": script, "name": script.replace("-", " ").title(), "transform_3d": transform(),
                    "components": {"sindri.script": {"source": source, "script": name, "properties": {}, "enabled": True}}})
    return out


def install(project: Path) -> None:
    art = Art(project)
    render_all(art)
    import cairosvg

    cairosvg.svg2png(bytestring=f'<svg xmlns="http://www.w3.org/2000/svg" width="8" height="8"><rect width="8" height="8" fill="{MATTE_RGB}"/></svg>'.encode(),
                     write_to=str(project / MATTE))
    (art.out / "manifest.json").write_text(json.dumps(art.manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    scene_path = project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    owned = ("trip", "drive")
    scene["entities"] = [e for e in scene["entities"] if not str(e.get("id", "")).startswith(owned)]
    if not any(e.get("id") == "showroom-controller" for e in scene["entities"]):
        raise SystemExit("run install_showroom.py first")
    scene["entities"].extend(build_entities(art))
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    install(args.project.resolve())
    print("installed the KJØR! trip: cruise dialog, map, drive and end screens")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
