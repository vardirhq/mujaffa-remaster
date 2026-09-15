from pathlib import Path

from tools.workshop_catalog import CATEGORIES


def test_interactivity_foundation():
    ids = [f"workshop-category-{entry['id']}" for entry in CATEGORIES]
    assert len(ids) == len(set(ids)) == 13
    assert all("price" not in entry for entry in CATEGORIES)


def test_category_controls_render_their_own_art():
    source = Path("tools/install_workshop_interactivity.py").read_text(encoding="utf-8")
    assert '"sindri.ui.image"' in source
    assert '"sindri.ui.button"' in source
    assert 'category-{entry[\'id\']}.png' in source
    assert '"sindri.ui.shape": {"kind": "rect", "fill": [0, 0, 0, 0.001]' not in source


def test_baked_chrome_does_not_duplicate_category_buttons():
    chrome = Path("tools/refine_workshop_chrome.py").read_text(encoding="utf-8")
    assert "Category controls are separate real UI entities" in chrome
    for entry in CATEGORIES:
        assert entry["label"] not in chrome


def test_category_layout_tracks_square_stage_on_portrait_viewports():
    controller = Path("scripts/workshop_category_controller.decay").read_text(encoding="utf-8")
    assert "min(Viewport.aspect, 1.0)" in controller
    assert "145.0 * unit" in controller
    assert "24.0 * unit" in controller
    assert "layout_controls();" in controller


def test_paint_controls_are_real_touch_targets():
    installer = Path("tools/install_workshop_interactivity.py").read_text(encoding="utf-8")
    for asset in ("paint-change.png", "stripe-none.png", "stripe-white.png", "stripe-green.png", "stripe-black.png", "stripe-pink.png"):
        assert asset in installer
    for name in ("Workshop Paint Change", "Workshop Stripe None", "Workshop Stripe White", "Workshop Stripe Green", "Workshop Stripe Black", "Workshop Stripe Pink"):
        assert name in installer


def test_paint_controller_changes_car_and_shared_state():
    controller = Path("scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert 'Game.set("workshop.paint", index);' in controller
    assert 'Game.set("workshop.stripe", index);' in controller
    assert "body.sprite.tint.r" in controller
    assert "Garage Car farvestribe-empty" in controller
    assert "Garage Car farvestribe-hvid" in controller
    assert "Garage Car farvestribe-grøn" in controller
    assert "Garage Car farvestribe-sort" in controller
    assert "Garage Car farvestribe-pink" in controller
    assert "Ui.is_pressed(this.change_paint)" in controller
    assert "min(Viewport.aspect, 1.0)" in controller


def test_paint_controls_disappear_outside_paint_category():
    router = Path("scripts/workshop_category_controller.decay").read_text(encoding="utf-8")
    assert "let painting = this.category == 0.0;" in router
    assert "World.set_active(this.paint_change, painting);" in router
    assert "World.set_active(this.stripe_pink, painting);" in router
