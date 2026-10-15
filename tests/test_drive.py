"""KJØR!: the route the map walks, and the numbers the drive keeps from v1.6."""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from install_drive import LEVEL_COMPLETE, ROUTE, STATUS  # noqa: E402

TRIP = (ROOT / "scripts/trip_controller.decay").read_text(encoding="utf-8")
DRIVE = (ROOT / "scripts/drive_controller.decay").read_text(encoding="utf-8")
SHOWROOM = (ROOT / "scripts/showroom_controller.decay").read_text(encoding="utf-8")
INSTALLER = (ROOT / "tools/install_drive.py").read_text(encoding="utf-8")

CODES = {"GRØNLAND": 1, "GRUNERLØKKA": 2, "SINSEN": 3, "TVEITA": 4,
         "RÅDHUSPLASSEN": 5, "BISLETT": 6, "FROGNER": 7, "HOLMENKOLLEN": 8}


def walk(start):
    frame, districts = start, []
    while frame in ROUTE:
        _, frame, district, _ = ROUTE[frame]
        districts.append(district)
    return frame, districts


def script_function(name):
    match = re.search(rf"fn {name}\(frame: f32\) -> f32 \{{(.*?)\n    \}}", TRIP, re.S)
    assert match, name
    return match.group(1)


def test_each_level_drives_its_route_to_the_level_complete_map():
    assert walk(368) == (483, ["GRØNLAND", "GRUNERLØKKA", "SINSEN", "TVEITA"])
    assert walk(404) == (492, ["GRØNLAND", "RÅDHUSPLASSEN", "BISLETT", "SINSEN", "TVEITA"])
    # With the three FIXED rows; v1.6 never gets past Frogner.
    assert walk(443) == (502, ["GRØNLAND", "RÅDHUSPLASSEN", "FROGNER", "HOLMENKOLLEN", "SINSEN", "TVEITA"])
    assert set(LEVEL_COMPLETE) == {483, 492, 502}


def test_trip_controller_matches_the_route_table():
    nexts = dict(re.findall(r"if frame == (\d+)\.0 \{ return (\d+)\.0; \}", script_function("next_state")))
    for frame, (_, following, _, _) in ROUTE.items():
        assert int(nexts.get(str(frame), 502)) == following, frame

    body = script_function("open_district")
    for frame, (_, _, district, _) in ROUTE.items():
        line = next((l for l in body.splitlines() if f"frame == {frame}.0" in l), None)
        code = int(re.search(r"return (\d)\.0", line).group(1)) if line else 4
        assert code == CODES[district], frame


def test_the_garage_follows_levels_one_and_two():
    # 640 and 643: `goto_label = "bane2_start"` / `"bane3_start"`, via the garage.
    assert "this.state == 483.0" in TRIP and "this.state = 404.0;" in TRIP
    assert "this.state == 492.0" in TRIP and "this.state = 443.0;" in TRIP


def test_status_tiers_are_frame_529():
    assert list(STATUS) == [1, 2, 3, 4, 5]
    for limit in ("2500.0", "1200.0", "600.0", "200.0"):
        assert f"if cool < {limit}" in TRIP
    assert "Du fikk {} street cred points." in INSTALLER


def test_drive_keeps_the_v16_numbers():
    for line in (
        "this.speed = 22.0;",
        "if this.level == 2.0 { this.speed = 24.0; }",
        "if this.level == 3.0 { this.speed = 26.0; }",
        "if this.energi + amount > 80.0 { crash(); }",
        "let amount = 30.0;",
    ):
        assert line in DRIVE, line


def test_kept_quirks_stay_kept():
    # Bislett finds no BISLET label and drives among the Grünerløkka cars.
    assert 'if code == 6.0 { return "GRUNERLØKKA"; }' in DRIVE
    # Grünerløkka's cars dent the BMW without ever ending the game.
    assert 'if this.traffic_set == "GRUNERLØKKA" {\n            this.energi = this.energi + amount;' in DRIVE


def test_sheets_use_the_engines_suffix():
    # sindri-core slices `x.png` with `x.sheet`; a `.sheet.json` is never read
    # and the whole atlas is drawn instead.
    for tool in ("install_drive.py", "swf_title_extract.py"):
        source = (ROOT / "tools" / tool).read_text(encoding="utf-8")
        assert ".sheet.json" not in source, tool
        assert '{name}.sheet"' in source, tool


def test_views_agree_between_controllers():
    assert 'Game.set("workshop.view", value);' in TRIP
    assert 'Game.set("workshop.view", value);' in SHOWROOM
    assert "if this.view == 0.0 && Ui.is_pressed(this.nav_kjor) { set_view(2.0); }" in SHOWROOM



def test_touch_drives_through_the_keyboard_rules():
    # A finger presses the same arrow steps the keys do, so it cannot out-steer them.
    assert "if right {" in DRIVE and "if left {" in DRIVE and "if up {" in DRIVE and "if down {" in DRIVE
    assert "if steering() {" in DRIVE
    assert "clamp(this.touch_y - 70.0, 60.0, 440.0)" in DRIVE
    # Taps land on the same checks as Z, X and B.
    assert 'let greet = Input.just_pressed("Z") || this.want_greet;' in DRIVE
    assert 'let pick = Input.just_pressed("X") || this.want_pick;' in DRIVE
    assert 'let burn = Input.just_pressed("B") || this.want_burn;' in DRIVE


def test_small_buttons_grow_for_thumbs():
    assert "entity.transform.scale.x = max(width, 36.0) * unit;" in TRIP
    assert "entity.transform.scale.y = 32.0 * unit;" in SHOWROOM


def test_mattes_cover_everything_outside_the_stage():
    # Flash never drew outside the 500x500 movie; on a phone the road and the
    # actors parked off-stage would otherwise show above and below it.
    from install_drive import MATTE_LAYER

    for side in ('"top": (0.0, 10.0)', '"bottom": (0.0, -10.0)', '"left": (-10.0, 0.0)', '"right": (10.0, 0.0)'):
        assert side in INSTALLER
    layers = [int(n) for n in re.findall(r'"layer": (\d+)', INSTALLER)] + [int(n) for n in re.findall(r', (\d+), "(?:trip|drive)', INSTALLER)]
    assert MATTE_LAYER > max(n for n in layers if n != MATTE_LAYER)
