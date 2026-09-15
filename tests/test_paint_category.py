from pathlib import Path


def test_paint_slice_has_dedicated_controller():
    source = Path("scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert "script WorkshopPaintController" in source
    assert "next_paint();" in source
    assert source.count("set_stripe(") >= 6


def test_paint_slice_does_not_fake_economy_values():
    source = Path("scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert "purchase(" not in source
    assert "street_cred" not in source
    assert "money" not in source
