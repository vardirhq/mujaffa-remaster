"""EKSOSANLEGG: the original's odd arithmetic, kept on purpose.

Three ways of moving `bil_cool` have turned up now. Paint and spoilers replace,
taking the fitted part's worth off first. The stereo accumulates, but each set
is bought once. The exhaust accumulates and never clears `udstodning_cool`,
which its own initialiser defines -- so the pipes do not cancel each other and
fitting all three in turn is worth 0.6 rather than 0.3.

These pin that as recovered behaviour rather than a bug someone will later
"fix", and pin the rule that keeps it bounded: the original will not sell you
the pipe you are wearing.
"""

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from swf_inventory import iter_tags, parse_header  # noqa: E402
from swf_layout import placements  # noqa: E402
from swf_workshop_economy import purchases  # noqa: E402
from tools.install_workshop_interactivity import EXHAUST_OPTIONS  # noqa: E402

SWF = ROOT / "mujaffa_3juni_2003.swf"
CONTROLLER = ROOT / "scripts" / "workshop_exhaust_controller.decay"
DATA = ROOT / "reference" / "original-workshop-data.json"
EXHAUST_ROW = 267
FITTED_GRAPHIC = 140            # swapped into the slot of the pipe you own


@pytest.fixture(scope="module")
def exhaust():
    return [c for c in json.loads(DATA.read_text(encoding="utf-8"))["categories"] if c["id"] == "exhaust"][0]


@pytest.fixture(scope="module")
def recovered():
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    return {p.character: p for p in purchases(SWF.read_bytes())}


def test_each_pipe_charges_and_gains_what_its_button_does(exhaust, recovered):
    for option in exhaust["options"]:
        purchase = recovered[option["source_button"]]
        assert purchase.price == option["price"], f"pipe {option['value']}"
        assert purchase.cool_delta == pytest.approx(option["cool_effect"]["delta"]), f"pipe {option['value']}"


def test_the_original_never_clears_the_fitted_pipe(recovered, exhaust):
    """The quirk itself: a flat add, and no `udstodning_cool` in sight.

    If a future pass "corrects" the original by subtracting the old pipe, this
    fails -- which is the point. The SWF is the authority on what it did.
    """
    for option in exhaust["options"]:
        purchase = recovered[option["source_button"]]
        assert purchase.cool is None, (
            f"pipe {option['value']} would have to touch a *_cool variable for a replacement"
        )
        assigned = {name for name, _value in purchase.assignments}
        assert "udstodning_cool" not in assigned
        assert assigned == {"penge", "udstodning", "bil_cool"}


def test_controller_keeps_the_additive_arithmetic(exhaust):
    source = CONTROLLER.read_text(encoding="utf-8")

    def body(name):
        start = source.index(f"fn {name}(value: f32) -> f32 {{")
        return source[start:source.index("\n    }", start)]

    prices = {int(match) for match in re.findall(r"return (\d+)\.0;", body("price"))}
    gains = {float(match) for match in re.findall(r"return (0\.\d+);", body("gain"))}
    assert prices == {option["price"] for option in exhaust["options"]}
    assert gains == {option["cool_effect"]["delta"] for option in exhaust["options"]}
    # The line that would turn this into a replacement, which the original is not.
    assert "gain(value) - " not in source
    assert 'Game.set("workshop.buy.cred", gain(value));' in source


def test_the_fitted_pipe_is_not_for_sale():
    """What keeps 0.6 the ceiling rather than the first step of a grind."""
    source = CONTROLLER.read_text(encoding="utf-8")
    for value in (1, 2, 3):
        assert f"World.set_active(this.buy{value}, showing && this.fitted != {value}.0);" in source
    assert "if this.fitted == value { return; }" in source


def test_the_original_swaps_a_graphic_into_the_fitted_slot(recovered):
    """Evidence for the rule above, rather than a design decision of mine."""
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    data, header = parse_header(SWF.read_bytes())
    found = placements(iter_tags(data, header.tags_offset))

    inside = [p for p in found if p.parent == EXHAUST_ROW and p.x is not None]
    buying = {round(p.x, 2) for p in inside if p.character in recovered}
    fitted = {round(p.x, 2) for p in inside if p.character == FITTED_GRAPHIC}
    assert buying, "the row holds the three buy buttons"
    assert buying <= fitted, (
        f"every buy slot {sorted(buying)} also carries the fitted graphic {sorted(fitted)}"
    )


def test_installer_and_reference_agree(exhaust):
    listed = {(value, price, button) for value, price, button in EXHAUST_OPTIONS}
    expected = {(o["value"], o["price"], o["source_button"]) for o in exhaust["options"]}
    assert listed == expected


def test_exactly_one_pipe_is_visible(exhaust):
    source = CONTROLLER.read_text(encoding="utf-8")
    for option in exhaust["options"]:
        assert f'World.find("Garage Car udstodning-{option["frame"]}")' in source
        assert option["frame"] == option["value"] + 1
    assert 'World.find("Garage Car udstodning-1")' in source, "the stock pipe is a layer too"
    shown = re.findall(r"World\.set_active\(this\.layer\d, this\.fitted == (\d)\.0\);", source)
    assert shown == ["0", "1", "2", "3"]
