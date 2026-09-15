#!/usr/bin/env python3
from pathlib import Path
state = Path("scripts/workshop_state.decay").read_text(encoding="utf-8")
required = [
    "var free_purchases: bool = true;",
    "var money: f32 = 5000.0;",
    "var street_cred: f32 = 0.0;",
    "if this.free_purchases",
    "this.money = this.money - price;",
]
missing = [item for item in required if item not in state]
if missing:
    raise SystemExit("workshop free-mode contract missing: " + ", ".join(missing))
print("workshop free-mode contract OK")
