#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

CATEGORIES = [
    ("paint", "PAINT"),
    ("daek", "TYRES"),
    ("hjulkapsel", "RIMS"),
    ("spoiler", "SPOILER"),
    ("udstodning", "EXHAUST"),
    ("vinduer", "WINDOWS"),
    ("soltag", "SUNROOF"),
    ("indtraek", "INTERIOR"),
    ("farvestribe", "STRIPES"),
    ("forrude", "WINDSCREEN"),
]


def safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def transform(position=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)) -> dict:
    return {
        "position": list(position),
        "rotation": [0.0, 0.0, 0.0, 1.0],
        "scale": list(scale),
    }


def ui_button(entity_id: str, name: str, parent: str, position, scale, fill, label: str, anchor="center") -> dict:
    return {
        "id": entity_id,
        "name": name,
        "parent": parent,
        "transform_3d": transform(position, scale),
        "components": {
            "sindri.ui.shape": {
                "kind": "rect",
                "fill": fill,
                "anchor": anchor,
                "layer": 102,
            },
            "sindri.ui.button": {"label": label},
        },
    }


def add_car_layers(scene: dict, manifest: dict) -> None:
    scene["entities"] = [
        entity for entity in scene["entities"]
        if not str(entity.get("id", "")).startswith("car-layer-")
    ]
    car = next(entity for entity in scene["entities"] if entity.get("id") == "parity-car")
    car["disabled"] = False
    car["transform_3d"] = transform((0.0, 0.15, 0.0), (1.0, 1.0, 1.0))
    car["components"] = {"sindri.tags": {"tags": ["car", "mujaffa-car"]}}

    outputs = manifest["outputs"]
    defaults = manifest["defaults"]
    generated: list[dict] = []

    def piece(key: str, label: str, layer: int, active: bool, tags: list[str]) -> None:
        output = outputs[key]
        png = output.get("png")
        if not png:
            raise SystemExit(f"car layer {key!r} has no PNG")
        generated.append({
            "id": f"car-layer-{safe_id(label)}",
            "name": f"Garage Car {label}",
            "parent": "parity-car",
            "disabled": not active,
            "transform_3d": transform((0.0, 0.0, 0.0), (3.791, 3.088, 1.0)),
            "components": {
                "sindri.sprite": {
                    "texture": f"assets/generated/car/{Path(png).name}",
                    "tint": [1.0, 1.0, 1.0, 1.0],
                    "layer": layer,
                },
                "sindri.tags": {"tags": ["garage-car-layer", *tags]},
            },
        })

    layer = 30
    for slot in manifest["body_stack"]:
        if slot["kind"] == "static":
            key = slot["key"]
            piece(key, key.replace(":", "-"), layer, True, ["static"])
            layer += 1
            continue
        category = slot["category"]
        variants = manifest["body_categories"][category]["variants"]
        for variant in variants:
            label = variant["label"]
            key = variant["key"]
            piece(key, f"{category}-{label}", layer, label == defaults[category], [category, safe_id(label)])
        layer += 1

    for tyre in manifest["tyres"]["variants"]:
        piece(f"daek:{tyre}", f"daek-{tyre}", 80, tyre == defaults["daek"], ["daek", safe_id(tyre)])
    for tyre in manifest["tyres"]["variants"]:
        for rim in manifest["rims"]["variants"]:
            piece(
                f"hjulkapsel:{tyre}:{rim}",
                f"hjulkapsel-{tyre}-{rim}",
                81,
                tyre == defaults["daek"] and rim == defaults["hjulkapsel"],
                ["hjulkapsel", safe_id(tyre), safe_id(rim)],
            )

    scene["entities"].extend(generated)


def add_garage_ui(scene: dict) -> None:
    scene["entities"] = [
        entity for entity in scene["entities"]
        if not str(entity.get("id", "")).startswith("garage-ui-")
        and entity.get("id") != "garage-controller"
    ]

    # The world background needs to cover every aspect ratio. The original SWF
    # was square; the remaster keeps the car presentation but lets the controls
    # use the actual screen around it.
    backdrop = next(entity for entity in scene["entities"] if entity.get("id") == "backdrop")
    backdrop["transform_3d"]["scale"] = [30.0, 30.0, 1.0]
    backdrop["components"]["sindri.shape"]["fill"] = [0.055, 0.05, 0.045, 1.0]

    # Route/debug presentation is not part of the garage. Keep it in the scene
    # for parity work, but hide it while this vertical slice becomes the default.
    for entity_id in ("route-1", "route-2", "route-3", "status-1", "status-2", "status-3", "status-4", "status-5"):
        entity = next((e for e in scene["entities"] if e.get("id") == entity_id), None)
        if entity:
            entity["disabled"] = True

    desktop_root = {
        "id": "garage-ui-desktop",
        "name": "Garage Desktop UI",
        "transform_3d": transform(),
        "components": {
            "sindri.ui.shape": {"kind": "rect", "fill": [0.0, 0.0, 0.0, 0.0], "anchor": "center", "layer": 100}
        },
    }
    mobile_root = {
        "id": "garage-ui-mobile",
        "name": "Garage Mobile UI",
        "disabled": True,
        "transform_3d": transform(),
        "components": {
            "sindri.ui.shape": {"kind": "rect", "fill": [0.0, 0.0, 0.0, 0.0], "anchor": "center", "layer": 100}
        },
    }
    scene["entities"].extend([desktop_root, mobile_root])

    palette = [
        [0.82, 0.22, 0.20, 0.96], [0.18, 0.52, 0.82, 0.96], [0.34, 0.34, 0.38, 0.96],
        [0.76, 0.43, 0.13, 0.96], [0.48, 0.48, 0.52, 0.96], [0.18, 0.62, 0.66, 0.96],
        [0.86, 0.67, 0.16, 0.96], [0.52, 0.28, 0.67, 0.96], [0.24, 0.68, 0.38, 0.96],
        [0.74, 0.30, 0.50, 0.96],
    ]

    # Desktop gets a real side rail with large targets. Mobile gets a compact
    # bottom category strip plus large prev/next controls above it. They are not
    # the same menu squeezed smaller; they are different compositions over the
    # same state.
    for index, ((category, label), color) in enumerate(zip(CATEGORIES, palette)):
        y = 0.73 - index * 0.16
        scene["entities"].append(ui_button(
            f"garage-ui-desktop-category-{category}",
            f"Desktop Category {label}",
            "garage-ui-desktop",
            (-0.72, y, 0.0), (0.22, 0.115, 1.0), color,
            label,
        ))
        x = -0.405 + index * 0.09
        scene["entities"].append(ui_button(
            f"garage-ui-mobile-category-{category}",
            f"Mobile Category {label}",
            "garage-ui-mobile",
            (x, -0.84, 0.0), (0.075, 0.12, 1.0), color,
            label,
        ))

    scene["entities"].extend([
        ui_button("garage-ui-desktop-prev", "Desktop Previous Part", "garage-ui-desktop", (0.60, -0.58, 0.0), (0.22, 0.13, 1.0), [0.12, 0.12, 0.14, 0.96], "Previous"),
        ui_button("garage-ui-desktop-next", "Desktop Next Part", "garage-ui-desktop", (0.82, -0.58, 0.0), (0.22, 0.13, 1.0), [0.18, 0.18, 0.21, 0.96], "Next"),
        ui_button("garage-ui-mobile-prev", "Mobile Previous Part", "garage-ui-mobile", (-0.23, -0.61, 0.0), (0.34, 0.16, 1.0), [0.12, 0.12, 0.14, 0.98], "Previous"),
        ui_button("garage-ui-mobile-next", "Mobile Next Part", "garage-ui-mobile", (0.23, -0.61, 0.0), (0.34, 0.16, 1.0), [0.18, 0.18, 0.21, 0.98], "Next"),
    ])

    scene["entities"].append({
        "id": "garage-controller",
        "name": "Garage Controller",
        "transform_3d": transform(),
        "components": {
            "sindri.script": {
                "source": "scripts/garage.decay",
                "script": "Garage",
                "properties": {},
                "enabled": True,
            }
        },
    })


def main() -> int:
    parser = argparse.ArgumentParser(description="Install the responsive Mujaffa garage scene")
    parser.add_argument("--project", type=Path, default=Path("."))
    args = parser.parse_args()
    project = args.project.resolve()
    scene_path = project / "main.scene.json"
    manifest_path = project / "assets/generated/car/layers-manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("generate runtime car art before installing the garage scene")
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    add_car_layers(scene, manifest)
    add_garage_ui(scene)
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("installed responsive garage scene with desktop and mobile controls")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
