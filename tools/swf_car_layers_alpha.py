#!/usr/bin/env python3
"""Build the workshop car with the original display state and full CXFORM support."""
from __future__ import annotations
from pathlib import Path

source_path = Path(__file__).with_name("swf_car_layers.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    "from swf_car_extract import IDENT, Movie, mul, transform_bounds",
    "from swf_car_display import IDENT, IDENT_CX, Movie, combine_cxform, mul, transform_bounds, svg_filter_values",
)

# The workshop capture is the resting car, not the later `mujaffa` animation
# state. Frames 5+ add shapes 773/774, which are the driver/foreground animation
# pieces visible in our bad reconstruction. Frame 1 contains the clean parked car.
source = source.replace("BODY_FRAME = 5", "BODY_FRAME = 1")

# swf_car_layers manually enters the body and tyre instances, so Movie.leaves
# never sees those two PlaceObject2 records. Carry their colour transforms into
# the manually flattened children rather than silently dropping them.
source = source.replace(
    "masks=tuple(active_masks),\n        )",
    "masks=tuple(active_masks),\n            cxform=combine_cxform(body_instance.get(\"cxform\"), item.get(\"cxform\")),\n        )",
    1,
)
source = source.replace(
    '            skip_names=frozenset({"fælge"}),\n        )',
    '            skip_names=frozenset({"fælge"}),\n            cxform=tyre_instance.get("cxform", IDENT_CX),\n        )',
    1,
)
source = source.replace(
    '                only_name="fælge",\n            )',
    '                only_name="fælge",\n                cxform=tyre_instance.get("cxform", IDENT_CX),\n            )',
    1,
)

# Character 61 sits at depth 1 of the car root, below body and tyres. It is the
# original under-car shadow/glow. The old composable builder selected only the
# named body/tyre/speaker instances and therefore threw this root artwork away.
needle = '''    slots: list[dict[str, object]] = []
    all_persistent: list[dict] = []
    body_layers: dict[str, list[dict]] = {}
    body_meta: dict[str, object] = {}
'''
replacement = needle + '''
    root_base = next((item for item in root_display if item["depth"] == 1 and item.get("character") is not None), None)
    if root_base is None or root_base.get("character") != 61:
        raise SystemExit("Mujaffa car root shadow changed; expected character 61 at depth 1")
    root_base_leaves = movie.leaves(
        root_base["character"], 1,
        matrix=root_base.get("matrix", IDENT),
        cxform=root_base.get("cxform", IDENT_CX),
    )
    body_layers["root:shadow"] = root_base_leaves
    all_persistent.extend(root_base_leaves)
    slots.append({"depth": 0, "kind": "static", "key": "root:shadow"})
'''
if needle not in source:
    raise SystemExit("swf_car_layers.py body-stack hook changed")
source = source.replace(needle, replacement, 1)

# Apply every recovered RGBA transform at rasterization time.
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
    raise SystemExit("swf_car_layers.py render hook changed")
source = source.replace(needle, replacement, 1)

code = compile(source, str(source_path), "exec")
exec(code, {"__name__": "__main__", "__file__": str(source_path)})
