#!/usr/bin/env python3
"""Cut the thirteen UTSTYR panels, their ticks and their price tags from the SWF.

The workshop's lower panel is sprite 924 on frame 722, one labelled frame per
category. Each category's buttons live in one child clip whose frame is the
fitted option: frame N draws the red tick on option N. BILSTEREO has four such
clips, one per speaker row, and LAKKERING's stripe swatches are `fartstribe`
(178), whose frames are the stripe colours.

So each panel is cut as a base picture (the panel without its stateful clips)
plus one picture per frame of each stateful clip, all as 500x500 stage layers.
`scripts/workshop_panel_art.decay` shows the frame that matches what is fitted.

Every option button also has a price tag (`koster1`..`koster5`, sprite 155)
that the button's rollover fills (`koster3:pris = 8000`) and shows. The tags are
cut with the price already in them and shown while the pointer is over the
button, as the original does. The remaster's own option buttons stay where they
are as hit areas; only their placeholder pictures are hidden.

Run last, after `install_drive.py`: it retextures the workshop's panels and
hides the placeholder pictures of the buttons the interactivity layer made.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
sys.path.insert(0, str(TOOLS))

import swf_title_extract as T  # noqa: E402
from install_drive import sprite_frames  # noqa: E402

IDENT = (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
WORKSHOP_FRAME = 722
PANEL = 924
TAG = 155
SCALE = 2.0
OUT = "assets/generated/workshop-panels"

# Category index (`workshop.category`), the remaster's label, sprite 924's
# frame, and the stateful clips with the board value each one follows.
CATEGORIES = [
    (0, "LAKKERING", 2, [(178, "stripe")]),
    (1, "BILSTEREO", 6, [(236, "front"), (243, "side"), (247, "rear"), (257, "woofer")]),
    (2, "SPOILER", 10, [(393, "spoiler")]),
    (3, "EKSOSANLEGG", 14, [(267, "exhaust")]),
    (4, "FELGER", 18, [(199, "rims")]),
    (5, "DEKK", 22, [(156, "tyres")]),
    (6, "RUTER", 26, [(277, "windows")]),
    (7, "SOLTAK", 30, [(901, "sunroof")]),
    (8, "NUMMERSKILT", 34, [(220, "plate")]),
    (9, "SETETREKK", 38, [(208, "interior")]),
    (10, "BILNIPS", 42, [(191, "trinket")]),
    (11, "BÅT-HORN", 46, [(914, "horn")]),
    (12, "BMW CAM", 51, [(923, "camera")]),
]

# The original's option buttons and the remaster's buttons that stand for them.
BUTTONS = {
    395: "Paint Change", 177: "Stripe None", 168: "Stripe White", 172: "Stripe Green", 164: "Stripe Black", 160: "Stripe Pink",
    230: "Audio Front 2", 231: "Audio Front 3", 237: "Audio Side 2", 238: "Audio Side 3",
    244: "Audio Rear 2", 245: "Audio Rear 3", 248: "Audio Woofer 1", 249: "Audio Woofer 2", 250: "Audio Woofer 3",
    391: "Spoiler 1", 390: "Spoiler 2", 385: "Spoiler 3", 384: "Spoiler 4",
    259: "Exhaust 1", 260: "Exhaust 2", 261: "Exhaust 3",
    194: "Rims Racer", 193: "Rims Krom", 192: "Rims Guld",
    145: "Tyres 1", 144: "Tyres 2", 143: "Tyres 3",
    270: "Windows 1", 269: "Windows 2", 268: "Windows 3",
    897: "Sunroof 1",
    209: "Plate Edit",
    202: "Interior 1", 201: "Interior 2", 200: "Interior 3",
    183: "Trinket 1", 182: "Trinket 2", 181: "Trinket 3", 180: "Trinket 4",
    902: "Horn 1", 903: "Horn 2",
    915: "Camera 1",
}
# Live text: the plate itself and the tag's price, which the tags carry.
LIVE_FIELDS = {"../../:nummerplade", "nummerplade1", "pris"}


def slug(label: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", label.lower().replace("å", "a")).strip("-")


def rollover_prices(raw: bytes) -> dict[int, tuple[str, int]]:
    """Button id -> (tag instance, price), from its `koster<n>:pris = <price>`."""
    from swf_inventory import iter_tags, parse_header
    from swf_script_sites import action_sites
    from swf_workshop_economy import PUSH, _decode

    data, header = parse_header(raw)
    prices: dict[int, tuple[str, int]] = {}
    for site in action_sites(iter_tags(data, header.tags_offset), header.version):
        if b"pris" not in site.payload or site.character is None:
            continue
        values = [v for code, argument in _decode(site.payload) if code == PUSH and argument for v in argument]
        for name, value in zip(values, values[1:]):
            hit = re.fullmatch(r"(?:\.\./)*(koster\d):pris", name) if isinstance(name, str) else None
            if hit and isinstance(value, (int, float)):
                prices[site.character] = (hit.group(1), int(value))
    return prices


class Panels:
    def __init__(self, project: Path) -> None:
        self.project = project
        self.reference = project / "reference-art"
        manifest = json.loads((self.reference / "manifest.json").read_text(encoding="utf-8"))
        self.shapes = {item["character_id"]: item for item in manifest["items"]}
        self.movie = T.TitleMovie(project / "mujaffa_3juni_2003.swf")
        self.out = project / OUT
        for field in self.movie.edit_texts.values():
            if field["variable"] in LIVE_FIELDS:
                field["text"] = ""
        self.matrix = next(item["matrix"] for item in self.movie.main_display(WORKSHOP_FRAME) if item.get("character") == PANEL)

    def render(self, name: str, draws, view=(0.0, 0.0, 500.0, 500.0)) -> dict:
        svg, unresolved = T._render(draws, self.movie, self.reference, self.shapes, view)
        if unresolved:
            raise SystemExit(f"{name} has unresolved shapes: {unresolved}")
        result = T._write(svg, self.out, name, view, SCALE)
        return {"png": f"{OUT}/{result['png']}", "rect": [round(v, 3) for v in view]}

    def walk(self, character: int, frame: int, matrix, overrides, parent=None, found=None):
        """Every placement under a clip: (character, name, matrix, parent clip)."""
        found = [] if found is None else found
        for item in self.movie.sprite_display(character, overrides.get(character, frame)):
            child = item.get("character")
            if child is None or "clip_depth" in item:
                continue
            composed = T.mul(matrix, item.get("matrix", IDENT))
            found.append((child, item.get("name"), composed, character))
            if self.movie.types.get(child) == 39 and child != TAG:
                self.walk(child, 1, composed, overrides, child, found)
        return found

    def placement(self, frame: int, character: int):
        for child, _, matrix, _ in self.walk(PANEL, frame, self.matrix, {PANEL: frame}):
            if child == character:
                return matrix
        raise SystemExit(f"sprite {character} is not in panel frame {frame}")

    def tag(self, category: int, button: str, character: int, price, matrix, placed, parent) -> dict:
        """The `koster<n>` tag beside a button, cut with its price in it."""
        tag_name, amount = price
        tags = [m for c, n, m, par in placed if c == TAG and n == tag_name and par == parent]
        if len(tags) != 1:
            raise SystemExit(f"{button}: button {character} has {len(tags)} `{tag_name}` tags")
        prices = [field for field in self.movie.edit_texts.values() if field["variable"] == "pris"]
        for field in prices:
            field["text"] = f"{amount}"
        draws = self.movie.drawables(TAG, tags[0], T.NO_TINT, "up", {}, (), frozenset())
        box = T._bounds(draws, self.shapes, self.movie.extents)
        entry = self.render(f"tag-{slug(button)}", draws, (box[0] - 1.0, box[2] - 1.0, box[1] - box[0] + 2.0, box[3] - box[2] + 2.0))
        for field in prices:
            field["text"] = ""
        box = T._bounds(self.movie.drawables(character, matrix, T.NO_TINT, "up", {}, (), frozenset()), self.shapes, self.movie.extents)
        return {"button": button, "source_button": character, "price": amount, "category": category, "tag": entry,
                "hit": [round(box[0], 2), round(box[2], 2), round(box[1] - box[0], 2), round(box[3] - box[2], 2)]}


def cut(project: Path) -> dict:
    p = Panels(project)
    prices = rollover_prices((project / "mujaffa_3juni_2003.swf").read_bytes())
    manifest: dict = {"source": "mujaffa_3juni_2003.swf", "panels": [], "tags": []}
    for index, label, frame, clips in CATEGORIES:
        name = slug(label)
        stateful = {character for character, _ in clips}
        base = p.movie.drawables(PANEL, p.matrix, T.NO_TINT, "up", {PANEL: frame}, (), frozenset(stateful | {TAG}))
        panel = {"index": index, "label": label, "base": p.render(f"{name}-base", base)["png"], "clips": []}
        for character, key in clips:
            matrix = p.placement(frame, character)
            states = []
            for n in range(1, sprite_frames(p.movie, character) + 1):
                draws = p.movie.drawables(character, matrix, T.NO_TINT, "up", {character: n}, (), frozenset({TAG}))
                states.append(p.render(f"{name}-{key}-{n}", draws)["png"])
            panel["clips"].append({"key": key, "sprite": character, "states": states})
        manifest["panels"].append(panel)

        # Each button's tag is the `koster<n>` beside it in the same clip. The
        # fitted option has no button in its own frame (the tick stands there),
        # so every frame of each clip is walked: the first frame's `empty`
        # stripe is only a button once a stripe is fitted. Other frames also
        # hold copies of buttons the first frame already has, under new ids.
        first = p.walk(PANEL, frame, p.matrix, {PANEL: frame})
        walks = [first] + [p.walk(PANEL, frame, p.matrix, {PANEL: frame, character: n})
                           for character, _ in clips for n in range(2, sprite_frames(p.movie, character) + 1)]
        seen: set[int] = set()
        for placed in walks:
            for character, _, matrix, parent in placed:
                if p.movie.types.get(character) != 34 or character not in prices or character in seen:
                    continue
                if character not in BUTTONS:
                    if placed is first:
                        raise SystemExit(f"{label}: button {character} has no remaster button")
                    continue
                seen.add(character)
                manifest["tags"].append(p.tag(index, BUTTONS[character], character, prices[character], matrix, placed, parent))
    return manifest


def transform(position=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)) -> dict:
    return {"position": list(position), "rotation": [0.0, 0.0, 0.0, 1.0], "scale": list(scale)}


def stage_sprite(entity_id: str, name: str, texture: str, layer: int, disabled: bool = True) -> dict:
    entity = {"id": entity_id, "name": name, "transform_3d": transform((0.0, 0.0, -4.0), (10.0, 10.0, 1.0)),
              "components": {"sindri.sprite": {"texture": texture, "tint": [1.0, 1.0, 1.0, 1.0], "layer": layer}}}
    if disabled:
        entity["disabled"] = True
    return entity


def install(project: Path, manifest: dict) -> None:
    scene_path = project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    entities = [e for e in scene["entities"] if not str(e.get("id", "")).startswith("workshop-panel-art")]
    by_name = {e.get("name"): e for e in entities}

    for panel in manifest["panels"]:
        name = slug(panel["label"])
        existing = by_name.get(f"Workshop Panel {panel['label']}")
        if existing is not None:
            # The category router shows and hides this one; it becomes the base.
            existing["components"]["sindri.sprite"]["texture"] = panel["base"]
            existing["components"]["sindri.sprite"]["tint"] = [1.0, 1.0, 1.0, 1.0]
        else:
            entities.append(stage_sprite(f"workshop-panel-art-{name}", f"Workshop Panel {panel['label']}", panel["base"], 230))
        for clip in panel["clips"]:
            for n, texture in enumerate(clip["states"], 1):
                entities.append(stage_sprite(f"workshop-panel-art-{name}-{clip['key']}-{n}",
                                             f"Workshop Panel {panel['label']} {clip['key']} {n}", texture, 231))

    px = 10.0 / 500.0
    for tag in manifest["tags"]:
        x, y, w, h = tag["tag"]["rect"]
        entities.append({"id": f"workshop-panel-art-tag-{slug(tag['button'])}", "name": f"Workshop Tag {tag['button']}", "disabled": True,
                         "transform_3d": transform((round((x + w / 2 - 250.0) * px, 4), round((250.0 - y - h / 2) * px, 4), -3.0),
                                                   (round(w * px, 4), round(h * px, 4), 1.0)),
                         "components": {"sindri.sprite": {"texture": tag["tag"]["png"], "tint": [1.0, 1.0, 1.0, 1.0], "layer": 233}}})
        # The panel art draws the button now; the remaster's own picture of
        # it would sit on top, so only its hit area is kept.
        button = by_name.get(f"Workshop {tag['button']}")
        if button is None:
            raise SystemExit(f"no remaster button `Workshop {tag['button']}`")
        button["components"]["sindri.ui.image"]["tint"] = [1.0, 1.0, 1.0, 0.0]

    # NUMMERSKILT's `edit` frame draws its own input box and `OK!`.
    for name in ("Workshop Plate Input", "Workshop Plate Confirm"):
        by_name[name]["components"]["sindri.ui.image"]["tint"] = [1.0, 1.0, 1.0, 0.0]
    # The plate as the `noedit` frame's field shows it (`../../:nummerplade`).
    display = by_name["Workshop Plate Display"]
    field = json.loads(json.dumps(display))
    field.update({"id": "workshop-panel-art-plate-field", "name": "Workshop Plate Field", "disabled": True})
    field["transform_3d"]["position"] = [round(321.0 / 250.0 - 1.0, 4), round(1.0 - 416.0 / 250.0, 4), 0.0]
    field["components"]["sindri.ui.text"]["color"] = [0.0, 0.0, 0.0, 1.0]
    field["components"]["sindri.ui.text"]["layer"] = 256
    entities.append(field)

    entities.append({"id": "workshop-panel-art-controller", "name": "Workshop Panel Art", "transform_3d": transform(),
                     "components": {"sindri.script": {"source": "scripts/workshop_panel_art.decay", "script": "WorkshopPanelArt",
                                                      "properties": {}, "enabled": True}}})
    scene["entities"] = entities
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Disabled sprites are not found by the export's texture walk.
    config = project / "sindri.toml"
    text = config.read_text(encoding="utf-8")
    head, _, tail = text.partition("\n[assets]\ninclude = ")
    included = json.loads(tail.strip()) if tail else []
    images = sorted({*included, *(f"{OUT}/png/{path.name}" for path in (project / OUT / "png").glob("*.png"))})
    config.write_text(head.rstrip() + "\n\n[assets]\ninclude = " + json.dumps(images, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    project = args.project.resolve()
    manifest = cut(project)
    (project / OUT / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    install(project, manifest)
    print(f"installed {len(manifest['panels'])} workshop panels and {len(manifest['tags'])} price tags from sprite {PANEL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
