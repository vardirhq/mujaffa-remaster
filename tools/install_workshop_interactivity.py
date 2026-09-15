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
    return px / 250.0 - 1.0


def stage_y(px: float) -> float:
    return 1.0 - px / 250.0


def stage_size(px: float) -> float:
    return px / 250.0


def burst() -> str:
    pts = "11,0 14,5 20,3 19,9 25,11 20,15 22,21 15,19 11,24 8,19 2,21 4,15 0,11 5,8 3,3 9,5"
    return f'<g transform="translate(2 0) scale(.72)"><polygon points="{pts}" fill="#ffd719" stroke="#111" stroke-width="1.4"/><text x="11.5" y="14" text-anchor="middle" font-size="8" font-weight="700" font-style="italic" fill="#111">ny</text></g>'


def make_button(out: Path, entry):
    """Render one category row as its own asset so the visible control is the hit target."""
    out.mkdir(parents=True, exist_ok=True)
    label = entry["label"]
    badge = burst() if label in ("BÅT-HORN", "BMW CAM") else ""
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="145" height="24" viewBox="0 0 145 24">
      {badge}
      <rect x="27" y="3" width="102" height="16" rx="3" fill="#2ca2c8" stroke="#111827" stroke-width="2"/>
      <text x="78" y="14.5" text-anchor="middle" font-family="Arial,sans-serif" font-size="10.5" font-weight="700" fill="#15151b">{label}</text>
    </svg>'''
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out / f"category-{entry['id']}.png"), output_width=580, output_height=96)


def button(entry, index):
    center_y = 137 + 25 * index
    return {
        "id": f"workshop-category-{entry['id']}",
        "name": f"Workshop Category {entry['label']}",
        "parent": "garage-ui-desktop",
        "transform_3d": transform(
            (stage_x(72.5), stage_y(center_y), 0.0),
            (stage_size(145), stage_size(24), 1.0),
        ),
        "components": {
            "sindri.ui.image": {
                "texture": f"assets/generated/workshop-ui/category-{entry['id']}.png",
                "tint": [1, 1, 1, 1],
                "anchor": "center",
                "layer": 240,
            },
            "sindri.ui.button": {"label": entry["label"]},
        },
    }


def make_panel(out: Path, entry):
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

    asset_dir = args.project / "assets" / "generated" / "workshop-ui"
    for entry in CATEGORIES:
        make_button(asset_dir, entry)
    for entry in CATEGORIES[1:]:
        make_panel(asset_dir, entry)
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
