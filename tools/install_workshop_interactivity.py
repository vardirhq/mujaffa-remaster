#!/usr/bin/env python3
"""Add interaction hit targets for the fixed 500x500 workshop."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from tools.workshop_catalog import CATEGORIES


def transform(position, scale):
    return {"position": list(position), "rotation": [0.0, 0.0, 0.0, 1.0], "scale": list(scale)}


def button(entry, index):
    stage_y = 137 + 25 * index
    return {
        "id": f"workshop-category-{entry['id']}",
        "name": f"Workshop Category {entry['label']}",
        "parent": "garage-ui-desktop",
        "transform_3d": transform((-0.695, 0.5 - stage_y / 500.0, 0.0), (0.20, 0.034, 1.0)),
        "components": {
            "sindri.ui.shape": {"kind": "rect", "fill": [0, 0, 0, 0.001], "anchor": "center", "layer": 240},
            "sindri.ui.button": {"label": entry["label"]},
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    scene_path = args.project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    removed = {"workshop-state", "workshop-category-controller"}
    scene["entities"] = [
        e for e in scene["entities"]
        if not str(e.get("id", "")).startswith("workshop-category-") and e.get("id") not in removed
    ]
    scene["entities"].extend(button(entry, i) for i, entry in enumerate(CATEGORIES))
    scene["entities"].append({
        "id": "workshop-state", "name": "Workshop State",
        "transform_3d": transform((0, 0, 0), (1, 1, 1)),
        "components": {"sindri.script": {
            "source": "scripts/workshop_state.decay",
            "script": "WorkshopState",
            "properties": {},
            "enabled": True,
        }},
    })
    scene["entities"].append({
        "id": "workshop-category-controller", "name": "Workshop Category Controller",
        "transform_3d": transform((0, 0, 0), (1, 1, 1)),
        "components": {"sindri.script": {
            "source": "scripts/workshop_category_controller.decay",
            "script": "WorkshopCategoryController",
            "properties": {},
            "enabled": True,
        }},
    })
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
