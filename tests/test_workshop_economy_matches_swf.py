"""The committed economy has to agree with the SWF it claims to come from.

`reference/original-workshop-data.json` arrived as a transcription: the job that
produced it was deleted in the same change, so nothing could regenerate it and
`test_original_workshop_data.py` only reads the file back to itself. Every price
in it could have been wrong without a test noticing.

These read the original SWF instead and compare. The parity spec refuses to
invent prices and cool deltas; this is what turns that refusal into something
CI can check.
"""

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from swf_workshop_economy import purchases  # noqa: E402  (needs the path above)

SWF = ROOT / "mujaffa_3juni_2003.swf"
DATA = ROOT / "reference" / "original-workshop-data.json"

# The SWF names parts in Danish; the reference file groups them by category.
# A group carries its own `state`, so most of the mapping comes from the data
# itself -- this only covers the categories that name their state elsewhere.
CATEGORY_STATE = {
    "paint": "farve",
    "spoiler": "spoiler",
    "exhaust": "udstodning",
    "rims": "hjulkapsel",
    "tyres": "daek",
    "windows": "vinduer",
    "sunroof": "soltag",
    "plate": "nummerplade1",
    "interior": "indtraek",
    "horn": "horn",
    "camera": "cam",
}


@pytest.fixture(scope="module")
def recovered():
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    return purchases(SWF.read_bytes())


@pytest.fixture(scope="module")
def reference():
    return json.loads(DATA.read_text(encoding="utf-8"))


def options(category):
    if "options" in category:
        yield from category["options"]
    for group in category.get("option_groups", []):
        yield from group.get("options", [])


def test_every_cited_button_charges_the_price_the_reference_claims(recovered, reference):
    """The strongest check available: the button id and its price, together.

    A transcription that drifted would keep plausible prices but lose the pairing.
    """
    charged = {(p.character, p.price) for p in recovered}
    unconfirmed = [
        (category["id"], option.get("id") or option.get("value"), option["source_button"], option["price"])
        for category in reference["categories"]
        for option in options(category)
        if option.get("source_button") is not None and option.get("price") is not None
        and (option["source_button"], option["price"]) not in charged
    ]
    assert not unconfirmed, f"buttons that do not charge the claimed price: {unconfirmed}"


def test_prices_per_category_match_the_swf(recovered, reference):
    by_state = {}
    for purchase in recovered:
        by_state.setdefault(purchase.state_variable or "farve", Counter())[purchase.price] += 1

    for category in reference["categories"]:
        states = {
            group["state"]
            for group in category.get("option_groups", [])
            if group.get("state")
        }
        if not states:
            state = CATEGORY_STATE.get(category["id"])
            if state is None:
                continue
            states = {state}
        claimed = Counter(
            option["price"] for option in options(category) if option.get("price") is not None
        )
        # The SWF repeats a button when the same upgrade appears on more than one
        # panel, so compare the distinct prices a category can charge.
        actual = Counter()
        for state in states:
            actual.update(set(by_state.get(state, {})))
        assert set(claimed) == set(actual), (
            f"{category['id']}: reference charges {sorted(claimed)}, SWF charges {sorted(actual)}"
        )


def test_price_checks_are_the_strict_test_the_original_used(recovered, reference):
    """Every purchase gates on `penge > price - 1`, which is why 500 needs 500."""
    thresholds = {(p.character, p.threshold) for p in recovered}
    for category in reference["categories"]:
        for option in options(category):
            check, button = option.get("price_check"), option.get("source_button")
            if not check or button is None:
                continue
            claimed = int(check.split(">")[1].strip())
            assert (button, claimed) in thresholds, (
                f"{category['id']}/{option.get('id') or option.get('value')}: "
                f"reference claims {check}, SWF button {button} does not test that"
            )
            assert claimed == option["price"] - 1, "the original tests one below the price"


def test_cool_targets_match_the_swf(recovered, reference):
    targets = {(p.character, p.cool[1]) for p in recovered if p.cool}
    checked = 0
    for category in reference["categories"]:
        for option in options(category):
            effect, button = option.get("cool_effect"), option.get("source_button")
            if not effect or button is None or "target" not in effect:
                continue
            if button not in {p.character for p in recovered if p.cool}:
                continue            # this button's coolness is computed some other way
            checked += 1
            assert (button, float(effect["target"])) in targets, (
                f"{category['id']}/{option.get('id') or option.get('value')}: "
                f"reference claims cool {effect['target']}, SWF button {button} sets something else"
            )
    assert checked >= 20, "expected the recoverable cool targets to be worth checking"


def test_starting_money_and_paint_come_from_the_initialiser(reference):
    """`initial_state` is set on the main timeline, not in a button."""
    from swf_actions import action_records
    from swf_inventory import iter_tags, parse_header
    from swf_script_sites import action_sites
    from swf_variables import push_values

    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    from swf_workshop_economy import _constant_pool

    data, header = parse_header(SWF.read_bytes())
    literals = set()
    for site in action_sites(iter_tags(data, header.tags_offset), header.version):
        try:
            records = action_records(site.payload)
        except Exception:
            continue
        pool = []
        for code, body, _ in records:
            if code == 0x88:
                pool = _constant_pool(body)
                literals.update(pool)
            elif code == 0x96:
                try:
                    literals.update(
                        value for value in push_values(body, pool)
                        if isinstance(value, (int, float, str))
                    )
                except Exception:
                    pass

    state = reference["initial_state"]
    assert state["money"] in literals
    assert state["paint_hex"] in literals
    for channel in state["paint_rgb"]:
        assert channel in literals
