"""Regression checks for the first RUTER/SOLTAK gameplay slice."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTROLLER = (ROOT / "scripts/workshop_windows_controller.decay").read_text()
INSTALLER = (ROOT / "tools/install_workshop_interactivity.py").read_text()


def test_original_prices_and_coolness():
    for amount in (700, 900, 1300, 1500):
        assert f"{amount}.0" in CONTROLLER
    for worth in ("0.05", "0.1", "0.2"):
        assert f"return {worth};" in CONTROLLER
    assert 'worth(value)-worth(this.windows)' in CONTROLLER
    assert 'Game.set("workshop.buy.cred",0.2)' in CONTROLLER


def test_all_original_car_variants_are_wired():
    for variant in ("standard", "gradient", "tonede", "spejlrefleks"):
        assert f"Garage Car vinduer-{variant}" in CONTROLLER
    for variant in ("off", "on"):
        assert f"Garage Car soltag-{variant}" in CONTROLLER


def test_purchases_use_shared_ticket_and_settle_before_fitting():
    assert 'Game.get("workshop.buy.ticket",0.0)+1.0' in CONTROLLER
    assert 'Game.get("workshop.buy.settled",0.0)!=this.ticket' in CONTROLLER
    assert 'Game.get("workshop.buy.granted",0.0)>0.0' in CONTROLLER
    assert "scene['entities'].extend(glass_entities())" in INSTALLER
    assert '"scripts/workshop_windows_controller.decay"' in INSTALLER
