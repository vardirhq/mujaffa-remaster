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
    # Sprite layers only: the UI canvas (dialogs, hit areas) is drawn apart.
    sprite_lines = [line for line in INSTALLER.splitlines() if "sindri.ui" not in line]
    layers = [int(n) for line in sprite_lines for n in re.findall(r'"layer": (\d+)', line)]
    layers += [int(n) for n in re.findall(r', (\d+), "(?:trip|drive)', INSTALLER)]
    assert MATTE_LAYER > max(n for n in layers if n != MATTE_LAYER)


def test_scripted_tints_are_authored_as_floats():
    # A Decay write keeps the authored number's type: an integer tint of 1
    # rounds every paint write to 0 or 1, so a 00349C car drove pure blue.
    assert '"tint": [1, 1, 1, 1]' not in INSTALLER
    assert '"tint": [1.0, 1.0, 1.0, 1.0]' in INSTALLER


def test_the_drive_spoiler_takes_the_paint():
    # Frame 794: `h = new Color(_root.bil.heks.hf); h.setRGB(colorHEX)`.
    assert 'car-heksfarve-' in INSTALLER
    assert 'one_of("Drive Car heksfarve ", 5.0' in DRIVE
    assert "wing.sprite.tint.r = this.car_body.sprite.tint.r" in DRIVE


def test_paint_bytes_are_converted_to_linear_light():
    paint = (ROOT / "scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
    for script in (paint, DRIVE):
        assert "fn to_linear(byte: f32) -> f32" in script
    assert "/ 255.0;" not in DRIVE[DRIVE.index("Frame 794"):DRIVE.index("dress_car();", DRIVE.index("Frame 794"))]


def test_the_broke_dialog_answers_every_refusal():
    state = (ROOT / "scripts/workshop_state.decay").read_text(encoding="utf-8")
    assert 'Game.set("workshop.buy.refused"' in state
    assert 'Game.get("workshop.buy.refused", 0.0)' in TRIP
    assert "BROKE_BUTTONS = {\"ok\": 281, \"lukk\": 285}" in INSTALLER


def test_live_text_is_bold_arial_metric_like_the_original():
    # Every edit text in the SWF is embedded Arial Bold (font 2). Liberation
    # Sans Bold has Arial's metrics under the OFL; `bold` asks for the face's
    # bold, without which a system regular of the same family can win.
    for tool in ("install_drive.py", "install_showroom.py", "install_workshop_interactivity.py"):
        source = (ROOT / "tools" / tool).read_text(encoding="utf-8")
        assert "ChakraPetch" not in source
        assert "LiberationSans-Bold.ttf" in source
        assert re.search(r'"bold":\s*True', source)
    assert (ROOT / "fonts/LiberationSans-Bold.ttf").is_file()
    assert "SIL Open Font License" in (ROOT / "fonts/OFL-LiberationSans.txt").read_text(encoding="utf-8")


def test_hud_bmw_reads_like_flash_and_end_screens_are_on_white():
    source = (ROOT / "tools/install_drive.py").read_text(encoding="utf-8")
    # Flash prints bil_cool 1 as "1" and 1.15 as "1.15": `{}` does the same.
    assert '"{.1}"' not in source
    assert 'name in ("BMW", "Cred", "Penger", "Level")' in source
    assert 'stage_layer("trip-over-paper", "Game Over Paper", PAPER, 0, "trip-over")' in source
    assert 'stage_layer("trip-status-paper", "Status Paper", PAPER, 0, "trip-status")' in source


def test_repair_and_respect_ask_like_repair_car():
    from install_drive import REPAIR, REPAIR_BUTTONS, REPAIR_FRAMES
    assert REPAIR == 886 and REPAIR_FRAMES == {"repair": 7, "respect": 14}
    assert REPAIR_BUTTONS["repair-ja"] == (7, 877) and REPAIR_BUTTONS["repair-nei"] == (7, 878)
    assert REPAIR_BUTTONS["respect-ja"] == (14, 883)
    # Nothing is settled without an answer any more.
    garage = TRIP[TRIP.index("fn back_in_garage()"):TRIP.index("fn pay_repair()")]
    assert "game.cool" not in garage and "trip.spent" not in garage
    assert "this.bill = energi * 20.0;" in garage
    answer = TRIP[TRIP.index("fn answer_repair()"):TRIP.index("fn digit_name(")]
    assert "if Ui.is_pressed(this.repair_ja) { pay_repair(); this.repair_due = false; }" in answer
    assert "if Ui.is_pressed(this.repair_nei) { this.repair_due = false; }" in answer
    assert 'Game.get("game.cool", 0.0) + 15.0' in answer
    # The respect cross leaves `repairok` set, so it asks again.
    assert "if Ui.is_pressed(this.respect_lukk) { World.set_active(this.respect, false); }" in answer
    # The bill's digit pictures follow field 882 and Arial Bold's digit advance.
    assert "291.4 + (slot - 1.0) * 11.133, 202.35, 15.133, 30.0" in TRIP


def test_bhaias_verksted_plays_after_start_and_every_drive():
    from install_drive import ARRIVAL, ARRIVAL_CAR, GARAGE_CAR
    assert (ARRIVAL[0], ARRIVAL[-1], ARRIVAL_CAR, GARAGE_CAR) == (755, 793, 946, 875)
    # START, a finished drive and both level-complete pages arrive; none of
    # them opens the workshop directly any more.
    assert TRIP.count("arrive();") == 4
    assert "show(0.0);\n                    back_in_garage();" not in TRIP
    assert 'if Sequence.is_finished(this.arrival) { arrived(); }' in TRIP
    # The garage leaves the car to the sequence while it plays.
    showroom = (ROOT / "tools/install_showroom.py").read_text(encoding="utf-8")
    assert "World.set_active(car, view <= 2.0 || view == 7.0);" in showroom
    assert '"target": "/Parity Car"' in INSTALLER


def test_ja_plays_the_drive_away_before_the_map():
    from install_drive import LEAVE, SHADOW
    assert (LEAVE[0], LEAVE[-1]) == (2, 50)
    assert "if Ui.is_pressed(this.cruise_ja) { drive_off(); }" in TRIP
    assert "if Sequence.is_finished(this.leave) { driven_off(); }" in TRIP
    assert '"target": f"/Parity Car/{SHADOW}"' in INSTALLER
    showroom = (ROOT / "tools/install_showroom.py").read_text(encoding="utf-8")
    assert 'if Game.get("trip.car_driven", 0.0) > 0.0 {{ return; }}' in showroom
