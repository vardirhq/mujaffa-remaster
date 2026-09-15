from pathlib import Path
from tools.workshop_catalog import CATEGORIES


def test_controller_routes_every_original_category():
    text = Path("scripts/workshop_category_controller.decay").read_text(encoding="utf-8")
    for index, entry in enumerate(CATEGORIES):
        assert f'World.find("Workshop Category {entry["label"]}")' in text
        assert f"set_category({float(index):.1f});" in text


def test_category_is_shared_and_visible():
    text = Path("scripts/workshop_category_controller.decay").read_text(encoding="utf-8")
    assert 'Game.set("workshop.category", value);' in text
    assert "marker.transform.position.y" in text
    assert "refresh_panels();" in text
    for entry in CATEGORIES[1:]:
        assert f'World.find("Workshop Panel {entry["label"]}")' in text
