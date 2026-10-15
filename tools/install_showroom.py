#!/usr/bin/env python3
"""Add the original SHOWROOM screen (main-timeline frame 730) beside the workshop.

The workshop is frame 722 (`køb`). Frame 730 (`showroom`) is the same stage
with the UTSTYR rail and category panel gone: room 934 instead of 867, Mujaffa
standing further left, the car 70.25 px left and 12.95 px higher at the same
scale, and panel 279 across the bottom holding edit-text 935, `beskrivelse`,
which frame 745 (`makeDescription`) fills from the car's state.

The two screens share one stage, so this installer does not build a second
scene. It groups the workshop-only world layers under `workshop-view`, adds the
frame-730 layers under a disabled `showroom-view`, and lets
`scripts/showroom_controller.decay` switch between them from the nav strip.

It also takes the baked numbers out of both chromes. Edit-texts 927, 928 and
931 are live variables in the original (`cool`, `penge`, `bil_cool`), so the
header now draws them as text a script writes rather than as pixels.

Run after `install_workshop_interactivity.py`; it needs `reference-art/` from
`swf_art_extract.py`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import cairosvg

TOOLS = Path(__file__).resolve().parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from swf_car_extract import Movie  # noqa: E402
from swf_showroom_extract import render_layer  # noqa: E402

SHOWROOM_FRAME = 730

# Main-timeline placements at frame 730, from `swf_scene_map.py`.
SHOWROOM = {
    "room": {"character": 934, "frame": 1, "matrix": (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)},
    "mujaffa": {"character": 869, "frame": 1, "matrix": (0.5999908447265625, 0.0, 0.0, 0.5999908447265625, 352.95, 157.7)},
    "panel": {"character": 279, "frame": 1, "matrix": (1.0, 0.0, 0.0, 1.0812835693359375, 200.9, 404.35)},
}

# Character 875 (`bil`) at frame 722 and frame 730. Same scale; only the
# translation differs, so the showroom car is the workshop car moved.
WORKSHOP_CAR = (329.65, 193.9)
SHOWROOM_CAR = (259.4, 180.95)

# One stage pixel in world units: the fixed stage is a 10-unit square for 500 px.
PX = 10.0 / 500.0

# Edit-text 935 (`beskrivelse`): field bounds (-2, 429.2) x (-2, 112.25) in its
# own space, placed at (14.75, 340.65) scaled (1.1089, 1.0327). Arial Bold 11,
# leading 2, black, word-wrapped. Flash insets text 2 px inside the field.
DESCRIPTION_MATRIX = (1.1088714599609375, 1.032684326171875, 14.75, 340.65)
DESCRIPTION_FIELD = (-2.0, 429.2, -2.0, 112.25)

# Edit-texts 927 (`cool`), 928 (`penge`) and 931 (`bil_cool`): Arial Bold 20,
# colour #99ffff, placed at scale 0.81. They sit on the header strip at the
# positions the chrome used to bake its numbers.
HEADER_FONT_PX = 20.0 * 0.80999755859375
HEADER_COLOUR = [153 / 255, 1.0, 1.0, 1.0]
HEADER = {
    "penge": {"name": "Header Penger", "x": 204.0},
    "bil_cool": {"name": "Header BMW", "x": 309.0},
    "cool": {"name": "Header Street Cred", "x": 469.0},
}
# The chrome's labels sit on y=72; a bottom-left anchor is the line box's
# bottom, which is the descender below the baseline, so the box ends lower.
HEADER_BASELINE = 76.0

# Workshop-only layers that frame 730 does not place.
WORKSHOP_ONLY = ("workshop-room", "workshop-mujaffa", "workshop-panel", "workshop-chrome")

GARAGE_LAYOUT_FIXED = '''    fn refresh_layout() {
        World.set_active(this.desktop, true);
        World.set_active(this.mobile, false);
        let car = this.car;
        car.transform.position.x = 0.0;
        car.transform.position.y = 0.0;
        car.transform.scale.x = 1.0;
        car.transform.scale.y = 1.0;
    }'''

GARAGE_LAYOUT_VIEWS = f'''    fn refresh_layout() {{
        // `workshop.view` is 1 on the frame-730 showroom, which hides the
        // UTSTYR rail and its controls and moves the car to its frame-730 place.
        // 2 is the KJØR! dialog over the workshop; from 3 on (map, drive, end
        // screens) the trip covers the stage and the garage car is put away.
        // 7 is "Bhaias Verksted", where the arrival sequence drives the car.
        let view = Game.get("workshop.view", 0.0);
        let showroom = view == 1.0;
        World.set_active(this.desktop, view == 0.0);
        World.set_active(this.mobile, false);
        let car = this.car;
        World.set_active(car, view <= 2.0 || view == 7.0);
        if view == 7.0 {{ return; }}
        car.transform.position.x = 0.0;
        car.transform.position.y = 0.0;
        if showroom {{
            car.transform.position.x = {(SHOWROOM_CAR[0] - WORKSHOP_CAR[0]) * PX:.4f};
            car.transform.position.y = {(WORKSHOP_CAR[1] - SHOWROOM_CAR[1]) * PX:.4f};
        }}
        car.transform.scale.x = 1.0;
        car.transform.scale.y = 1.0;
    }}'''


def transform(position=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)) -> dict:
    return {"position": list(position), "rotation": [0.0, 0.0, 0.0, 1.0], "scale": list(scale)}


def world_x(px: float) -> float:
    return round((px - 250.0) * PX, 4)


def world_y(px: float) -> float:
    return round((250.0 - px) * PX, 4)


def stage_sprite(entity_id: str, name: str, texture: str, layer: int, parent: str) -> dict:
    return {
        "id": entity_id,
        "name": name,
        "parent": parent,
        "transform_3d": transform((0.0, 0.0, 0.0), (10.0, 10.0, 1.0)),
        "components": {
            "sindri.sprite": {"texture": texture, "tint": [1, 1, 1, 1], "layer": layer},
            "sindri.tags": {"tags": ["showroom-parity", "fixed-500-stage"]},
        },
    }


def header_svg(active: str) -> str:
    """The header and nav strip shared by both screens, with no numbers in it."""

    def tab(x: float, width: float, label: str) -> str:
        on = label == active
        fill, stroke, ink = ("#51ebef", "#16395f", "#102345") if on else ("#1b6f96", "#53eff2", "#d8f5f7")
        return (
            f'<rect x="{x}" y="474" width="{width}" height="20" rx="6" fill="{fill}" stroke="{stroke}" stroke-width="2"/>'
            f'<text x="{x + width / 2}" y="489" text-anchor="middle" font-size="14" font-weight="700" fill="{ink}">{label}</text>'
        )

    return (
        '<rect x="0" y="0" width="500" height="31" fill="#070936"/><rect x="0" y="31" width="500" height="25" fill="#41608d"/>'
        '<text x="314" y="52" text-anchor="middle" font-size="24" font-weight="700" fill="#30517d">BHAIAS VERKSTED</text>'
        '<rect x="0" y="56" width="500" height="24" fill="#2d9dc0"/>'
        '<text x="151" y="72" font-size="10.5" font-weight="700" fill="#111">PENGER:</text>'
        '<text x="269" y="72" font-size="10.5" font-weight="700" fill="#111">BMW:</text>'
        '<text x="372" y="72" font-size="10.5" font-weight="700" fill="#111">STREET CRED:</text>'
        '<rect x="0" y="468" width="500" height="32" fill="#070936"/>'
        + tab(205, 105, "VERKSTED")
        + tab(315, 105, "SHOWROOM")
        + tab(424, 69, "KJØR!")
    )


def render_showroom_chrome(out: Path) -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000" viewBox="0 0 500 500">'
        + header_svg("SHOWROOM")
        + "</svg>"
    )
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=2000, output_height=2000)


def description_entity() -> dict:
    sx, sy, tx, ty = DESCRIPTION_MATRIX
    x0, x1, y0, y1 = DESCRIPTION_FIELD
    left = tx + sx * (x0 + 2.0)
    right = tx + sx * (x1 - 2.0)
    top = ty + sy * (y0 + 2.0)
    bottom = ty + sy * (y1 - 2.0)
    return {
        "id": "showroom-description",
        "name": "Showroom Description",
        "parent": "showroom-view",
        "transform_3d": transform((world_x(left), world_y(top), 0.0)),
        "components": {
            "sindri.text": {
                "text": "",
                "font": "fonts/LiberationSans-Bold.ttf", "bold": True,
                "font_size": round(11.0 * sy * PX, 4),
                "line_height": round((11.0 + 2.0) * sy * PX, 4),
                "color": [0.0, 0.0, 0.0, 1.0],
                "anchor": "top_left",
                "bounds": [round((right - left) * PX, 4), round((bottom - top) * PX, 4)],
                "wrap": "word",
                "layer": 26,
            }
        },
    }


def header_entity(key: str, spec: dict) -> dict:
    return {
        "id": f"header-{key.replace('_', '-')}",
        "name": spec["name"],
        "transform_3d": transform((world_x(spec["x"]), world_y(HEADER_BASELINE), 0.0)),
        "components": {
            "sindri.text": {
                "text": "{}",
                "font": "fonts/LiberationSans-Bold.ttf", "bold": True,
                "font_size": round(HEADER_FONT_PX * 0.8 * PX, 4),
                "line_height": round(HEADER_FONT_PX * PX, 4),
                "color": HEADER_COLOUR,
                "anchor": "bottom_left",
                "layer": 125,
                "values": [0.0],
            }
        },
    }


def nav_button(entity_id: str, name: str, label: str) -> dict:
    # Laid out every frame by the showroom controller, like the category rail.
    return {
        "id": entity_id,
        "name": name,
        "transform_3d": transform((0.0, 0.0, 0.0), (0.001, 0.001, 1.0)),
        "components": {"sindri.ui.button": {"label": label}},
    }


def install(project: Path, scale: float) -> None:
    swf = project / "mujaffa_3juni_2003.swf"
    raw_art = project / "reference-art"
    manifest = json.loads((raw_art / "manifest.json").read_text(encoding="utf-8"))
    items = {item["character_id"]: item for item in manifest["items"]}
    movie = Movie(swf)

    out = project / "assets" / "generated" / "showroom-730"
    outputs = {}
    for name, spec in SHOWROOM.items():
        outputs[name] = render_layer(movie, raw_art, items, spec, name, out, scale)
        if outputs[name]["unresolved"]:
            raise SystemExit(f"showroom layer {name} has unresolved shapes: {outputs[name]['unresolved']}")
    render_showroom_chrome(out / "png" / "chrome.png")
    (out / "manifest.json").write_text(
        json.dumps(
            {
                "source": swf.name,
                "main_timeline_frame": SHOWROOM_FRAME,
                "label": "showroom",
                "canvas": [500, 500],
                "outputs": outputs,
                "car": {"workshop": list(WORKSHOP_CAR), "showroom": list(SHOWROOM_CAR)},
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )

    scene_path = project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    owned = ("workshop-view", "showroom-view", "showroom-", "header-", "nav-")
    scene["entities"] = [e for e in scene["entities"] if not str(e.get("id", "")).startswith(owned)]

    ids = {e.get("id") for e in scene["entities"]}
    missing = [i for i in WORKSHOP_ONLY if i not in ids]
    if missing:
        raise SystemExit(f"workshop layers missing; run the workshop installers first: {missing}")
    for entity in scene["entities"]:
        entity_id = str(entity.get("id", ""))
        if entity_id in WORKSHOP_ONLY or (entity_id.startswith("workshop-panel-") and "sindri.sprite" in entity.get("components", {})):
            entity["parent"] = "workshop-view"

    png = "assets/generated/showroom-730/png"
    scene["entities"].extend(
        [
            {"id": "workshop-view", "name": "Workshop View", "transform_3d": transform(), "components": {"sindri.tags": {"tags": ["view"]}}},
            {"id": "showroom-view", "name": "Showroom View", "disabled": True, "transform_3d": transform(), "components": {"sindri.tags": {"tags": ["view"]}}},
            # Frame 730 depths: room 92 < Mujaffa 93 < panel 287 < text 290 < car 431.
            stage_sprite("showroom-room", "Original Showroom Room", f"{png}/room.png", -6, "showroom-view"),
            stage_sprite("showroom-mujaffa", "Original Showroom Mujaffa", f"{png}/mujaffa.png", 20, "showroom-view"),
            stage_sprite("showroom-panel", "Original Showroom Panel", f"{png}/panel.png", 25, "showroom-view"),
            stage_sprite("showroom-chrome", "Showroom Chrome", f"{png}/chrome.png", 120, "showroom-view"),
            description_entity(),
            *(header_entity(key, spec) for key, spec in HEADER.items()),
            nav_button("nav-verksted", "Nav Verksted", "VERKSTED"),
            nav_button("nav-showroom", "Nav Showroom", "SHOWROOM"),
            nav_button("nav-kjor", "Nav Kjor", "KJØR!"),
            {
                "id": "showroom-controller",
                "name": "Showroom Controller",
                "transform_3d": transform(),
                "components": {
                    "sindri.script": {
                        "source": "scripts/showroom_controller.decay",
                        "script": "ShowroomController",
                        "properties": {},
                        "enabled": True,
                    }
                },
            },
        ]
    )
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    garage = project / "scripts" / "garage.decay"
    text = garage.read_text(encoding="utf-8")
    if GARAGE_LAYOUT_VIEWS not in text:
        if GARAGE_LAYOUT_FIXED not in text:
            raise SystemExit("Garage.refresh_layout changed; run install_workshop_parity.py first or update this installer")
        garage.write_text(text.replace(GARAGE_LAYOUT_FIXED, GARAGE_LAYOUT_VIEWS, 1), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--project", type=Path, default=Path("."))
    ap.add_argument("--scale", type=float, default=4.0)
    args = ap.parse_args()
    install(args.project.resolve(), args.scale)
    print(f"installed frame-{SHOWROOM_FRAME} showroom beside the frame-722 workshop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
