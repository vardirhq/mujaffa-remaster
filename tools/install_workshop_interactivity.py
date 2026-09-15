#!/usr/bin/env python3
"""Add functional category and LAKKERING controls to the fixed workshop."""
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
        "transform_3d": transform((stage_x(72.5), stage_y(center_y), 0.0), (stage_size(145), stage_size(24), 1.0)),
        "components": {
            "sindri.ui.image": {"texture": f"assets/generated/workshop-ui/category-{entry['id']}.png", "tint": [1, 1, 1, 1], "anchor": "center", "layer": 240},
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
        "id": f"workshop-panel-{entry['id']}", "name": f"Workshop Panel {entry['label']}", "disabled": True,
        "transform_3d": transform((0.0, 0.0, -4.0), (10.0, 10.0, 1.0)),
        "components": {"sindri.sprite": {"texture": f"assets/generated/workshop-ui/panel-{entry['id']}.png", "tint": [1, 1, 1, 1], "layer": 230}},
    }


def render_control(out: Path, name: str, width: int, height: int, body: str):
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">{body}</svg>'
    cairosvg.svg2png(bytestring=svg.encode("utf-8"), write_to=str(out / name), output_width=width * 4, output_height=height * 4)


def make_paint_controls(out: Path):
    render_control(out, "paint-change.png", 56, 38,
        '<rect x="2" y="2" width="52" height="34" rx="3" fill="#2a9ac3" stroke="#6b3150" stroke-width="2"/><text x="28" y="26" text-anchor="middle" font-family="Arial,sans-serif" font-size="18" font-weight="700" fill="#ec3345">skift</text>')
    render_control(out, "stripe-none.png", 34, 26,
        '<rect x="2" y="2" width="30" height="22" rx="5" fill="#32a8c8" stroke="#111" stroke-width="2"/><path d="M7 13 l7 7 14-20" fill="none" stroke="#e33435" stroke-width="4"/>')
    render_control(out, "stripe-white.png", 34, 26,
        '<rect x="2" y="2" width="30" height="22" rx="5" fill="#fff" stroke="#111" stroke-width="2"/><path d="M4 7 l26 16 M4 14 l22 10" stroke="#2486bf" stroke-width="4"/>')
    render_control(out, "stripe-green.png", 34, 26,
        '<rect x="2" y="2" width="30" height="22" rx="5" fill="#5fd52e" stroke="#111" stroke-width="2"/><path d="M4 6 l27 16 M4 13 l21 11" stroke="#258cc1" stroke-width="4"/>')
    render_control(out, "stripe-black.png", 34, 26,
        '<rect x="2" y="2" width="30" height="22" rx="5" fill="#111" stroke="#111" stroke-width="2"/><path d="M4 6 l26 16" stroke="#217ead" stroke-width="4"/>')
    render_control(out, "stripe-pink.png", 34, 26,
        '<rect x="2" y="2" width="30" height="22" rx="5" fill="#f66ca9" stroke="#111" stroke-width="2"/><path d="M4 6 l26 16" stroke="#267eac" stroke-width="4"/>')


def paint_control(entity_id: str, name: str, texture: str, x: float, y: float, w: float, h: float):
    return {
        "id": entity_id, "name": name, "parent": "garage-ui-desktop",
        "transform_3d": transform((stage_x(x), stage_y(y), 0.0), (stage_size(w), stage_size(h), 1.0)),
        "components": {
            "sindri.ui.image": {"texture": f"assets/generated/workshop-ui/{texture}", "tint": [1, 1, 1, 1], "anchor": "center", "layer": 250},
            "sindri.ui.button": {"label": name},
        },
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    scene_path = args.project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    removed = {"workshop-state", "workshop-category-controller", "workshop-category-marker", "workshop-selection-marker", "workshop-paint-controller"}
    scene["entities"] = [e for e in scene["entities"]
        if not str(e.get("id", "")).startswith("workshop-category-")
        and not str(e.get("id", "")).startswith("workshop-panel-")
        and not str(e.get("id", "")).startswith("workshop-paint-")
        and not str(e.get("id", "")).startswith("workshop-stripe-")
        and e.get("id") not in removed]

    asset_dir = args.project / "assets" / "generated" / "workshop-ui"
    for entry in CATEGORIES:
        make_button(asset_dir, entry)
    for entry in CATEGORIES[1:]:
        make_panel(asset_dir, entry)
        scene["entities"].append(panel_entity(entry))
    make_paint_controls(asset_dir)

    scene["entities"].extend(button(entry, i) for i, entry in enumerate(CATEGORIES))
    scene["entities"].extend([
        paint_control("workshop-paint-change", "Workshop Paint Change", "paint-change.png", 205, 433, 56, 38),
        paint_control("workshop-stripe-none", "Workshop Stripe None", "stripe-none.png", 359, 400, 34, 26),
        paint_control("workshop-stripe-white", "Workshop Stripe White", "stripe-white.png", 397, 400, 34, 26),
        paint_control("workshop-stripe-green", "Workshop Stripe Green", "stripe-green.png", 359, 430, 34, 26),
        paint_control("workshop-stripe-black", "Workshop Stripe Black", "stripe-black.png", 397, 430, 34, 26),
        paint_control("workshop-stripe-pink", "Workshop Stripe Pink", "stripe-pink.png", 435, 430, 34, 26),
    ])
    scene["entities"].append({
        "id": "workshop-state", "name": "Workshop State", "transform_3d": transform((0, 0, 0), (1, 1, 1)),
        "components": {"sindri.script": {"source": "scripts/workshop_state.decay", "script": "WorkshopState", "properties": {}, "enabled": True}},
    })
    scene["entities"].append({
        "id": "workshop-category-controller", "name": "Workshop Category Controller", "transform_3d": transform((0, 0, 0), (1, 1, 1)),
        "components": {"sindri.script": {"source": "scripts/workshop_category_controller.decay", "script": "WorkshopCategoryController", "properties": {}, "enabled": True}},
    })
    scene["entities"].append({
        "id": "workshop-paint-controller", "name": "Workshop Paint Controller", "transform_3d": transform((0, 0, 0), (1, 1, 1)),
        "components": {"sindri.script": {"source": "scripts/workshop_paint_controller.decay", "script": "WorkshopPaintController", "properties": {}, "enabled": True}},
    })
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
