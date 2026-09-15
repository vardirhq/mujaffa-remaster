#!/usr/bin/env python3
import json
import sys
from pathlib import Path

project = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
scene = json.loads((project / "main.scene.json").read_text(encoding="utf-8"))
by_name = {entity.get("name"): entity for entity in scene["entities"]}
for name in (
    "Workshop Paint Change", "Workshop Stripe None", "Workshop Stripe White",
    "Workshop Stripe Green", "Workshop Stripe Black", "Workshop Stripe Pink",
):
    entity = by_name[name]
    assert "sindri.ui.image" in entity["components"]
    assert "sindri.ui.button" in entity["components"]
controller = by_name["Workshop Paint Controller"]
assert controller["components"]["sindri.script"]["source"] == "scripts/workshop_paint_controller.decay"
print("paint category controls and controller installed")
