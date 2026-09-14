#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
from pathlib import Path


def data_uri(path: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build registered frame-730 showroom core reference")
    ap.add_argument("--project", type=Path, default=Path("."))
    ap.add_argument("--scale", type=float, default=4.0)
    args = ap.parse_args()
    project = args.project.resolve()
    showroom = project / "assets" / "generated" / "showroom"
    car = project / "assets" / "generated" / "car-stage"
    layers = [
        showroom / "showroom-room.png",
        showroom / "showroom-mujaffa.png",
        showroom / "showroom-panel.png",
        car / "preview-stock.png",
    ]
    missing = [str(p) for p in layers if not p.is_file()]
    if missing:
        raise SystemExit("missing registered showroom layers: " + ", ".join(missing))

    # These are all 500x500 stage-registered textures. Stacking them without
    # offsets is the important invariant. This core reference intentionally
    # excludes buttons/text until their SWF definitions are reconstructed.
    images = "".join(
        f'<image x="0" y="0" width="500" height="500" href="{data_uri(path)}"/>'
        for path in layers
    )
    svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="500" height="500" viewBox="0 0 500 500">{images}</svg>'
    import cairosvg
    target = showroom / "showroom-parity-core.png"
    cairosvg.svg2png(
        bytestring=svg.encode("utf-8"),
        write_to=str(target),
        output_width=int(500 * args.scale),
        output_height=int(500 * args.scale),
    )
    print(f"wrote registered showroom parity core reference to {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
