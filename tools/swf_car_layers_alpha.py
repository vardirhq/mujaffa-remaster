#!/usr/bin/env python3
"""Run the composable car-layer builder with full CXFORMWITHALPHA support."""
from __future__ import annotations
from pathlib import Path

source_path = Path(__file__).with_name("swf_car_layers.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    "from swf_car_extract import IDENT, Movie, mul, transform_bounds",
    "from swf_car_display import IDENT, Movie, mul, transform_bounds, svg_filter_values",
)
# The base layer builder already owns SVG assembly. Inject a per-leaf Flash
# colour transform using feComponentTransfer. This preserves RGB multiply/add
# as well as alpha instead of reducing CXFORMWITHALPHA to group opacity.
needle = '            element = image_for(leaf["shape"], leaf["matrix"])\n'
replacement = needle + '''            values = svg_filter_values(leaf.get("cxform"))
            if any(abs(s - 1.0) > 1e-7 or abs(i) > 1e-7 for s, i in values):
                fid = f"cx{len(defs)+1}_{inline_serial}"
                channels = ("R", "G", "B", "A")
                funcs = "".join(
                    f'<feFunc{channel} type="linear" slope="{slope:.8g}" intercept="{intercept:.8g}"/>'
                    for channel, (slope, intercept) in zip(channels, values)
                )
                defs.append(f'<filter id="{fid}" color-interpolation-filters="sRGB"><feComponentTransfer>{funcs}</feComponentTransfer></filter>')
                element = f'<g filter="url(#{fid})">{element}</g>'
'''
if needle not in source:
    raise SystemExit("swf_car_layers.py render hook changed; update colour-transform adapter")
source = source.replace(needle, replacement, 1)
code = compile(source, str(source_path), "exec")
exec(code, {"__name__": "__main__", "__file__": str(source_path)})
