from pathlib import Path
from tools.workshop_catalog import CATEGORIES

def test_controller_routes_every_original_category():
    text = Path("scripts/workshop_category_controller.decay").read_text(encoding="utf-8")
    for index, entry in enumerate(CATEGORIES):
        assert f'World.find("Workshop Category {entry["label"]}")' in text
        assert f"this.category = {float(index):.1f};" in text
