#!/usr/bin/env python3
"""Replace the temporary workshop chrome with a closer 500x500 parity pass.

The actual room, Mujaffa and logo remain SWF-derived layers. This file only
covers foreground chrome that our current extractor cannot yet reconstruct as
Flash buttons/text. Coordinates follow the original 500x500 workshop capture.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import cairosvg

CATEGORIES = [
    "LAKKERING", "BILSTEREO", "SPOILER", "EKSOSANLEGG", "FELGER", "DEKK",
    "RUTER", "SOLTAK", "NUMMERSKILT", "SETETREKK", "BILNIPS", "BÅT-HORN", "BMW CAM",
]


def burst(y: float) -> str:
    # Original is a small yellow jagged badge with lowercase `ny`, not a star.
    pts = "11,0 14,5 20,3 19,9 25,11 20,15 22,21 15,19 11,24 8,19 2,21 4,15 0,11 5,8 3,3 9,5"
    return f'<g transform="translate(13 {y-11}) scale(.72)"><polygon points="{pts}" fill="#ffd719" stroke="#111" stroke-width="1.4"/><text x="11.5" y="14" text-anchor="middle" font-size="8" font-weight="700" font-style="italic" fill="#111">ny</text></g>'


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    out = args.project.resolve() / "assets" / "generated" / "workshop-ui" / "workshop-chrome.png"
    out.parent.mkdir(parents=True, exist_ok=True)

    buttons=[]
    y=137
    for index,label in enumerate(CATEGORIES):
        selected = index == 0
        left = f'<path d="M20 {y} l-7 -5 v10 z" fill="#219ac1" stroke="#111" stroke-width="1.2"/>' if selected else ""
        right = f'<path d="M132 {y} l7 -5 v10 z" fill="#219ac1" stroke="#111" stroke-width="1.2"/>' if selected else ""
        badge = burst(y) if label in ("BÅT-HORN","BMW CAM") else ""
        buttons.append(f'''{badge}{left}<rect x="27" y="{y-9}" width="102" height="16" rx="3" fill="#2ca2c8" stroke="#111827" stroke-width="2"/><text x="78" y="{y+2.5}" text-anchor="middle" font-size="10.5" font-weight="700" fill="#15151b">{label}</text>{right}''')
        y += 25

    svg=f'''<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000" viewBox="0 0 500 500">
      <!-- Header: the title belongs on the second blue strip in the original. -->
      <rect x="0" y="0" width="500" height="31" fill="#070936"/>
      <rect x="0" y="31" width="500" height="25" fill="#41608d"/>
      <text x="314" y="52" text-anchor="middle" font-size="24" font-weight="700" fill="#30517d">BHAIAS VERKSTED</text>
      <rect x="0" y="56" width="500" height="24" fill="#2d9dc0"/>
      <text x="151" y="72" font-size="10.5" font-weight="700" fill="#111">PENGER:</text><text x="204" y="72" font-size="13" font-weight="700" fill="#e8f3f0">5000</text>
      <text x="269" y="72" font-size="10.5" font-weight="700" fill="#111">BMW:</text><text x="309" y="72" font-size="13" font-weight="700" fill="#e8f3f0">1</text>
      <text x="372" y="72" font-size="10.5" font-weight="700" fill="#111">STREET CRED:</text><text x="469" y="72" font-size="13" font-weight="700" fill="#e8f3f0">0</text>

      <!-- Deliberate 4px gutters between the original UI islands. -->
      <rect x="4" y="83" width="145" height="381" rx="12" fill="#139bc3" stroke="#0c1039" stroke-width="4"/>
      <text x="76" y="108" text-anchor="middle" font-size="20" font-weight="800" fill="#d6ffff">UTSTYR</text>
      {''.join(buttons)}

      <rect x="153" y="351" width="343" height="111" rx="12" fill="#129bc4" stroke="#0b103b" stroke-width="4"/>
      <text x="175" y="377" font-size="14" font-weight="700" fill="#10131c">Lakker BMW</text>
      <text x="176" y="397" font-size="8.5" font-weight="700" fill="#10131c">Trykk “skift”</text>
      <text x="176" y="409" font-size="8.5" font-weight="700" fill="#10131c">for å endre farge</text>
      <rect x="179" y="416" width="52" height="34" rx="3" fill="#2a9ac3" stroke="#6b3150" stroke-width="2"/>
      <text x="205" y="439" text-anchor="middle" font-size="18" font-weight="700" fill="#ec3345">skift</text>
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
    cairosvg.svg2png(bytestring=svg.encode(), write_to=str(out), output_width=2000, output_height=2000)
    print(f"refined workshop chrome: {out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
