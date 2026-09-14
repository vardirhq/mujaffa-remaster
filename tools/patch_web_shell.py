#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

OLD = "canvas { display: block; width: 100vw; height: 100vh; touch-action: none; }"
NEW = """body {
      display: grid;
      place-items: center;
      min-height: 100dvh;
      background: #111318;
    }
    canvas {
      display: block;
      width: min(100vw, 100dvh);
      height: min(100vw, 100dvh);
      aspect-ratio: 1 / 1;
      touch-action: none;
    }"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Keep Mujaffa's original square stage intact on every viewport")
    parser.add_argument("index", type=Path)
    args = parser.parse_args()

    text = args.index.read_text(encoding="utf-8")
    if OLD not in text:
        raise SystemExit("Sindri export shell changed: expected full-viewport canvas rule was not found")
    args.index.write_text(text.replace(OLD, NEW, 1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
