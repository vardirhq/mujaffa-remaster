from pathlib import Path

def test_workshop_state_contract():
    text = Path("scripts/workshop_state.decay").read_text(encoding="utf-8")
    for needle in ("var free_purchases: bool = true", "var money: f32 = 5000.0", "if this.free_purchases", "this.money = this.money - price"):
        assert needle in text
    for name in ("paint", "audio", "spoiler", "exhaust", "rims", "tyres", "windows", "sunroof", "plate", "interior", "trinket", "horn", "camera"):
        assert f"var {name}: f32" in text
