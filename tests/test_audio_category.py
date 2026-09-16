"""BILSTEREO: the prices it charges, and the spacing it inherits.

The stereo is the first category with an economy, so it is the first that can
get one wrong. Every number in the controller is checked against the SWF rather
than against the reference file alone, so a typo here fails even if the
reference and the script agree with each other.
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from swf_workshop_economy import purchases  # noqa: E402

SWF = ROOT / "mujaffa_3juni_2003.swf"
CONTROLLER = ROOT / "scripts" / "workshop_audio_controller.decay"
INSTALLER = ROOT / "tools" / "install_workshop_interactivity.py"
DATA = ROOT / "reference" / "original-workshop-data.json"

# Where the panel puts these is `test_panel_layout.py`; this file is about what
# they cost.


@pytest.fixture(scope="module")
def audio():
    return [c for c in json.loads(DATA.read_text(encoding="utf-8"))["categories"] if c["id"] == "audio"][0]


@pytest.fixture(scope="module")
def recovered():
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    return {p.character: p for p in purchases(SWF.read_bytes())}


def test_every_transition_the_reference_claims_is_in_the_swf(audio, recovered):
    """Price and coolness together, per button, including the partial upgrades."""
    checked = 0
    for group in audio["option_groups"]:
        for option in group["options"]:
            claims = ([(option["source_button"], option["cool_delta"])] if option.get("source_button")
                      else [(t["source_button"], t["cool_delta"]) for t in option.get("transitions", [])])
            for button, delta in claims:
                purchase = recovered.get(button)
                assert purchase is not None, f"{group['id']}->{option['value']}: button {button} charges nothing"
                assert purchase.price == option["price"], (
                    f"{group['id']}->{option['value']}: button {button} charges {purchase.price}, "
                    f"reference says {option['price']}"
                )
                assert purchase.cool_delta == pytest.approx(delta), (
                    f"{group['id']}->{option['value']}: button {button} moves cool by "
                    f"{purchase.cool_delta}, reference says {delta}"
                )
                checked += 1
    assert checked == 15, "all fifteen stereo transitions are covered"


def test_controller_charges_what_the_swf_charges(audio):
    """The prices written into the Decay script, against the original's."""
    source = CONTROLLER.read_text(encoding="utf-8")
    prices = {int(match) for match in re.findall(r"return (\d+)\.0;", source)}
    expected = {option["price"] for group in audio["option_groups"] for option in group["options"]}
    assert expected <= prices, f"controller is missing prices {sorted(expected - prices)}"
    # And nothing beyond them: an invented price would show up here.
    assert prices <= expected, f"controller charges prices the original does not: {sorted(prices - expected)}"


def test_controller_steps_cool_by_the_swf_amount(audio, recovered):
    """Each set is worth a fixed amount per level, so a jump is a multiple of it.

    Front 1->3 costs the same as front 2->3 but is worth twice as much, which is
    the whole reason the controller multiplies rather than looking up a table.
    """
    source = CONTROLLER.read_text(encoding="utf-8")
    steps = [float(match) for match in re.findall(r"return (0\.\d+);", source)]
    for group in audio["option_groups"]:
        singles = [o for o in group["options"] if o.get("cool_delta") is not None]
        assert singles, f"{group['id']} has no single-level upgrade to take a step from"
        step = singles[0]["cool_delta"]
        assert step in steps, f"{group['id']}: controller never steps by {step}"
        for option in group["options"]:
            for transition in option.get("transitions", []):
                jump = transition["cool_delta"] / step
                assert jump == pytest.approx(round(jump)), (
                    f"{group['id']}->{option['value']}: {transition['cool_delta']} is not a multiple of {step}"
                )


def test_installer_labels_buttons_with_the_original_prices(audio):
    source = INSTALLER.read_text(encoding="utf-8")
    listed = {int(price) for price in re.findall(r"\((?:\d),(\d+)\)", source)}
    expected = {option["price"] for group in audio["option_groups"] for option in group["options"]}
    assert expected <= listed, f"installer is missing prices {sorted(expected - listed)}"


def test_a_refused_sale_does_not_fit_the_speakers():
    """The till settles a frame later, so the upgrade waits for the grant."""
    source = CONTROLLER.read_text(encoding="utf-8")
    assert 'Game.set("workshop.buy.ticket", this.ticket);' in source
    assert 'Game.get("workshop.buy.settled", 0.0) != this.ticket { return; }' in source
    assert 'if Game.get("workshop.buy.granted", 0.0) > 0.0 { apply(' in source
