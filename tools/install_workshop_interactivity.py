#!/usr/bin/env python3
"""Add functional category switching to the fixed 500x500 workshop."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
import cairosvg

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.workshop_catalog import CATEGORIES


def transform(position, scale):
    return {"position": list(position), "rotation": [0.0, 0.0, 0.0, 1.0], "scale": list(scale)}


def stage_x(px: float) -> float:
    """Convert a 500px stage x coordinate to Sindri's -1..1 overlay space."""
    return px / 250.0 - 1.0


def stage_y(px: float) -> float:
    """Convert a 500px stage y coordinate to Sindri's +1..-1 overlay space."""
    return 1.0 - px / 250.0


def stage_size(px: float) -> float:
    """Convert a pixel extent on the 500px stage to overlay units."""
    return px / 250.0


def button(entry, index):
    center_y = 137 + 25 * index
    return {
        "id": f"workshop-category-{entry['id']}",
        "name": f"Workshop Category {entry['label']}",
        "parent": "garage-ui-desktop",
        # The chrome buttons are 102x17 px centred at x=78. Sindri UI transforms
        # use a two-unit-high overlay, not 0..1 normalized coordinates.
        "transform_3d": transform(
            (stage_x(78), stage_y(center_y), 0.0),
            (stage_size(102), stage_size(17), 1.0),
        ),
        "components": {
            "sindri.ui.shape": {"kind": "rect", "fill": [0, 0, 0, 0.001], "anchor": "center", "layer": 240},
            "sindri.ui.button": {"label": entry["label"]},
        },
    }


def make_panel(out: Path, entry):
    """Make a transparent full-stage overlay for categories not yet SWF-recovered.

    We deliberately show only the authentic category name. Options, prices and
    copy must come from the SWF rather than being invented by this scaffolding.
    """
    out.mkdir(parents=True, exist_ok=True)
    label = entry["label"]
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500">
      <rect x="153" y="351" width="343" height="111" rx="12" fill="#129bc4" stroke="#0b103b" stroke-width="4"/>
      <text x="176" y="380" font-family="Arial,sans-serif" font-size="18" font-weight="700" fill="#10131c">{label}</text>
    </svg>'''
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out / f"panel-{entry['id']}.png"), output_width=1000, output_height=1000)


def panel_entity(entry):
    return {
        "id": f"workshop-panel-{entry['id']}",
        "name": f"Workshop Panel {entry['label']}",
        "disabled": True,
        "transform_3d": transform((0.0, 0.0, -4.0), (10.0, 10.0, 1.0)),
        "components": {
            "sindri.sprite": {
                "texture": f"assets/generated/workshop-ui/panel-{entry['id']}.png",
                "tint": [1, 1, 1, 1],
                "layer": 230,
            }
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    scene_path = args.project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    removed = {"workshop-state", "workshop-category-controller", "workshop-category-marker", "workshop-selection-marker"}
    scene["entities"] = [
        e for e in scene["entities"]
        if not str(e.get("id", "")).startswith("workshop-category-")
        and not str(e.get("id", "")).startswith("workshop-panel-")
        and e.get("id") not in removed
    ]

    panel_dir = args.project / "assets" / "generated" / "workshop-ui"
    for entry in CATEGORIES[1:]:
        make_panel(panel_dir, entry)
        scene["entities"].append(panel_entity(entry))

    scene["entities"].extend(button(entry, i) for i, entry in enumerate(CATEGORIES))
    scene["entities"].append({
        "id": "workshop-selection-marker",
        "name": "Workshop Category Marker",
        "parent": "garage-ui-desktop",
        "transform_3d": transform((stage_x(20), stage_y(137), 0.0), (stage_size(8), stage_size(8), 1.0)),
        "components": {
            "sindri.ui.shape": {"kind": "rect", "fill": [0.05, 0.08, 0.18, 1.0], "anchor": "center", "layer": 245},
        },
    })
    scene["entities"].append({
        "id": "workshop-state", "name": "Workshop State",
        "transform_3d": transform((0, 0, 0), (1, 1, 1)),
        "components": {"sindri.script": {
            "source": "scripts/workshop_state.decay", "script": "WorkshopState",
            "properties": {}, "enabled": True,
        }},
    })
    scene["entities"].append({
        "id": "workshop-category-controller", "name": "Workshop Category Controller",
        "transform_3d": transform((0, 0, 0), (1, 1, 1)),
        "components": {"sindri.script": {
            "source": "scripts/workshop_category_controller.decay", "script": "WorkshopCategoryController",
            "properties": {}, "enabled": True,
        }},
    })
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
