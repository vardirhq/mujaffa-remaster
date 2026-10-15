"""LAKKERING `skift` (button 395) is the paint purchase."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAINT = (ROOT / "scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
GARAGE = (ROOT / "scripts/garage.decay").read_text(encoding="utf-8")


def test_skift_charges_500_and_replaces_the_paint_cred():
    assert 'Game.set("workshop.buy.price", 500.0);' in PAINT
    assert 'Game.set("workshop.buy.cred", 0.15 - this.paint_cool);' in PAINT
    assert "this.paint_cool = 0.15;" in PAINT


def test_the_mixer_opens_only_when_paid_for():
    settle = PAINT[PAINT.index("fn settle_paint()"):PAINT.index("fn update(")]
    assert 'Game.get("workshop.buy.granted", 0.0) > 0.0' in settle and "set_mixer(true)" in settle
    assert "set_mixer(true)" not in PAINT[PAINT.index("fn update("):]


def test_the_garage_ignores_the_arrow_keys():
    # The drive steers with them; the garage used to repaint the car grey.
    assert "ArrowLeft" not in GARAGE and "ArrowRight" not in GARAGE
