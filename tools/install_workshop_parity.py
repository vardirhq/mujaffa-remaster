#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import cairosvg

CATEGORIES = [
    ("paint", "LAKKERING"),
    ("audio", "BILSTEREO"),
    ("spoiler", "SPOILER"),
    ("exhaust", "EKSOSANLEGG"),
    ("rims", "FELGER"),
    ("tyres", "DEKK"),
    ("windows", "RUTER"),
    ("sunroof", "SOLTAK"),
    ("plate", "NUMMERSKILT"),
    ("interior", "SETETREKK"),
    ("windscreen", "BILNIPS"),
    ("horn", "BÅT-HORN"),
    ("camera", "BMW CAM"),
]


def transform(position=(0.0, 0.0, 0.0), scale=(1.0, 1.0, 1.0)):
    return {"position": list(position), "rotation": [0.0, 0.0, 0.0, 1.0], "scale": list(scale)}


def world_image(entity_id: str, name: str, texture: str, layer: int):
    return {
        "id": entity_id,
        "name": name,
        "transform_3d": transform((0.0, 0.0, -4.0), (10.0, 10.0, 1.0)),
        "components": {
            "sindri.sprite": {"texture": texture, "tint": [1, 1, 1, 1], "layer": layer},
            "sindri.tags": {"tags": ["workshop-parity", "fixed-500-stage"]},
        },
    }


def ui_button(entity_id: str, name: str, position, scale, label: str, disabled=False):
    return {
        "id": entity_id,
        "name": name,
        "parent": "garage-ui-desktop",
        "disabled": disabled,
        "transform_3d": transform(position, scale),
        "components": {
            "sindri.ui.shape": {"kind": "rect", "fill": [0, 0, 0, 0.001], "anchor": "center", "layer": 200},
            "sindri.ui.button": {"label": label},
        },
    }


def make_chrome(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    buttons = []
    y = 137
    for _, label in CATEGORIES:
        marker = '<text x="12" y="{y}" font-size="13" fill="#10131c">▷</text>'.format(y=y+3) if label == "LAKKERING" else ""
        star = '<path d="M19 {y} l4 6 7-1-4 6 3 7-8-3-6 5 1-8-6-4 8-2z" fill="#ffd21a" stroke="#111" stroke-width="1"/><text x="14" y="{ty}" font-size="6" font-weight="700" fill="#111">NY</text>'.format(y=y-10,ty=y+3) if label in ("BÅT-HORN","BMW CAM") else ""
        buttons.append(f'''{marker}{star}<rect x="27" y="{y-10}" width="102" height="17" rx="3" fill="#2ca2c8" stroke="#121421" stroke-width="2"/><text x="78" y="{y+2}" text-anchor="middle" font-size="11" font-weight="700" fill="#15151b">{label}</text>''')
        y += 25

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1000" viewBox="0 0 500 500">
      <rect x="0" y="0" width="500" height="500" fill="none"/>
      <rect x="0" y="0" width="500" height="34" fill="#070936"/>
      <rect x="0" y="34" width="500" height="29" fill="#41608d"/>
      <text x="101" y="28" font-size="32" font-style="italic" font-weight="900" fill="#ef332f" stroke="#111" stroke-width="1.2">MUJAFFA</text>
      <text x="103" y="53" font-size="28" font-style="italic" font-weight="900" fill="#ef332f" stroke="#111" stroke-width="1.2">SPILLET</text>
      <text x="258" y="27" text-anchor="middle" font-size="25" font-weight="700" fill="#30517d">BHAIAS VERKSTED</text>
      <rect x="0" y="55" width="500" height="25" fill="#2d9dc0"/>
      <text x="151" y="72" font-size="11" font-weight="700" fill="#111">PENGER:</text><text x="204" y="72" font-size="14" font-weight="700" fill="#e8f3f0">5000</text>
      <text x="269" y="72" font-size="11" font-weight="700" fill="#111">BMW:</text><text x="309" y="72" font-size="14" font-weight="700" fill="#e8f3f0">1</text>
      <text x="372" y="72" font-size="11" font-weight="700" fill="#111">STREET CRED:</text><text x="469" y="72" font-size="14" font-weight="700" fill="#e8f3f0">0</text>

      <rect x="4" y="83" width="145" height="381" rx="12" fill="#139bc3" stroke="#0c1039" stroke-width="4"/>
      <text x="76" y="108" text-anchor="middle" font-size="20" font-weight="800" fill="#d6ffff">UTSTYR</text>
      {''.join(buttons)}

      <rect x="153" y="351" width="343" height="111" rx="12" fill="#129bc4" stroke="#0b103b" stroke-width="4"/>
      <text x="175" y="377" font-size="14" font-weight="700" fill="#10131c">Lakker BMW</text>
      <text x="176" y="397" font-size="9" font-weight="700" fill="#10131c">Trykk “skift”</text>
      <text x="176" y="409" font-size="9" font-weight="700" fill="#10131c">for å endre farge</text>
      <rect x="179" y="416" width="52" height="34" rx="3" fill="#2a9ac3" stroke="#6b3150" stroke-width="2"/><text x="205" y="440" text-anchor="middle" font-size="21" font-weight="700" fill="#ec3345">skift</text>
      <text x="345" y="378" font-size="14" font-weight="700" fill="#10131c">Fartstripe</text>
      <g transform="translate(344 389)">
        <rect x="0" y="0" width="30" height="22" rx="5" fill="#32a8c8" stroke="#111" stroke-width="2"/><path d="M5 11 l7 7 14-20" fill="none" stroke="#e33435" stroke-width="4"/>
        <rect x="38" y="0" width="30" height="22" rx="5" fill="#fff" stroke="#111" stroke-width="2"/><path d="M40 5 l26 16 M40 12 l22 13" stroke="#2486bf" stroke-width="4"/>
        <rect x="0" y="30" width="30" height="22" rx="5" fill="#5fd52e" stroke="#111" stroke-width="2"/><path d="M2 34 l27 16 M2 41 l21 12" stroke="#258cc1" stroke-width="4"/>
        <rect x="38" y="30" width="30" height="22" rx="5" fill="#111" stroke="#111" stroke-width="2"/><path d="M40 34 l26 16" stroke="#217ead" stroke-width="4"/>
        <rect x="76" y="30" width="30" height="22" rx="5" fill="#f66ca9" stroke="#111" stroke-width="2"/><path d="M78 34 l26 16" stroke="#267eac" stroke-width="4"/>
      </g>

      <rect x="0" y="468" width="500" height="32" fill="#070936"/>
      <rect x="205" y="474" width="105" height="20" rx="6" fill="#51ebef" stroke="#16395f" stroke-width="2"/><text x="257" y="489" text-anchor="middle" font-size="14" font-weight="700" fill="#102345">VERKSTED</text>
      <rect x="315" y="474" width="105" height="20" rx="6" fill="#1b6f96" stroke="#53eff2" stroke-width="2"/><text x="367" y="489" text-anchor="middle" font-size="14" font-weight="700" fill="#d8f5f7">SHOWROOM</text>
      <rect x="424" y="474" width="69" height="20" rx="6" fill="#1b6f96" stroke="#53eff2" stroke-width="2"/><text x="458" y="489" text-anchor="middle" font-size="14" font-weight="700" fill="#d8f5f7">KJØR!</text>
    </svg>'''
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out / "workshop-chrome.png"), output_width=2000, output_height=2000)


def main() -> int:
    ap = argparse.ArgumentParser(description="Install the fixed original-style 500x500 Mujaffa workshop")
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    project = args.project.resolve()
    scene_path = project / "main.scene.json"
    scene = json.loads(scene_path.read_text(encoding="utf-8"))
    chrome = project / "assets" / "generated" / "workshop-ui"
    make_chrome(chrome)

    remove_prefixes = ("garage-ui-", "garage-polish-")
    scene["entities"] = [e for e in scene["entities"] if not str(e.get("id", "")).startswith(remove_prefixes) and e.get("id") not in ("garage-controller",)]

    # Canonical fixed stage. No phone-specific composition, drawers, sheets or
    # hamburger menus. The original 500x500 game scales as one intact surface.
    scene["entities"].extend([
        world_image("workshop-room", "Original Workshop Room", "assets/generated/showroom/showroom-room.png", -6),
        world_image("workshop-mujaffa", "Original Workshop Mujaffa", "assets/generated/showroom/showroom-mujaffa.png", 20),
        world_image("workshop-panel", "Original Workshop Panel", "assets/generated/showroom/showroom-panel.png", 90),
        world_image("workshop-chrome", "Original Workshop Chrome", "assets/generated/workshop-ui/workshop-chrome.png", 120),
        {"id": "garage-ui-desktop", "name": "Garage Desktop UI", "transform_3d": transform(), "components": {"sindri.ui.shape": {"kind": "rect", "fill": [0,0,0,0], "anchor": "center", "layer": 199}}},
        {"id": "garage-ui-mobile", "name": "Garage Mobile UI", "disabled": True, "transform_3d": transform(), "components": {"sindri.ui.shape": {"kind": "rect", "fill": [0,0,0,0], "anchor": "center", "layer": 199}}},
    ])

    # Interactive hit boxes follow the original left-hand equipment list. They
    # are intentionally invisible: the visible controls are the workshop art.
    mapped = [
        ("paint", "PAINT"), ("spoiler", "SPOILER"), ("exhaust", "EXHAUST"),
        ("rims", "RIMS"), ("tyres", "TYRES"), ("windows", "WINDOWS"),
        ("sunroof", "SUNROOF"), ("interior", "INTERIOR"), ("windscreen", "WINDSCREEN"),
    ]
    row_y = {"paint":0.445,"spoiler":0.245,"exhaust":0.145,"rims":0.045,"tyres":-0.055,"windows":-0.155,"sunroof":-0.255,"interior":-0.455,"windscreen":-0.555}
    for key, label in mapped:
        scene["entities"].append(ui_button(f"garage-ui-desktop-category-{key}", f"Desktop Category {label}", (-0.695, row_y[key], 0.0), (0.20, 0.042, 1.0), label))

    # Dummy category entities preserve the current Garage script's expected
    # lookup surface for categories that live as workshop sub-options.
    scene["entities"].append(ui_button("garage-ui-desktop-category-stripes", "Desktop Category STRIPES", (0.69,-0.22,0), (0.24,0.12,1), "STRIPES"))
    scene["entities"].extend([
        ui_button("garage-ui-desktop-prev", "Desktop Previous Part", (-0.46,0.445,0), (0.025,0.05,1), "Previous"),
        ui_button("garage-ui-desktop-next", "Desktop Next Part", (-0.40,0.445,0), (0.025,0.05,1), "Next"),
        # Hidden mobile aliases stop the legacy controller from looking up null
        # while guaranteeing there is no mobile-specific presentation.
        {**ui_button("garage-ui-mobile-prev", "Mobile Previous Part", (0,0,0), (0.001,0.001,1), "Previous", True), "parent":"garage-ui-mobile"},
        {**ui_button("garage-ui-mobile-next", "Mobile Next Part", (0,0,0), (0.001,0.001,1), "Next", True), "parent":"garage-ui-mobile"},
    ])
    for key, label in [("paint","PAINT"),("tyres","TYRES"),("rims","RIMS"),("spoiler","SPOILER"),("exhaust","EXHAUST"),("windows","WINDOWS"),("sunroof","SUNROOF"),("interior","INTERIOR"),("stripes","STRIPES"),("windscreen","WINDSCREEN")]:
        scene["entities"].append({**ui_button(f"garage-ui-mobile-category-{key}", f"Mobile Category {label}", (0,0,0), (0.001,0.001,1), label, True), "parent":"garage-ui-mobile"})

    scene["entities"].append({
        "id": "garage-controller", "name": "Garage Controller", "transform_3d": transform(),
        "components": {"sindri.script": {"source": "scripts/garage.decay", "script": "Garage", "properties": {}, "enabled": True}},
    })
    scene_path.write_text(json.dumps(scene, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # Patch only the legacy responsive layout branch. Customization logic stays
    # shared and unchanged; presentation is now permanently the original stage.
    garage = project / "scripts" / "garage.decay"
    text = garage.read_text(encoding="utf-8")
    old = '''    fn refresh_layout() {\n        let aspect = max(Viewport.aspect, 0.001);\n        let phone = aspect < 0.78;\n        World.set_active(this.mobile, phone);\n        World.set_active(this.desktop, !phone);\n        let car = this.car;\n        if phone {\n            car.transform.position.x = 0.0;\n            car.transform.position.y = 1.25;\n            car.transform.scale.x = 0.72;\n            car.transform.scale.y = 0.72;\n        } else {\n            car.transform.position.x = 0.55;\n            car.transform.position.y = 0.10;\n            car.transform.scale.x = 1.0;\n            car.transform.scale.y = 1.0;\n        }\n    }'''
    new = '''    fn refresh_layout() {\n        World.set_active(this.desktop, true);\n        World.set_active(this.mobile, false);\n        let car = this.car;\n        car.transform.position.x = 0.0;\n        car.transform.position.y = 0.0;\n        car.transform.scale.x = 1.0;\n        car.transform.scale.y = 1.0;\n    }'''
    if old not in text:
        raise SystemExit("Garage.refresh_layout changed; update fixed workshop installer")
    garage.write_text(text.replace(old, new, 1), encoding="utf-8")
    print("installed fixed 500x500 original-style workshop; no mobile-specific UI remains")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
