#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path

# Original main-timeline frame 722 (`køb` / workshop) placement for character
# 875 (`bil`). The previous value came from frame 730 (`showroom`), which is a
# different screen and made the workshop car too large and far left.
CAR_MATRIX = (0.93035888671875, 0.0, 0.0, 0.93035888671875, 329.65, 193.9)
WORKSHOP_FRAME = 722


def register_png(source: Path, target: Path, bounds: list[float], scale: float) -> None:
    xmin, xmax, ymin, ymax = bounds
    width = xmax - xmin
    height = ymax - ymin
    encoded = base64.b64encode(source.read_bytes()).decode("ascii")
    a, b, c, d, tx, ty = CAR_MATRIX
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">
      <g transform="matrix({a} {b} {c} {d} {tx} {ty})">
        <image x="{xmin}" y="{ymin}" width="{width}" height="{height}" href="data:image/png;base64,{encoded}"/>
      </g>
    </svg>'''
    import cairosvg
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(target),
        output_width=max(1, math.ceil(500 * scale)),
        output_height=max(1, math.ceil(500 * scale)),
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Register composable car PNGs to original 500x500 workshop stage")
    ap.add_argument("car_dir", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--scale", type=float, default=4.0)
    args = ap.parse_args()

    manifest = json.loads((args.car_dir / "layers-manifest.json").read_text(encoding="utf-8"))
    bounds = manifest["canvas_bounds"]
    args.out.mkdir(parents=True, exist_ok=True)

    count = 0
    for output in manifest["outputs"].values():
        png = output.get("png")
        if not png:
            continue
        source = args.car_dir / Path(png).name
        target = args.out / source.name
        register_png(source, target, bounds, args.scale)
        count += 1

    (args.out / "stage-registration.json").write_text(json.dumps({
        "main_timeline_frame": WORKSHOP_FRAME,
        "label": "køb",
        "character_id": 875,
        "matrix": list(CAR_MATRIX),
        "canvas": [500, 500],
        "source_canvas_bounds": bounds,
        "registered_outputs": count,
    }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"registered {count} car layers to original workshop stage")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
