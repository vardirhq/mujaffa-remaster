"""SPOILER: what it charges, what it is worth, and which wing shows.

The stereo accumulates; a spoiler replaces. Going from the 2200 wing to the 4000
one is worth 0.15 rather than 0.3, because the original takes the fitted wing's
contribution off before adding the new one. These pin that difference, since a
controller that added the target outright would look right on a bare car and
overpay coolness on every upgrade after the first.
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from swf_workshop_economy import purchases  # noqa: E402
from tools.install_workshop_interactivity import SPOILER_OPTIONS  # noqa: E402

SWF = ROOT / "mujaffa_3juni_2003.swf"
CONTROLLER = ROOT / "scripts" / "workshop_spoiler_controller.decay"
DATA = ROOT / "reference" / "original-workshop-data.json"


@pytest.fixture(scope="module")
def spoiler():
    return [c for c in json.loads(DATA.read_text(encoding="utf-8"))["categories"] if c["id"] == "spoiler"][0]


@pytest.fixture(scope="module")
def recovered():
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    return {p.character: p for p in purchases(SWF.read_bytes())}


def test_each_wing_charges_what_its_button_charges(spoiler, recovered):
    for option in spoiler["options"]:
        purchase = recovered[option["source_button"]]
        assert purchase.price == option["price"], f"wing {option['value']}"
        assert purchase.cool[0] == "spoiler_cool", "the original tracks the fitted wing's worth"
        assert purchase.cool[1] == pytest.approx(option["cool_effect"]["target"]), f"wing {option['value']}"


def test_controller_charges_and_is_worth_what_the_swf_says(spoiler):
    source = CONTROLLER.read_text(encoding="utf-8")

    def body(name):
        start = source.index(f"fn {name}(value: f32) -> f32 {{")
        return source[start:source.index("\n    }", start)]

    # Scoped per function: `worth` legitimately returns 0.0 for a bare boot, and
    # that is not a price.
    prices = {int(match) for match in re.findall(r"return (\d+)\.0;", body("price"))}
    worths = {float(match) for match in re.findall(r"return (0\.\d+);", body("worth"))}
    expected_prices = {option["price"] for option in spoiler["options"]}
    expected_worths = {option["cool_effect"]["target"] for option in spoiler["options"]}
    assert prices == expected_prices, f"controller charges {sorted(prices)}, original {sorted(expected_prices)}"
    # Plus the bare boot's nothing, which is a state rather than a wing.
    assert worths == expected_worths | {0.0}, (
        f"controller values {sorted(worths)}, original {sorted(expected_worths)} and a bare boot"
    )


def test_upgrading_sends_the_difference_not_the_total():
    """The line that separates a replacement from an accumulation."""
    source = CONTROLLER.read_text(encoding="utf-8")
    assert 'Game.set("workshop.buy.cred", worth(value) - worth(this.fitted));' in source
    assert "fn worth(value: f32)" in source
    assert "if value == 0.0 { return 0.0; }" in source, "a bare boot is worth nothing"


def test_installer_and_reference_agree_on_every_wing(spoiler):
    listed = {(value, price, button) for value, price, button in SPOILER_OPTIONS}
    expected = {(o["value"], o["price"], o["source_button"]) for o in spoiler["options"]}
    assert listed == expected


def test_exactly_one_wing_is_visible(spoiler):
    """The car carries all five layers; fitting one is choosing which shows.

    The original's frame numbers are the layer numbers, offset by the bare boot
    the car starts on, so wing N is `Garage Car spoiler-{N+1}`.
    """
    source = CONTROLLER.read_text(encoding="utf-8")
    for option in spoiler["options"]:
        assert f'World.find("Garage Car spoiler-{option["frame"]}")' in source, f"wing {option['value']}"
        assert option["frame"] == option["value"] + 1, "frame numbering is the layer numbering"
    assert 'World.find("Garage Car spoiler-1")' in source, "the bare boot is a layer too"
    shown = re.findall(r"World\.set_active\(this\.layer\d, this\.fitted == (\d)\.0\);", source)
    assert shown == ["0", "1", "2", "3", "4"], "each wing shows for exactly one state"


def test_a_refused_sale_does_not_fit_a_wing():
    source = CONTROLLER.read_text(encoding="utf-8")
    assert 'Game.get("workshop.buy.settled", 0.0) != this.ticket { return; }' in source
    assert 'if Game.get("workshop.buy.granted", 0.0) > 0.0 {' in source
    granted = source.index('if Game.get("workshop.buy.granted", 0.0) > 0.0 {')
    assert "this.fitted = this.pending;" in source[granted:granted + 200], "the wing is fitted only once paid for"
