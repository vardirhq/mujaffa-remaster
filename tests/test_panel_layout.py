"""The workshop panel's geometry, recomposed from the SWF.

A placement matrix carries a scale as well as an offset, and the panel is drawn
at 0.9388. An earlier pass read the speaker rows' 26.4 panel-local step as a
stage distance and shipped rows 6% too far apart; the test that was supposed to
guard it compared the wrong number to itself, so it passed.

These recompose each constant the installer uses by walking the same chain the
player's screen does, so a figure that is right in the wrong units fails here.
"""

import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

from swf_inventory import iter_tags, parse_header  # noqa: E402
from swf_layout import placements, resolve, spacing  # noqa: E402
from tools.install_workshop_interactivity import (  # noqa: E402
    AUDIO_ROW_Y, PANEL_SCALE, PANEL_X, PANEL_Y, SPOILER_BUTTON_X,
    audio_row_y, audio_slot_x, exhaust_point, rims_point, spoiler_point, tyres_point,
)

SWF = ROOT / "mujaffa_3juni_2003.swf"
WORKSHOP_PANEL = 924
SPEAKER_ROWS = [236, 243, 247, 257]
SPOILER_ROW = 393
SPOILER_BUTTONS = [391, 390, 385, 384]      # cheapest first, left to right
EXHAUST_ROW = 267
EXHAUST_BUTTONS = [259, 260, 261]
RIMS_ROW = 199
RIMS_BUTTONS = [194, 193, 192]      # cheapest first
TYRES_ROW = 156
TYRES_BUTTONS = [145, 144, 143]


@pytest.fixture(scope="module")
def found():
    if not SWF.is_file():
        pytest.skip("original SWF is not present in this checkout")
    data, header = parse_header(SWF.read_bytes())
    return placements(iter_tags(data, header.tags_offset))


def test_the_panel_is_scaled_and_the_installer_knows_it(found):
    """The whole reason panel-local offsets are not stage distances."""
    x, y, scale = resolve(found, [(None, WORKSHOP_PANEL)])
    assert (round(x, 2), round(y, 2)) == (PANEL_X, PANEL_Y)
    assert scale == pytest.approx(PANEL_SCALE, abs=1e-5)
    assert scale != 1.0, "if the panel were unscaled none of this would matter"


def test_speaker_rows_are_spaced_as_the_screen_shows_them(found):
    original = spacing(found, [(None, WORKSHOP_PANEL)], SPEAKER_ROWS)
    installed = [audio_row_y(index) for index in range(len(SPEAKER_ROWS))]
    ours = [round(later - earlier, 3) for earlier, later in zip(installed, installed[1:])]
    # A hundredth of a pixel: the installer rounds the panel scale, the file
    # does not. Anything larger is a real disagreement.
    assert ours == pytest.approx(original, abs=0.01), f"installed {ours}, original {original}"
    # The bug this replaces: the unscaled figures, which are ~6% larger.
    unscaled = [round(b - a, 3) for a, b in zip(AUDIO_ROW_Y, AUDIO_ROW_Y[1:])]
    assert ours != unscaled, "panel-local offsets are not stage distances"


def test_speaker_slots_sit_where_the_original_puts_them(found):
    for slot, character in ((0, 248), (1, 249), (2, 250)):     # the woofer buys in all three
        x, _y, _scale = resolve(found, [(None, WORKSHOP_PANEL), (WORKSHOP_PANEL, 257), (257, character)])
        assert audio_slot_x(slot) == pytest.approx(x, abs=0.05), f"slot {slot}"


def test_spoiler_buttons_sit_where_the_original_puts_them(found):
    for index, character in enumerate(SPOILER_BUTTONS):
        x, y, _scale = resolve(
            found, [(None, WORKSHOP_PANEL), (WORKSHOP_PANEL, SPOILER_ROW), (SPOILER_ROW, character)]
        )
        ours = spoiler_point(index)
        assert ours[0] == pytest.approx(x, abs=0.05), f"spoiler {index + 1} x"
        assert ours[1] == pytest.approx(y, abs=0.05), f"spoiler {index + 1} y"


def test_spoiler_row_is_ordered_cheapest_first(found):
    gaps = spacing(found, [(None, WORKSHOP_PANEL), (WORKSHOP_PANEL, SPOILER_ROW)], SPOILER_BUTTONS, axis="x")
    assert all(gap > 0 for gap in gaps)
    installed = [spoiler_point(index)[0] for index in range(len(SPOILER_BUTTONS))]
    assert installed == sorted(installed), "the cheapest wing is leftmost, as in the original"
    assert len(set(SPOILER_BUTTON_X)) == 4


def test_exhaust_buttons_sit_where_the_original_puts_them(found):
    """The row is unscaled, unlike the speaker rows, so its offsets add straight."""
    for index, character in enumerate(EXHAUST_BUTTONS):
        x, y, _scale = resolve(
            found, [(None, WORKSHOP_PANEL), (WORKSHOP_PANEL, EXHAUST_ROW), (EXHAUST_ROW, character)]
        )
        ours = exhaust_point(index)
        assert ours[0] == pytest.approx(x, abs=0.05), f"pipe {index + 1} x"
        assert ours[1] == pytest.approx(y, abs=0.05), f"pipe {index + 1} y"


# Every controller that owns panel controls, and where its numbers come from.
PLACED_BY_CONTROLLER = {
    "workshop_paint_controller": None,          # its own coordinates, older than this
    "workshop_audio_controller": "audio",
    "workshop_spoiler_controller": "spoiler",
    "workshop_exhaust_controller": "exhaust",
    "workshop_wheels_controller": "wheels",
}


def test_every_panel_controller_places_against_the_viewport():
    """The bug this guards: buttons authored once and never laid out again.

    The stage is square and a phone's viewport is not, so a control that trusts
    where the installer left it drifts off the stage entirely. It looks correct
    in CI, whose smoke canvas is 960x540 and therefore wider than tall, and
    wrong on the device -- so the check has to be on the source, not a render.
    """
    for name in PLACED_BY_CONTROLLER:
        source = (ROOT / "scripts" / f"{name}.decay").read_text(encoding="utf-8")
        assert "Viewport.aspect" in source, f"{name} never consults the viewport"
        assert "0.004 * min(Viewport.aspect, 1.0)" in source, f"{name} uses a different unit"
        assert "fn place(" in source, f"{name} has no placement helper"
        assert source.count("layout_controls()") >= 2, f"{name} must lay out on start and on update"


def test_controller_coordinates_match_the_installer():
    """Two copies of the same numbers -- the Decay script and the installer --
    so they are pinned to each other as well as to the SWF."""
    expected = {
        "spoiler": [(spoiler_point(index), (62.0, 26.0)) for index in range(4)],
        "exhaust": [(exhaust_point(index), (60.0, 26.0)) for index in range(3)],
    }
    for name, category in PLACED_BY_CONTROLLER.items():
        if category not in expected:
            continue        # wheels names its buttons per option, checked in its own file
        source = (ROOT / "scripts" / f"{name}.decay").read_text(encoding="utf-8")
        placed = re.findall(r"place\(this\.buy\d, ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+), unit\);", source)
        assert len(placed) == len(expected[category]), f"{name} places {len(placed)} controls"
        for (x, y, w, h), ((ex, ey), (ew, eh)) in zip(placed, expected[category]):
            assert float(x) == pytest.approx(ex, abs=0.01), f"{category} x"
            assert float(y) == pytest.approx(ey, abs=0.01), f"{category} y"
            assert (float(w), float(h)) == (ew, eh), f"{category} size"


def test_audio_controller_coordinates_match_the_installer():
    source = (ROOT / "scripts" / "workshop_audio_controller.decay").read_text(encoding="utf-8")

    def numbers(name):
        head = source.index(f"fn {name}(")
        return [float(value) for value in re.findall(r"return ([\d.]+);", source[head:source.index("\n    }", head)])]

    assert numbers("slot_x") == pytest.approx([audio_slot_x(slot) for slot in range(3)], abs=0.01)
    assert numbers("row_y") == pytest.approx([audio_row_y(row) for row in range(4)], abs=0.01)


@pytest.mark.parametrize(
    "row,buttons,point",
    [(RIMS_ROW, RIMS_BUTTONS, rims_point), (TYRES_ROW, TYRES_BUTTONS, tyres_point)],
    ids=["rims", "tyres"],
)
def test_wheel_buttons_sit_where_the_original_puts_them(found, row, buttons, point):
    for index, character in enumerate(buttons):
        x, y, _scale = resolve(found, [(None, WORKSHOP_PANEL), (WORKSHOP_PANEL, row), (row, character)])
        ours = point(index)
        assert ours[0] == pytest.approx(x, abs=0.05), f"{row} button {index} x"
        assert ours[1] == pytest.approx(y, abs=0.05), f"{row} button {index} y"


def test_everything_lands_inside_the_panel():
    """The remaster's panel is 153..496 by 351..462; the original's rows fit it."""
    points = [(audio_slot_x(slot), audio_row_y(row)) for slot in range(3) for row in range(4)]
    points += [spoiler_point(index) for index in range(4)]
    points += [exhaust_point(index) for index in range(3)]
    points += [rims_point(index) for index in range(3)]
    points += [tyres_point(index) for index in range(3)]
    for x, y in points:
        assert 153 <= x <= 496, f"x {x} escapes the panel"
        assert 351 <= y <= 462, f"y {y} escapes the panel"
