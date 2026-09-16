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

from swf_layout import placements  # noqa: E402

sys.path.insert(0, str(ROOT))
from tools.install_workshop_interactivity import AUDIO_SLOT_X, audio_row_y  # noqa: E402
from swf_workshop_economy import purchases  # noqa: E402

SWF = ROOT / "mujaffa_3juni_2003.swf"
CONTROLLER = ROOT / "scripts" / "workshop_audio_controller.decay"
INSTALLER = ROOT / "tools" / "install_workshop_interactivity.py"
DATA = ROOT / "reference" / "original-workshop-data.json"

# The speaker sprites, in the order the panel lists them, and the sprite the
# workshop draws them in.
SPEAKER_SPRITES = [236, 243, 247, 257]
WORKSHOP_PANEL = 924


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


def test_panel_spacing_matches_the_original(audio):
    """The one geometry claim: the row spacing, taken from the workshop's panel.

    The speaker rows are placed twice. Sprite 258 spaces them at a tidy 25px;
    sprite 924 spaces them 26.35/26.4/26.4. 924 is the workshop's -- it is placed
    at the stage's lower panel, where this category is drawn, and 258 sits
    mid-stage. Taking the tidy one would be inventing a neater game than the
    original, so this pins the uneven one.

    Both are differences within a single parent, so the parent's placement and
    scale cancel. The panel's own position on the stage is the remaster's and is
    not claimed here.
    """
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    from swf_inventory import iter_tags, parse_header

    data, header = parse_header(SWF.read_bytes())
    found = placements(iter_tags(data, header.tags_offset))

    rows = [p for p in found if p.character in SPEAKER_SPRITES and p.parent == WORKSHOP_PANEL]
    assert len(rows) == len(SPEAKER_SPRITES), "every speaker row is placed inside the workshop panel"
    ys = sorted(p.y for p in rows)
    original = [round(later - earlier, 3) for earlier, later in zip(ys, ys[1:])]

    installed = [audio_row_y(index) for index in range(len(SPEAKER_SPRITES))]
    ours = [round(later - earlier, 3) for earlier, later in zip(installed, installed[1:])]
    assert ours == original, f"installed rows are spaced {ours}, the original {original}"
    assert original != [25.0, 25.0, 25.0], "the workshop panel is the uneven one, not sprite 258"

    # A row sprite holds labels and artwork as well, so only the characters that
    # actually charge money count as buttons.
    charging = {purchase.character for purchase in purchases(SWF.read_bytes())}
    buttons = [p for p in found if p.parent in SPEAKER_SPRITES and p.character in charging and p.x is not None]
    columns = sorted({round(p.x, 3) for p in buttons})
    assert columns == list(AUDIO_SLOT_X), f"installer slots {list(AUDIO_SLOT_X)}, original {columns}"

    # The woofer is the row that proves the slots are indexed by level: it is the
    # only one that buys in the leftmost slot, because it is the only one that
    # starts at nothing.
    woofer = {round(p.x, 3) for p in buttons if p.parent == 257}
    others = {round(p.x, 3) for p in buttons if p.parent != 257}
    assert woofer == set(AUDIO_SLOT_X), "the woofer charges in all three slots"
    assert min(others) > min(woofer), "only the woofer uses the leftmost slot"


def test_a_refused_sale_does_not_fit_the_speakers():
    """The till settles a frame later, so the upgrade waits for the grant."""
    source = CONTROLLER.read_text(encoding="utf-8")
    assert 'Game.set("workshop.buy.ticket", this.ticket);' in source
    assert 'Game.get("workshop.buy.settled", 0.0) != this.ticket { return; }' in source
    assert 'if Game.get("workshop.buy.granted", 0.0) > 0.0 { apply(' in source
