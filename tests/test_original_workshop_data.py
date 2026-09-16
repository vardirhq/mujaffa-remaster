import json
from pathlib import Path

DATA = Path(__file__).parents[1] / "reference" / "original-workshop-data.json"


def load():
    return json.loads(DATA.read_text(encoding="utf-8"))


def test_reference_has_all_original_categories_in_order():
    data = load()
    assert [category["label"] for category in data["categories"]] == [
        "LAKKERING",
        "BILSTEREO",
        "SPOILER",
        "EKSOSANLEGG",
        "FELGER",
        "DEKK",
        "RUTER",
        "SOLTAK",
        "NUMMERSKILT",
        "SETETREKK",
        "BILNIPS",
        "BÅT-HORN",
        "BMW CAM",
    ]


def test_reference_preserves_original_starting_economy_and_paint():
    state = load()["initial_state"]
    assert state["money"] == 5000
    assert state["bil_cool"] == 1.0
    assert state["paint_rgb"] == [0, 52, 156]
    assert state["paint_hex"] == "00349C"


def test_reference_keeps_known_original_quirks():
    data = load()
    categories = {category["id"]: category for category in data["categories"]}
    assert categories["plate"]["options"][0]["special_case"] == {
        "input": "moused",
        "money_delta_on_confirm": 20000,
    }
    assert categories["horn"]["notes"].startswith("The initializer uses horn_cool_")
    assert categories["camera"]["options"][0]["cool_effect"]["delta"] == 0.7
