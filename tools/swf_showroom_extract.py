#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

from swf_car_extract import Movie

# Canonical VERKSTED state: main timeline frame 722 (`køb`).
WORKSHOP = {
    "room": {"character": 867, "frame": 1, "matrix": (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)},
    "mujaffa": {"character": 869, "frame": 1, "matrix": (0.5999908447265625, 0.0, 0.0, 0.5999908447265625, 426.95, 175.7)},
    "panel": {"character": 383, "frame": 1, "matrix": (0.881744384765625, 0.0, 0.0, 0.881744384765625, 78.5, 288.0)},
    # Character 1 is the actual hand-drawn MUJAFFA SPILLET logo. The previous
    # workshop chrome approximated it with italic text, which was both ugly and
    # incorrectly overlapped with the workshop title.
    "logo": {"character": 1, "frame": 1, "matrix": (0.3799896240234375, 0.0, 0.0, 0.3799896240234375, 72.9, 47.85)},
}


def inline_shape(raw_art: Path, info: dict, matrix, serial: int) -> str:
    svg = (raw_art / info["svg"]).read_text(encoding="utf-8")
    match = re.search(r'viewBox="([^"]+)"', svg)
    if not match:
        raise ValueError(f"shape {info['character_id']} SVG is missing viewBox")
    vx, vy, vw, vh = [float(v) for v in match.group(1).split()]
    inner = svg[svg.find(">") + 1 : svg.rfind("</svg>")]
    prefix = f"s{info['character_id']}_{serial}_"
    for old_id in re.findall(r'id="([^"]+)"', inner):
        inner = inner.replace(f'id="{old_id}"', f'id="{prefix}{old_id}"')
        inner = inner.replace(f'url(#{old_id})', f'url(#{prefix}{old_id})')
        inner = inner.replace(f'href="#{old_id}"', f'href="#{prefix}{old_id}"')
        inner = inner.replace(f'xlink:href="#{old_id}"', f'xlink:href="#{prefix}{old_id}"')
    ms = " ".join(f"{v:.8g}" for v in matrix)
    return (
        f'<g transform="matrix({ms})"><svg x="{vx:.8g}" y="{vy:.8g}" '
        f'width="{vw:.8g}" height="{vh:.8g}" viewBox="{vx:.8g} {vy:.8g} {vw:.8g} {vh:.8g}" '
        f'overflow="visible">{inner}</svg></g>'
    )


def render_layer(movie: Movie, raw_art: Path, items: dict, spec: dict, name: str, out: Path, scale: float) -> dict:
    leaves = movie.leaves(
        spec["character"],
        spec["frame"],
        matrix=spec["matrix"],
        overrides={spec["character"]: spec["frame"]},
    )
    serial = 0
    body = []
    unresolved = []
    for leaf in leaves:
        info = items.get(leaf["shape"])
        if info is None:
            unresolved.append(leaf["shape"])
            continue
        serial += 1
        body.append(inline_shape(raw_art, info, leaf["matrix"], serial))
    svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">' + "".join(body) + "</svg>"
    svg_dir = out / "svg"
    png_dir = out / "png"
    svg_dir.mkdir(parents=True, exist_ok=True)
    png_dir.mkdir(parents=True, exist_ok=True)
    svg_path = svg_dir / f"{name}.svg"
    png_path = png_dir / f"{name}.png"
    svg_path.write_text(svg, encoding="utf-8")
    import cairosvg
    cairosvg.svg2png(
        bytestring=svg.encode(),
        write_to=str(png_path),
        output_width=max(1, math.ceil(500 * scale)),
        output_height=max(1, math.ceil(500 * scale)),
    )
    return {
        "character_id": spec["character"],
        "frame": spec["frame"],
        "matrix": list(spec["matrix"]),
        "svg": str(svg_path.relative_to(out)),
        "png": str(png_path.relative_to(out)),
        "shape_count": len(leaves),
        "unresolved": sorted(set(unresolved)),
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("swf", type=Path)
    ap.add_argument("reference_art", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--scale", type=float, default=4.0)
    args = ap.parse_args()

    movie = Movie(args.swf)
    art = json.loads((args.reference_art / "manifest.json").read_text(encoding="utf-8"))
    items = {item["character_id"]: item for item in art["items"]}
    outputs = {}
    for name, spec in WORKSHOP.items():
        outputs[name] = render_layer(movie, args.reference_art, items, spec, f"showroom-{name}", args.out, args.scale)
        if outputs[name]["unresolved"]:
            raise SystemExit(f"workshop layer {name} has unresolved shapes: {outputs[name]['unresolved']}")

    (args.out / "showroom-manifest.json").write_text(
        json.dumps({
            "source": args.swf.name,
            "main_timeline_frame": 722,
            "label": "køb",
            "screen": "workshop",
            "canvas": [500, 500],
            "outputs": outputs,
            "note": "Every PNG is registered to the original frame-722 workshop state. Filenames retain the historical showroom prefix for runtime compatibility.",
        }, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"extracted {len(outputs)} positioned original workshop layers")


if __name__ == "__main__":
    main()
