#!/usr/bin/env python3
"""Build the workshop car with the original display state and CXFORM support.

CairoSVG does not implement SVG feComponentTransfer. Earlier parity passes
encoded Flash CXFORMWITHALPHA entirely through that filter, so the intermediate
SVG described the transform while the PNG rasterizer silently discarded it.
Alpha multiplication is therefore emitted as ordinary SVG group opacity, which
CairoSVG explicitly supports and which survives into the PNG Sindri renders.
"""
from __future__ import annotations
from pathlib import Path

source_path = Path(__file__).with_name("swf_car_layers.py")
source = source_path.read_text(encoding="utf-8")
source = source.replace(
    "from swf_car_extract import IDENT, Movie, mul, transform_bounds",
    "from swf_car_display import IDENT, IDENT_CX, Movie, combine_cxform, mul, transform_bounds, svg_filter_values",
)
source = source.replace("BODY_FRAME = 5", "BODY_FRAME = 1")
source = source.replace(
    "import argparse\\n",
    "import argparse\\nimport base64\\nimport io\\nfrom PIL import Image\\n",
    1,
)

# Apply Flash CXFORM to isolated rasterized leaves, not unsupported SVG filters.
# The leaf is rasterized against transparency before recoloring so additive
# channels never paint outside the original geometry.
raster_helper = '''
    def raster_cxform(element: str, values) -> str:
        import cairosvg
        from PIL import Image
        import io
        import base64

        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="{x0} {y0} {width} {height}">{element}</svg>'
        )
        raw = cairosvg.svg2png(
            bytestring=svg.encode(),
            output_width=max(1, math.ceil(width * args.scale)),
            output_height=max(1, math.ceil(height * args.scale)),
        )
        image = Image.open(io.BytesIO(raw)).convert("RGBA")
        # Apply per-channel LUTs in native Pillow code. Python loops over
        # millions of pixels per leaf would make the already-long CI worse.
        alpha = image.getchannel("A")
        channels = image.split()
        adjusted = []
        for index, channel in enumerate(channels):
            slope, intercept = values[index]
            lut = [
                max(0, min(255, round(value * slope + intercept * 255)))
                for value in range(256)
            ]
            adjusted.append(channel.point(lut))
        # Never create color/alpha outside the original leaf silhouette.
        adjusted[3] = Image.frombytes(
            "L", image.size,
            bytes(min(a, b) for a, b in zip(adjusted[3].tobytes(), alpha.tobytes()))
        ) if values[3][1] > 0 else adjusted[3]
        image = Image.merge("RGBA", tuple(adjusted))
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
        return (
            f'<image x="{x0}" y="{y0}" width="{width}" height="{height}" '
            f'href="data:image/png;base64,{encoded}"/>'
        )

'''
source = source.replace(
    "    def render_svg(leaves: list[dict]) -> tuple[str, list[int]]:",
    raster_helper + "    def render_svg(leaves: list[dict]) -> tuple[str, list[int]]:",
    1,
)


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

needle = '            element = image_for(leaf["shape"], leaf["matrix"])\n'
replacement = needle + '''            values = svg_filter_values(leaf.get("cxform"))
            rgb_values = values[:3]
            alpha_slope, alpha_intercept = values[3]

            # CairoSVG ignores feComponentTransfer. Bake non-identity Flash
            # RGB/alpha transforms into a transparent leaf raster instead.
            # Pure multiplicative alpha remains SVG opacity for performance.
            needs_rgb = any(abs(s - 1.0) > 1e-7 or abs(i) > 1e-7 for s, i in rgb_values)
            needs_alpha_add = abs(alpha_intercept) > 1e-9
            if needs_rgb or needs_alpha_add:
                element = raster_cxform(element, values)
            elif abs(alpha_slope - 1.0) > 1e-7:
                opacity = max(0.0, min(1.0, alpha_slope))
                element = f'<g opacity="{opacity:.8g}">{element}</g>'
'''
if needle not in source:
    raise SystemExit("swf_car_layers.py render hook changed")
source = source.replace(needle, replacement, 1)

code = compile(source, str(source_path), "exec")
exec(code, {"__name__": "__main__", "__file__": str(source_path)})
