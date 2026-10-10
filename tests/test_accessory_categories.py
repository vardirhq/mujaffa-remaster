"""Gameplay wiring for SETETREKK, BILNIPS and existing EKSOSANLEGG."""
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INSTALL=(ROOT/"tools/install_workshop_interactivity.py").read_text()
for_script=lambda name:(ROOT/f"scripts/workshop_{name}_controller.decay").read_text()

def test_original_prices_and_ticket_protocol():
    for name,prices in (("interior",(500,1500,4000)),("trinket",(25,50,70,125)),("stripe",(250,))):
        source=for_script(name)
        for price in prices: assert f"{price}.0" in source
        assert 'Game.get("workshop.buy.ticket",0.0)+1.0' in source
        assert 'Game.get("workshop.buy.granted",0.0)>0.0' in source
        assert f'"scripts/workshop_{name}_controller.decay"' in INSTALL

def test_original_car_layer_names():
    for name,variants in (("interior",("polyester","tiger","læder","skind")),
                          ("trinket",("empty","hjerte","wunderbaum","nosser","koran")),
                          ("stripe",("empty","grøn","hvid","sort","pink"))):
        source=for_script(name)
        for variant in variants: assert f"-{variant}" in source

def test_exhaust_already_playable():
    source=for_script("exhaust")
    for price in (300,900,2700): assert f"{price}.0" in source
    assert 'Game.set("workshop.buy.cred", gain(value))' in source
