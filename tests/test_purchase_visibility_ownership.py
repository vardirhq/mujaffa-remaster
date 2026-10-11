from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ROUTER=(ROOT/"scripts/workshop_category_controller.decay").read_text()

def test_category_router_controls_purchase_visibility():
    assert "fn refresh_new_purchase_visibility()" in ROUTER
    assert "refresh_panels();refresh_new_purchase_visibility();" in ROUTER
    assert "layout_new_purchases(); refresh_new_purchase_visibility();" in ROUTER
    for field in ("horn_buy1","horn_buy2","camera_buy1"):
        assert f"World.set_active(this.{field}," in ROUTER

def test_no_competing_visibility_writers():
    for name in ("horn","camera"):
        script=(ROOT/f"scripts/workshop_{name}_controller.decay").read_text()
        assert "World.set_active(" not in script
