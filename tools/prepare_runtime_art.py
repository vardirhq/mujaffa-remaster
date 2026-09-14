#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate runtime-safe Mujaffa car textures from the preserved SWF")
    ap.add_argument("--project", type=Path, default=Path("."))
    ap.add_argument("--scale", type=float, default=4.0)
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

        run(
            str(tools / "swf_art_extract.py"),
            str(swf),
            str(raw_art),
            "--scale",
            str(args.scale),
            "--max-size",
            "2048",
        )
        run(
            str(tools / "swf_car_layers.py"),
            str(swf),
            str(raw_art),
            str(layers),
            "--scale",
            str(args.scale),
        )

        if output.exists():
            shutil.rmtree(output)
        output.mkdir(parents=True, exist_ok=True)

        for png in (layers / "png").glob("*.png"):
            if png.name == "preview-stock.png":
                continue
            shutil.copy2(png, output / png.name)
        shutil.copy2(layers / "layers-manifest.json", output / "layers-manifest.json")

    png_count = len(list(output.glob("*.png")))
    if png_count < 50:
        raise SystemExit(f"runtime car generation produced only {png_count} PNGs")

    print(f"prepared {png_count} runtime car textures in {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
