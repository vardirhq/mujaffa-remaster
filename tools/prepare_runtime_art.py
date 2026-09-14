#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def safe_id(value: str) -> str:
    return "".join(ch if ch.isalnum() else "-" for ch in value.lower()).strip("-")


def install_car_scene(project: Path, manifest: dict) -> int:
    scene_path = project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    entities = [e for e in scene["entities"] if not str(e.get("id", "")).startswith("car-layer-")]
    car = next((e for e in entities if e.get("id") == "parity-car"), None)
    if car is None:
        raise SystemExit("main.scene.json has no parity-car root")
    car["disabled"] = True
    car["transform_3d"]["scale"] = [1.0, 1.0, 1.0]
    car["components"] = {"sindri.tags": {"tags": ["car", "mujaffa-car"]}}
    defaults = manifest["defaults"]
    outputs = manifest["outputs"]
    layer_entities = []
    layer = 30

    def add_piece(key: str, label: str, render_layer: int) -> None:
        output = outputs[key]
        png = output.get("png")
        if not png:
            raise SystemExit(f"car layer {key!r} has no PNG")
        filename = Path(png).name
        layer_entities.append({
            "id": f"car-layer-{safe_id(label)}",
            "name": f"Car {label}",
            "parent": "parity-car",
            "transform_3d": {"position": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0], "scale": [3.791, 3.088, 1.0]},
            "components": {
                "sindri.sprite": {"texture": f"assets/generated/car/{filename}", "tint": [1.0, 1.0, 1.0, 1.0], "layer": render_layer},
                "sindri.tags": {"tags": ["car-layer", safe_id(label)]},
            },
        })

    for slot in manifest["body_stack"]:
        if slot["kind"] == "static":
            key = slot["key"]
            label = key.replace(":", "-")
        else:
            category = slot["category"]
            key = f"{category}:{defaults[category]}"
            label = category
        add_piece(key, label, layer)
        layer += 1
    tyre = defaults["daek"]
    rim = defaults["hjulkapsel"]
    add_piece(f"daek:{tyre}", "tyres", 80)
    add_piece(f"hjulkapsel:{tyre}:{rim}", "rims", 81)
    scene["entities"] = entities + layer_entities
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    script_path = project / "scripts" / "game_state.decay"
    script = script_path.read_text(encoding="utf-8")
    old = "World.set_active(this.car, this.phase > 0.0);"
    if old not in script:
        raise SystemExit("GameState car visibility hook changed; update runtime art installer")
    script_path.write_text(script.replace(old, "World.set_active(this.car, true);"), encoding="utf-8")
    return len(layer_entities)


def install_showroom_art(raw_art: Path, project: Path) -> int:
    """Copy canonical original showroom artwork out of the SWF extraction.

    Character 934 is the full garage/showroom room visible at the original
    `showroom` label (main timeline frame 730).  Keep a few adjacent source
    pieces as reference/runtime-ready assets so later parity work can replace
    the remaining invented UI without another extraction pass.
    """
    manifest = json.loads((raw_art / "manifest.json").read_text(encoding="utf-8"))
    by_id = {item["character_id"]: item for item in manifest["items"]}
    output = project / "assets" / "generated" / "showroom"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    wanted = {
        934: "original-showroom-background.png",
        278: "original-blue-panel.png",
        291: "original-info-frame.png",
        891: "original-buy-background.png",
    }
    copied = 0
    mapping = {}
    for character_id, filename in wanted.items():
        item = by_id.get(character_id)
        if item is None or not item.get("png"):
            raise SystemExit(f"reference extraction is missing showroom character {character_id}")
        shutil.copy2(raw_art / item["png"], output / filename)
        mapping[str(character_id)] = {"file": filename, "bounds": item["bounds"]}
        copied += 1
    (output / "manifest.json").write_text(json.dumps({
        "source": "mujaffa_3juni_2003.swf",
        "showroom_frame": 730,
        "showroom_background_character": 934,
        "assets": mapping,
    }, indent=2) + "\n", encoding="utf-8")
    return copied


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate runtime-safe Mujaffa art from the preserved SWF")
    ap.add_argument("--project", type=Path, default=Path("."))
    ap.add_argument("--scale", type=float, default=4.0)
    ap.add_argument("--install-scene", action="store_true", help="replace the debug car in main.scene.json with generated layered sprites")
    args = ap.parse_args()
    project = args.project.resolve()
    swf = project / "mujaffa_3juni_2003.swf"
    tools = project / "tools"
    output = project / "assets" / "generated" / "car"
    if not swf.is_file():
        raise SystemExit(f"missing reference SWF: {swf}")

    with tempfile.TemporaryDirectory(prefix="mujaffa-runtime-art-") as temp_dir:
        temp = Path(temp_dir)
        raw_art = temp / "reference-art"
        layers = temp / "car-layers"
        run(str(tools / "swf_art_extract.py"), str(swf), str(raw_art), "--scale", str(args.scale), "--max-size", "2048")
        run(str(tools / "swf_car_layers.py"), str(swf), str(raw_art), str(layers), "--scale", str(args.scale))
        showroom_count = install_showroom_art(raw_art, project)
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True, exist_ok=True)
        for png in (layers / "png").glob("*.png"):
            shutil.copy2(png, output / png.name)
        manifest = json.loads((layers / "layers-manifest.json").read_text(encoding="utf-8"))
        shutil.copy2(layers / "layers-manifest.json", output / "layers-manifest.json")

    png_count = len(list(output.glob("*.png")))
    if png_count < 50:
        raise SystemExit(f"runtime car generation produced only {png_count} PNGs")
    installed = 0
    if args.install_scene:
        installed = install_car_scene(project, manifest)
        if installed < 10:
            raise SystemExit(f"runtime car scene installed only {installed} layers")
    message = f"prepared {png_count} runtime car textures and {showroom_count} original showroom assets"
    if args.install_scene:
        message += f"; installed {installed} composable car layers"
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
