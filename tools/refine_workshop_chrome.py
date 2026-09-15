#!/usr/bin/env python3
"""Render the fixed 500x500 workshop chrome without interactive controls.

The room, Mujaffa and logo remain SWF-derived layers. Category controls are separate real UI entities.
Paint controls are separate real UI entities too, so visible pixels are the touch targets.
"""
from __future__ import annotations
import argparse
from pathlib import Path
import cairosvg


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--project", type=Path, default=Path("."))
    args = ap.parse_args()
    out = args.project.resolve() / "assets" / "generated" / "workshop-ui" / "workshop-chrome.png"
    out.parent.mkdir(parents=True, exist_ok=True)
    svg='''<svg xmlns="http://www.w3.org/2000/svg" width="2000" height="2000" viewBox="0 0 500 500">
      <rect x="0" y="0" width="500" height="31" fill="#070936"/><rect x="0" y="31" width="500" height="25" fill="#41608d"/>
      <text x="314" y="52" text-anchor="middle" font-size="24" font-weight="700" fill="#30517d">BHAIAS VERKSTED</text>
      <rect x="0" y="56" width="500" height="24" fill="#2d9dc0"/>
      <text x="151" y="72" font-size="10.5" font-weight="700" fill="#111">PENGER:</text><text x="204" y="72" font-size="13" font-weight="700" fill="#e8f3f0">5000</text>
      <text x="269" y="72" font-size="10.5" font-weight="700" fill="#111">BMW:</text><text x="309" y="72" font-size="13" font-weight="700" fill="#e8f3f0">1</text>
      <text x="372" y="72" font-size="10.5" font-weight="700" fill="#111">STREET CRED:</text><text x="469" y="72" font-size="13" font-weight="700" fill="#e8f3f0">0</text>
      <rect x="4" y="83" width="145" height="381" rx="12" fill="#139bc3" stroke="#0c1039" stroke-width="4"/><text x="76" y="108" text-anchor="middle" font-size="20" font-weight="800" fill="#d6ffff">UTSTYR</text>
      <rect x="153" y="351" width="343" height="111" rx="12" fill="#129bc4" stroke="#0b103b" stroke-width="4"/>
      <text x="175" y="377" font-size="14" font-weight="700" fill="#10131c">Lakker BMW</text><text x="176" y="397" font-size="8.5" font-weight="700" fill="#10131c">Trykk “skift”</text><text x="176" y="409" font-size="8.5" font-weight="700" fill="#10131c">for å endre farge</text><text x="345" y="378" font-size="14" font-weight="700" fill="#10131c">Fartstripe</text>
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
