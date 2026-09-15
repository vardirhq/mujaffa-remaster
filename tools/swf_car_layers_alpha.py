#!/usr/bin/env python3
"""Run the composable car-layer builder with CXFORMWITHALPHA support.

Kept as a thin adapter so the established layer builder remains readable while
we validate full Flash colour-transform parity.
"""
from __future__ import annotations
import runpy
from pathlib import Path

source_path = Path(__file__).with_name("swf_car_layers.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    "from swf_car_extract import IDENT, Movie, mul, transform_bounds",
    "from swf_car_display import IDENT, Movie, mul, transform_bounds",
)
needle = '            element = image_for(leaf["shape"], leaf["matrix"])\n'
replacement = needle + '            alpha = float(leaf.get("alpha", 1.0))\n            if alpha < 0.99999:\n                element = f\'<g opacity="{alpha:.6f}">{element}</g>\'\n'
if needle not in source:
    raise SystemExit("swf_car_layers.py render hook changed; update alpha adapter")
source = source.replace(needle, replacement, 1)
code = compile(source, str(source_path), "exec")
exec(code, {"__name__": "__main__", "__file__": str(source_path)})
