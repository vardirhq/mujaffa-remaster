#!/usr/bin/env python3
"""Install the original-derived classic title scene from recovered SWF evidence.

`swf_title_extract.py` composes the opening screens into layers and records
where each one sits on the original 500x500 stage. This tool turns that
manifest into `title.scene.json`: one world sprite per screen backdrop, three
per control so hover and press show the original's own artwork, and one
transparent UI button per control carrying the hit area the original button
responds to.

The scene is committed, so CI regenerates it and fails on any difference. That
is the check that keeps the runtime title honest: the scene in the repository is
the SWF's opening, not a redraw of it that has drifted.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

STAGE = 500.0
# The classic presentation is a fixed square stage, so the world camera's
# `fit: shorter` maps the original 500px stage onto 10 world units either way
# the window is shaped.
WORLD_UNITS = 10.0
# The screen overlay is 2 units tall, so 500 stage pixels span 2 UI units.
UI_UNITS = 2.0

STATES = ("up", "over", "down")
STATE_LAYERS = {"up": 60, "over": 62, "down": 64}
# The recovered performance draws over the backdrop it was lifted out of, and
# under the menu buttons.
ANIMATION_LAYER = 10

# What the recovered animations are, in names a script and a reader can use.
ANIMATION_NAMES = {
    "opening-1": "Title Mujaffa Arm",
    "opening-2": "Title Mujaffa Mouth",
    "prompt": "Title Prompt",
}

# How a recovered control is named in the scene, so scripts can find it by a
# name that reads like the control rather than like its character id.
CONTROL_NAMES = {
    "title-start-game": "Title Start",
    "title-instructions": "Title Instructions",
    "instructions-next-page": "Instructions Next",
    "instructions-previous-page": "Instructions Previous",
    "instructions-start-game": "Instructions Start",
}

SCREEN_NAMES = {
    "title": "Title Backdrop",
    "instructions-1": "Instructions Page 1",
    "instructions-2": "Instructions Page 2",
    "instructions-3": "Instructions Page 3",
    "instructions-4": "Instructions Page 4",
    "instructions-5": "Instructions Page 5",
}


def transform(position=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    return {"position": list(position), "rotation": [0.0, 0.0, 0.0, 1.0], "scale": list(scale)}


def stage_to(rect, units):
    """Centre and size for a stage rect, in a space `units` tall over the stage."""
    x, y, width, height = rect
    per_pixel = units / STAGE
    return (
        round((x + width / 2.0 - STAGE / 2.0) * per_pixel, 6),
        round((STAGE / 2.0 - (y + height / 2.0)) * per_pixel, 6),
        round(width * per_pixel, 6),
        round(height * per_pixel, 6),
    )


def camera():
    return {
        "id": "title-camera",
        "name": "Title Camera",
        "transform_3d": transform((0.0, 0.0, 5.0)),
        "components": {
            "sindri.camera": {
                "far": 100.0,
                "near": 0.1,
                "projection": "orthographic",
                "vertical_size": WORLD_UNITS,
                "fit": "shorter",
            }
        },
    }


def stage_sprite(entity_id, name, texture, rect, layer, disabled=False):
    x, y, width, height = stage_to(rect, WORLD_UNITS)
    entity = {
        "id": entity_id,
        "name": name,
        "transform_3d": transform((x, y, -4.0), (width, height, 1.0)),
        "components": {
            "sindri.sprite": {"texture": texture, "tint": [1.0, 1.0, 1.0, 1.0], "layer": layer},
            "sindri.tags": {"tags": ["classic-title", "fixed-500-stage"]},
        },
    }
    if disabled:
        entity["disabled"] = True
    return entity


def animation(entity_id, name, spec):
    """One recovered clip, played on a sprite sheet cut from the original."""
    x, y, width, height = stage_to(spec["stage_rect"], WORLD_UNITS)
    texture = f"assets/generated/title/{spec['png']}"
    clip = spec["clip"]
    return {
        "id": entity_id,
        "name": name,
        "transform_3d": transform((x, y, -4.0), (width, height, 1.0)),
        "components": {
            "sindri.sprite": {
                "texture": f"{texture}#{clip['frames'][0]}",
                "tint": [1.0, 1.0, 1.0, 1.0],
                "layer": ANIMATION_LAYER,
            },
            "sindri.animation.sprite": {
                "clips": {
                    "play": {
                        "frames": clip["frames"],
                        "seconds_per_frame": clip["seconds_per_frame"],
                        "looping": clip["looping"],
                    }
                },
                "playing": "play",
                "speed": 1.0,
            },
            "sindri.tags": {"tags": ["classic-title", "fixed-500-stage", "title-animation"]},
        },
    }


def hit_button(entity_id, name, rect, label, disabled=False):
    x, y, width, height = stage_to(rect, UI_UNITS)
    entity = {
        "id": entity_id,
        "name": name,
        "transform_3d": transform((x, y, 0.0), (width, height, 1.0)),
        "components": {
            # A hit area, not a look: the original button's own artwork is the
            # world sprite behind it, so this shape stays all but invisible.
            "sindri.ui.shape": {
                "kind": "rect",
                "fill": [0.0, 0.0, 0.0, 0.001],
                "anchor": "center",
                "layer": 200,
            },
            "sindri.ui.button": {"label": label},
            "sindri.tags": {"tags": ["classic-title", "title-control"]},
        },
    }
    if disabled:
        entity["disabled"] = True
    return entity


def build(manifest: dict) -> dict:
    entities = [camera()]
    stage_rect = [0.0, 0.0, STAGE, STAGE]

    for key, screen in manifest["screens"].items():
        name = SCREEN_NAMES[key]
        entities.append(
            stage_sprite(
                f"title-screen-{key}",
                name,
                f"assets/generated/title/{screen['backdrop']['png']}",
                stage_rect,
                -10 if key == "title" else -9,
                disabled=key != "title",
            )
        )

    for spec in manifest["animations"]:
        entities.append(
            animation(
                f"title-animation-{spec['id']}",
                ANIMATION_NAMES.get(spec["id"], f"Title Animation {spec['id']}"),
                spec,
            )
        )

    for control in manifest["controls"]:
        name = CONTROL_NAMES[control["id"]]
        for state in STATES:
            entities.append(
                stage_sprite(
                    f"title-control-{control['id']}-{state}",
                    f"{name} {state.capitalize()}",
                    f"assets/generated/title/{control['states'][state]}",
                    control["art_rect"],
                    STATE_LAYERS[state],
                    disabled=state != "up" or control["screens"] != ["title"],
                )
            )
        entities.append(
            hit_button(
                f"title-control-{control['id']}",
                name,
                control["hit_rect"],
                name,
                disabled=control["screens"] != ["title"],
            )
        )

    entities.append(
        {
            "id": "title-controller",
            "name": "Title Controller",
            "transform_3d": transform(),
            "components": {
                "sindri.script": {
                    "source": "scripts/title.decay",
                    "script": "Title",
                    "properties": {},
                    "enabled": True,
                }
            },
        }
    )

    return {
        "format_version": 9,
        "metadata": {"name": "Mujaffa Classic Title"},
        "entities": entities,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path("."))
    parser.add_argument(
        "--manifest",
        type=Path,
        help="title manifest; defaults to the project's generated title art",
    )
    args = parser.parse_args()
    project = args.project.resolve()
    manifest_path = args.manifest or project / "assets" / "generated" / "title" / "title-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    scene = build(manifest)
    (project / "title.scene.json").write_text(
        json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(
        f"installed classic title scene: {len(manifest['screens'])} screens, "
        f"{len(manifest['controls'])} controls, {len(manifest['animations'])} animations, "
        f"{len(scene['entities'])} entities"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
