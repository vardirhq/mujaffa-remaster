"""The classic title screen's contract: entry point, navigation, evidence.

The artwork itself is generated from the SWF and not committed, so these tests
check the parts that are: the scene the generator produced, the controller that
drives it, and the agreement between the two.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCENE = json.loads((ROOT / "title.scene.json").read_text(encoding="utf-8"))
CONTROLLER = (ROOT / "scripts/title.decay").read_text(encoding="utf-8")
BY_NAME = {entity["name"]: entity for entity in SCENE["entities"]}


def test_title_is_the_project_entry_scene():
    manifest = (ROOT / "sindri.toml").read_text(encoding="utf-8")
    assert 'main_scene = "title.scene.json"' in manifest
    assert 'scenes = ["main.scene.json"]' in manifest


def test_title_scene_owns_navigation_into_gameplay():
    assert "Title Start" in BY_NAME
    assert "sindri.ui.button" in BY_NAME["Title Start"]["components"]
    controller = BY_NAME["Title Controller"]["components"]["sindri.script"]
    assert controller["source"] == "scripts/title.decay"
    assert controller["script"] == "Title"
    assert 'Scene.go("main.scene.json")' in CONTROLLER


def test_every_recovered_control_is_drawn_in_three_original_states():
    for control in (
        "Title Start",
        "Title Instructions",
        "Instructions Next",
        "Instructions Previous",
        "Instructions Start",
    ):
        assert "sindri.ui.button" in BY_NAME[control]["components"], control
        for state in ("Up", "Over", "Down"):
            sprite = BY_NAME[f"{control} {state}"]["components"]["sindri.sprite"]
            assert sprite["texture"].startswith("assets/generated/title/png/"), control


def test_the_opening_is_animated_rather_than_a_still():
    """The original's mouth, arm and prompt move; a frozen title is a regression."""
    for name in ("Title Mujaffa Arm", "Title Mujaffa Mouth", "Title Prompt"):
        animation = BY_NAME[name]["components"]["sindri.animation.sprite"]
        clip = animation["clips"][animation["playing"]]
        assert len(clip["frames"]) > 1, name
        assert clip["seconds_per_frame"] == round(1.0 / 12.0, 6), name
        assert len(set(clip["frames"])) > 1, name
    # The welcome plays once and settles; the prompt never stops flashing.
    arm = BY_NAME["Title Mujaffa Arm"]["components"]["sindri.animation.sprite"]
    assert arm["clips"]["play"]["looping"] is False
    prompt = BY_NAME["Title Prompt"]["components"]["sindri.animation.sprite"]
    assert prompt["clips"]["play"]["looping"] is True


def test_the_five_original_instruction_pages_are_present():
    for page in range(1, 6):
        entity = BY_NAME[f"Instructions Page {page}"]
        assert entity["disabled"] is True, page
        assert entity["components"]["sindri.sprite"]["texture"].endswith(
            f"instructions-{page}-backdrop.png"
        )
    assert "Title Backdrop" in BY_NAME
    assert "disabled" not in BY_NAME["Title Backdrop"]


def test_controller_hit_areas_match_the_scene_the_generator_installed():
    """The script re-places the hit areas each frame; the scene bakes them once.

    They are two statements of the same original stage rects, so they have to
    agree -- otherwise a control is clickable somewhere other than where the
    original's button is drawn.
    """
    placed = {
        match[0]: tuple(float(value) for value in match[1:])
        for match in re.findall(
            r"place\(this\.(\w+), ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+), unit\);",
            CONTROLLER,
        )
    }
    assert set(placed) == {"begin", "guide", "next", "previous", "play"}
    names = {
        "begin": "Title Start",
        "guide": "Title Instructions",
        "next": "Instructions Next",
        "previous": "Instructions Previous",
        "play": "Instructions Start",
    }
    for field, (x, y, width, height) in placed.items():
        transform = BY_NAME[names[field]]["transform_3d"]
        unit = 2.0 / 500.0
        assert transform["position"][0] == round((x + width / 2 - 250.0) * unit, 6), field
        assert transform["position"][1] == round((250.0 - (y + height / 2)) * unit, 6), field
        assert transform["scale"][0] == round(width * unit, 6), field
        assert transform["scale"][1] == round(height * unit, 6), field


def test_title_owns_no_workshop_economy_state():
    text = (ROOT / "title.scene.json").read_text(encoding="utf-8")
    for leak in ("workshop", "penge", "street_cred", "original-workshop-data"):
        assert leak not in text.lower()
