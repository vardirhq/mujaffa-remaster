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


def neutralize_paint_texture(path: Path) -> None:
    """Make the paint layer neutral so runtime RGB tint controls every channel.

    The SWF extraction bakes the original blue paint into this layer. Multiplying
    that blue raster by a runtime tint suppresses red and green. Preserve the
    extracted alpha and light/shade information, but remove its baked hue.
    """
    from PIL import Image, ImageOps

    image = Image.open(path).convert("RGBA")
    alpha = image.getchannel("A")
    neutral = ImageOps.grayscale(image.convert("RGB"))
    image = Image.merge("RGBA", (neutral, neutral, neutral, alpha))
    image.save(path)


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


def install_showroom_art(showroom: Path, project: Path) -> int:
    output = project / "assets" / "generated" / "showroom"
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)
    copied = 0
    for png in (showroom / "png").glob("*.png"):
        shutil.copy2(png, output / png.name)
        copied += 1
    shutil.copy2(showroom / "showroom-manifest.json", output / "showroom-manifest.json")
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
    registered = project / "assets" / "generated" / "car-stage"
    if not swf.is_file():
        raise SystemExit(f"missing reference SWF: {swf}")

    with tempfile.TemporaryDirectory(prefix="mujaffa-runtime-art-") as temp_dir:
        temp = Path(temp_dir)
        raw_art = temp / "reference-art"
        layers = temp / "car-layers"
        showroom = temp / "showroom"
        run(str(tools / "swf_art_extract_fixed.py"), str(swf), str(raw_art), "--scale", str(args.scale), "--max-size", "2048")
        run(str(tools / "swf_car_layers_alpha.py"), str(swf), str(raw_art), str(layers), "--scale", str(args.scale))
        run(str(tools / "swf_showroom_extract.py"), str(swf), str(raw_art), str(showroom), "--scale", str(args.scale))
        showroom_count = install_showroom_art(showroom, project)
        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True, exist_ok=True)
        for png in (layers / "png").glob("*.png"):
            shutil.copy2(png, output / png.name)
        manifest = json.loads((layers / "layers-manifest.json").read_text(encoding="utf-8"))
        paint_png = manifest["outputs"]["paint:tintable"].get("png")
        if not paint_png:
            raise SystemExit("paint:tintable has no generated PNG")
        neutralize_paint_texture(output / Path(paint_png).name)
        shutil.copy2(layers / "layers-manifest.json", output / "layers-manifest.json")

    if registered.exists():
        shutil.rmtree(registered)
    run(str(tools / "register_showroom_car.py"), str(output), str(registered), "--scale", str(args.scale))
    run(str(tools / "build_showroom_reference.py"), "--project", str(project), "--scale", str(args.scale))

    png_count = len(list(output.glob("*.png")))
    if png_count < 50:
        raise SystemExit(f"runtime car generation produced only {png_count} PNGs")
    registered_count = len(list(registered.glob("*.png")))
    if registered_count < 50:
        raise SystemExit(f"showroom car registration produced only {registered_count} PNGs")

    installed = 0
    if args.install_scene:
        installed = install_car_scene(project, manifest)
        if installed < 10:
            raise SystemExit(f"runtime car scene installed only {installed} layers")
    message = f"prepared {png_count} runtime car textures, {registered_count} stage-registered showroom car textures and {showroom_count} positioned original showroom layers"
    if args.install_scene:
        message += f"; installed {installed} composable car layers"
    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
