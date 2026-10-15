"""The UTSTYR panels come from sprite 924 and their buttons sit on its rects."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import install_workshop_panels as panels  # noqa: E402

SCRIPTS = ROOT / "scripts"


def test_every_option_button_has_its_rollover_price():
    prices = panels.rollover_prices((ROOT / "mujaffa_3juni_2003.swf").read_bytes())
    assert set(panels.BUTTONS) <= set(prices)
    # Spot checks against the original's `koster<n>:pris = <price>` rollovers.
    assert prices[395] == ("koster5", 500)
    assert prices[177] == ("koster1", 250)
    assert prices[391] == ("koster1", 450)
    assert prices[209] == ("koster1", 3000)
    assert prices[915] == ("koster2", 6000)


def test_every_remaster_button_named_by_the_panels_exists():
    installer = (ROOT / "tools/install_workshop_interactivity.py").read_text(encoding="utf-8")
    sources = installer + "".join(path.read_text(encoding="utf-8") for path in SCRIPTS.glob("workshop_*.decay"))
    for button in panels.BUTTONS.values():
        assert f"Workshop {button}" in sources, button


def test_panel_art_shows_every_category_and_tag():
    art = (SCRIPTS / "workshop_panel_art.decay").read_text(encoding="utf-8")
    for _, label, _, clips in panels.CATEGORIES:
        for _, key in clips:
            assert f'clip("{label}", "{key}"' in art
    for button in panels.BUTTONS.values():
        assert f'tag("{button}")' in art
    # LAKKERING's picture steps aside for the RGB mixer.
    paint = (SCRIPTS / "workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert 'Game.set("workshop.paint.mixing", 1.0)' in paint
    assert 'Game.get("workshop.paint.mixing", 0.0)' in art


def test_stripes_are_bought_at_the_original_price():
    paint = (SCRIPTS / "workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert 'Game.set("workshop.buy.price", 250.0);' in paint
    assert re.search(r"Ui.is_pressed\(this.stripe_white\) \{ ask_stripe\(1.0\); \}", paint)


def test_buttons_sit_on_the_original_rects():
    trinket = (SCRIPTS / "workshop_trinket_controller.decay").read_text(encoding="utf-8")
    for x in ("255.1", "319.0", "382.8", "446.6"):
        assert f"place(this.buy" in trinket and f"{x},418.9,59.4,38.9" in trinket
    router = (SCRIPTS / "workshop_category_controller.decay").read_text(encoding="utf-8")
    assert "this.camera_buy1.transform.position.x=(283.3-250.0)*unit;" in router
    plate = (SCRIPTS / "workshop_plate_controller.decay").read_text(encoding="utf-8")
    assert "this.edit.transform.position.x=(215.6-250.0)*unit;" in plate
    paint = (SCRIPTS / "workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert "place(this.change_paint, 213.87, 426.92, 57.2, 33.3, unit);" in paint


def test_pages_installs_the_panels_last():
    workflow = (ROOT / ".github/workflows/pages.yml").read_text(encoding="utf-8")
    assert workflow.index("install_drive.py") < workflow.index("install_workshop_panels.py")
