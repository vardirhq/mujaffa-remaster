#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import math
import re
from pathlib import Path

from swf_car_extract import IDENT, Movie, mul, transform_bounds

BODY_PARTS = {
    "indtraek": ("indtræk", 93, ["polyester", "tiger", "læder", "skind"]),
    "forrude": ("lir", 102, ["empty", "nosser", "wunderbaum", "hjerte", "koran"]),
    "cam": ("cam", 771, ["uden", "med"]),
    "vinduer": ("vindue", 107, ["standard", "gradient", "tonede", "spejlrefleks"]),
    "udstodning": ("udstødning", 131, ["1", "2", "3", "4"]),
    "paint": ("lakering", 97, ["tintable"]),
    "farvestribe": ("fartstriber", 66, ["empty", "pink", "sort", "grøn", "hvid"]),
    "soltag": ("soltag", 112, ["off", "on"]),
    "nummerplade": ("plade", 109, ["dynamic-text"]),
    "spoiler": ("spoiler", 87, ["1", "2", "3", "4", "5"]),
}

TYRES = ["1", "2", "3", "4"]
RIMS = ["standard", "racer", "krom", "guld"]


def sanitize(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", value.lower()).strip("-")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build composable Mujaffa car layers from the preserved SWF")
    ap.add_argument("swf", type=Path)
    ap.add_argument("reference_art", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument("--scale", type=float, default=4.0)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "svg").mkdir(exist_ok=True)
    (args.out / "png").mkdir(exist_ok=True)

    movie = Movie(args.swf)
    art = json.loads((args.reference_art / "manifest.json").read_text(encoding="utf-8"))
    items = {item["character_id"]: item for item in art["items"]}

    root = 875
    root_display = movie.display(root, 1)
    root_named = {item.get("name"): item for item in root_display if item.get("name")}
    body_instance = root_named["karosseri"]
    tyre_instance = root_named["dæk"]
    body_id = body_instance["character"]
    tyre_id = tyre_instance["character"]
    body_matrix = body_instance.get("matrix", IDENT)
    tyre_matrix = tyre_instance.get("matrix", IDENT)

    body_display = movie.display(body_id, 1)
    body_by_depth = {item["depth"]: item for item in body_display}
    body_masks = [item for item in body_display if "clip_depth" in item and item.get("character") is not None]
    name_to_category = {instance_name: category for category, (instance_name, _, _) in BODY_PARTS.items()}

    def body_item_leaves(depth: int, overrides=None) -> list[dict]:
        item = body_by_depth[depth]
        child = item.get("character")
        if child is None or "clip_depth" in item:
            return []
        child_matrix = mul(body_matrix, item.get("matrix", IDENT))
        active_masks = []
        for mask_item in body_masks:
            if mask_item["depth"] < depth <= mask_item["clip_depth"]:
                active_masks.append((mask_item["character"], mul(body_matrix, mask_item.get("matrix", IDENT))))
        return movie.leaves(
            child,
            1,
            matrix=child_matrix,
            overrides=overrides or {},
            masks=tuple(active_masks),
        )

    slots: list[dict[str, object]] = []
    all_persistent: list[dict] = []
    body_layers: dict[str, list[dict]] = {}
    body_meta: dict[str, object] = {}

    for item in body_display:
        if "clip_depth" in item:
            continue
        depth = item["depth"]
        instance_name = item.get("name")
        category = name_to_category.get(instance_name)
        if category is None:
            key = f"static:{depth}"
            leaves = body_item_leaves(depth)
            body_layers[key] = leaves
            all_persistent.extend(leaves)
            slots.append({"depth": depth, "kind": "static", "key": key})
            continue

        _, sprite_id, labels = BODY_PARTS[category]
        frame_count = movie.sprites.get(sprite_id, (1, b""))[0]
        variants = []
        for frame in range(1, frame_count + 1):
            label = labels[frame - 1] if frame - 1 < len(labels) else str(frame)
            leaves = body_item_leaves(depth, {sprite_id: frame})
            key = f"{category}:{label}"
            body_layers[key] = leaves
            all_persistent.extend(leaves)
            variants.append({"label": label, "frame": frame, "key": key})
        body_meta[category] = {
            "sprite": sprite_id,
            "instance": instance_name,
            "depth": depth,
            "variants": variants,
        }
        slots.append({"depth": depth, "kind": "variant", "category": category})

    tyre_layers: dict[str, list[dict]] = {}
    rim_layers: dict[str, list[dict]] = {}
    for tyre_frame, tyre_label in enumerate(TYRES, 1):
        leaves = movie.leaves(
            tyre_id,
            tyre_frame,
            matrix=tyre_matrix,
            skip_names=frozenset({"fælge"}),
        )
        tyre_layers[f"daek:{tyre_label}"] = leaves
        all_persistent.extend(leaves)
        for rim_frame, rim_label in enumerate(RIMS, 1):
            leaves = movie.leaves(
                tyre_id,
                tyre_frame,
                matrix=tyre_matrix,
                overrides={74: rim_frame},
                only_name="fælge",
            )
            key = f"hjulkapsel:{tyre_label}:{rim_label}"
            rim_layers[key] = leaves
            all_persistent.extend(leaves)

    bounds = []
    for leaf in all_persistent:
        info = items.get(leaf["shape"])
        if info:
            bounds.append(transform_bounds(info["bounds"], leaf["matrix"]))
    if not bounds:
        raise SystemExit("no persistent car geometry found")
    x0 = min(b[0] for b in bounds) - 4.0
    x1 = max(b[1] for b in bounds) + 4.0
    y0 = min(b[2] for b in bounds) - 4.0
    y1 = max(b[3] for b in bounds) + 4.0
    canvas = (x0, x1, y0, y1)
    width = x1 - x0
    height = y1 - y0

    def image_for(shape_id: int, matrix) -> str:
        info = items.get(shape_id)
        if not info:
            return ""
        svg = (args.reference_art / info["svg"]).read_text(encoding="utf-8")
        encoded = base64.b64encode(svg.encode()).decode()
        bx0, bx1, by0, by1 = info["bounds"]
        matrix_text = " ".join(f"{v:.8g}" for v in matrix)
        return (
            f'<image href="data:image/svg+xml;base64,{encoded}" x="{bx0}" y="{by0}" '
            f'width="{bx1-bx0}" height="{by1-by0}" transform="matrix({matrix_text})"/>'
        )

    def render_svg(leaves: list[dict]) -> tuple[str, list[int]]:
        body: list[str] = []
        defs: list[str] = []
        unresolved: list[int] = []
        mask_ids: dict[tuple, str] = {}

        def ensure_mask(desc) -> str:
            key = (desc[0], tuple(round(v, 7) for v in desc[1]))
            if key in mask_ids:
                return mask_ids[key]
            mask_id = f"m{len(mask_ids)+1}"
            mask_ids[key] = mask_id
            mask_leaves = movie.leaves(desc[0], 1, matrix=desc[1], overrides={})
            inner = "".join(image_for(ml["shape"], ml["matrix"]) for ml in mask_leaves if ml["shape"] in items)
            defs.append(
                f'<mask id="{mask_id}" maskUnits="userSpaceOnUse" x="{x0}" y="{y0}" '
                f'width="{width}" height="{height}" style="mask-type:alpha">{inner}</mask>'
            )
            return mask_id

        for leaf in leaves:
            if leaf["shape"] not in items:
                unresolved.append(leaf["shape"])
                continue
            element = image_for(leaf["shape"], leaf["matrix"])
            for desc in leaf.get("masks", ()):
                element = f'<g mask="url(#{ensure_mask(desc)})">{element}</g>'
            body.append(element)
        svg = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {width} {height}">'
            f'<defs>{"".join(defs)}</defs>{"".join(body)}</svg>'
        )
        return svg, sorted(set(unresolved))

    def write(name: str, leaves: list[dict]) -> dict[str, object]:
        svg, unresolved = render_svg(leaves)
        svg_path = args.out / "svg" / f"{name}.svg"
        png_path = args.out / "png" / f"{name}.png"
        svg_path.write_text(svg, encoding="utf-8")
        try:
            import cairosvg
            cairosvg.svg2png(
                bytestring=svg.encode(),
                write_to=str(png_path),
                output_width=max(1, math.ceil(width * args.scale)),
                output_height=max(1, math.ceil(height * args.scale)),
            )
            png = str(png_path.relative_to(args.out))
        except ImportError:
            png = None
        return {
            "svg": str(svg_path.relative_to(args.out)),
            "png": png,
            "shapes": len(leaves),
            "unresolved": unresolved,
        }

    outputs: dict[str, object] = {}
    for key, leaves in body_layers.items():
        outputs[key] = write(sanitize(key), leaves)
    for key, leaves in tyre_layers.items():
        outputs[key] = write(sanitize(key), leaves)
    for key, leaves in rim_layers.items():
        outputs[key] = write(sanitize(key), leaves)

    defaults = {
        "indtraek": "polyester",
        "forrude": "empty",
        "cam": "uden",
        "vinduer": "standard",
        "udstodning": "1",
        "paint": "tintable",
        "farvestribe": "empty",
        "soltag": "off",
        "nummerplade": "dynamic-text",
        "spoiler": "1",
        "daek": "1",
        "hjulkapsel": "standard",
    }

    preview: list[dict] = []
    for slot in slots:
        if slot["kind"] == "static":
            preview.extend(body_layers[slot["key"]])
        else:
            category = slot["category"]
            preview.extend(body_layers[f"{category}:{defaults[category]}"])
    preview.extend(tyre_layers[f"daek:{defaults['daek']}"])
    preview.extend(rim_layers[f"hjulkapsel:{defaults['daek']}:{defaults['hjulkapsel']}"])
    outputs["preview:stock"] = write("preview-stock", preview)

    speaker_display = movie.display(root_named["speakers"]["character"], 1)
    speaker_instances = {
        item.get("name"): {
            "sprite": item.get("character"),
            "matrix": item.get("matrix", IDENT),
            "depth": item["depth"],
        }
        for item in speaker_display
        if item.get("name")
    }

    manifest = {
        "source": args.swf.name,
        "root_sprite": root,
        "body_sprite": body_id,
        "tyre_sprite": tyre_id,
        "canvas_bounds": canvas,
        "scale": args.scale,
        "defaults": defaults,
        "body_stack": slots,
        "body_categories": body_meta,
        "tyres": {"sprite": tyre_id, "variants": TYRES},
        "rims": {
            "sprite": 74,
            "variants": RIMS,
            "note": "rim placement changes with the selected tyre frame, so exports are keyed by both tyre and rim",
        },
        "speakers": {
            "sprite": root_named["speakers"]["character"],
            "instances": speaker_instances,
            "persistent_layer_status": "deferred",
            "note": "speaker child timelines are purchase/drop animations that jump back to frame 1; they are not treated as persistent car layers yet",
        },
        "paint": {
            "runtime": "tintable",
            "note": "the original applies a Flash Color transform to the paint sprite; the extracted layer preserves geometry but runtime tint parity is still required",
        },
        "number_plate": {
            "runtime": "dynamic-text",
            "note": "plate characters remain runtime text rather than baked artwork",
        },
        "outputs": outputs,
    }
    (args.out / "layers-manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"composable car: {len(outputs)} outputs on {width:.1f}x{height:.1f} shared canvas")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
