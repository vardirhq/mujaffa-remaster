"""FELGER and DEKK: two categories, one set of wheels.

The car carries a rim layer for every (tyre, rim) pair, so neither category can
decide what shows without the other's state. One controller owns the grid, and
these pin that it covers all sixteen combinations -- a missing pair would leave
the wheels blank for exactly one tyre-and-rim choice, which is the sort of thing
that only shows up after someone buys the fourth tyre.
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
from tools.install_workshop_interactivity import RIMS_OPTIONS, TYRES_OPTIONS  # noqa: E402

SWF = ROOT / "mujaffa_3juni_2003.swf"
CONTROLLER = ROOT / "scripts" / "workshop_wheels_controller.decay"
DATA = ROOT / "reference" / "original-workshop-data.json"
RIM_NAMES = ["standard", "racer", "krom", "guld"]
ROWS = {"rims": 199, "tyres": 156}
FITTED_GRAPHIC = 140


@pytest.fixture(scope="module")
def categories():
    data = json.loads(DATA.read_text(encoding="utf-8"))
    return {c["id"]: c for c in data["categories"]}


@pytest.fixture(scope="module")
def recovered():
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    return {p.character: p for p in purchases(SWF.read_bytes())}


@pytest.mark.parametrize("category", ["rims", "tyres"])
def test_each_option_charges_what_its_button_charges(categories, recovered, category):
    for option in categories[category]["options"]:
        purchase = recovered[option["source_button"]]
        assert purchase.price == option["price"], f"{category} {option['value']}"
        assert purchase.cool[1] == pytest.approx(option["cool_effect"]["target"]), f"{category} {option['value']}"


def test_controller_charges_and_values_what_the_swf_says(categories):
    source = CONTROLLER.read_text(encoding="utf-8")

    def body(name):
        head = source.index(f"fn {name}(value: f32) -> f32 {{")
        return source[head:source.index("\n    }", head)]

    for category, price_fn, worth_fn in (("rims", "rim_price", "rim_worth"), ("tyres", "tyre_price", "tyre_worth")):
        prices = {int(match) for match in re.findall(r"return (\d+)\.0;", body(price_fn))}
        worths = {float(match) for match in re.findall(r"return (0\.\d+);", body(worth_fn))}
        assert prices == {option["price"] for option in categories[category]["options"]}, category
        expected = {option["cool_effect"]["target"] for option in categories[category]["options"]}
        # Plus the stock part's nothing, which is a state rather than an option.
        assert worths == expected | {0.0}, category


def test_both_replace_rather_than_accumulate():
    source = CONTROLLER.read_text(encoding="utf-8")
    assert 'Game.set("workshop.buy.cred", rim_worth(value) - rim_worth(this.rims));' in source
    assert 'Game.set("workshop.buy.cred", tyre_worth(value) - tyre_worth(this.tyres));' in source


def test_the_grid_covers_every_tyre_and_rim_pair():
    """Sixteen layers, each shown for exactly one pair."""
    source = CONTROLLER.read_text(encoding="utf-8")
    for tyre in range(1, 5):
        for rim in RIM_NAMES:
            assert f'World.find("Garage Car hjulkapsel-{tyre}-{rim}")' in source, f"{tyre}/{rim} is never found"
    shown = re.findall(
        r"World\.set_active\(this\.rim_(\d)_(\w+), this\.tyres == (\d)\.0 && this\.rims == (\d)\.0\);", source
    )
    assert len(shown) == 16, f"expected sixteen pairings, found {len(shown)}"
    for tyre, rim, tyre_state, rim_state in shown:
        assert int(tyre) == int(tyre_state) + 1, f"{tyre}/{rim} shows for the wrong tyre"
        assert RIM_NAMES.index(rim) == int(rim_state), f"{tyre}/{rim} shows for the wrong rim"
    assert len({(t, r) for t, r, _s, _u in shown}) == 16, "no pair is covered twice"


def test_the_tyre_layers_follow_the_tyre_alone():
    source = CONTROLLER.read_text(encoding="utf-8")
    shown = re.findall(r"World\.set_active\(this\.tyre_(\d), this\.tyres == (\d)\.0\);", source)
    assert [(int(a), int(b)) for a, b in shown] == [(1, 0), (2, 1), (3, 2), (4, 3)]


@pytest.mark.parametrize("category", ["rims", "tyres"])
def test_neither_sells_what_is_already_fitted(category, recovered):
    """The original's rule, not mine: character 140 covers every buy slot."""
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    data, header = parse_header(SWF.read_bytes())
    found = placements(iter_tags(data, header.tags_offset))
    inside = [p for p in found if p.parent == ROWS[category] and p.x is not None]
    buying = {round(p.x, 2) for p in inside if p.character in recovered}
    fitted = {round(p.x, 2) for p in inside if p.character == FITTED_GRAPHIC}
    assert buying and buying <= fitted, f"{category}: buy slots {sorted(buying)} vs fitted {sorted(fitted)}"

    source = CONTROLLER.read_text(encoding="utf-8")
    field = "rims" if category == "rims" else "tyres"
    assert re.search(rf"on_{field} && this\.{field} != \d\.0", source), f"{category} sells what is fitted"


def test_installer_and_reference_agree(categories):
    assert {(v, p, b) for v, p, b in RIMS_OPTIONS} == {
        (o["value"], o["price"], o["source_button"]) for o in categories["rims"]["options"]
    }
    assert {(v, p, b) for v, p, b in TYRES_OPTIONS} == {
        (o["value"], o["price"], o["source_button"]) for o in categories["tyres"]["options"]
    }


def test_one_till_serves_both_categories():
    """A single pending purchase, tagged with which category asked."""
    source = CONTROLLER.read_text(encoding="utf-8")
    assert source.count('Game.set("workshop.buy.ticket", this.ticket);') == 2
    assert "if this.pending_kind > 0.0 { return; }" in source
    assert "if this.pending_kind == 1.0 { this.rims = this.pending_value; }" in source
