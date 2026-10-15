"""The frame-730 showroom: placements from the SWF and frame 745's description."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from install_showroom import GARAGE_LAYOUT_FIXED, GARAGE_LAYOUT_VIEWS, PX, SHOWROOM_CAR, WORKSHOP_CAR  # noqa: E402

CONTROLLER = (ROOT / "scripts/showroom_controller.decay").read_text(encoding="utf-8")
INSTALLER = (ROOT / "tools/install_showroom.py").read_text(encoding="utf-8")

# Every description string from frame 745's constant pool, quirks included:
# no comma after the white stripe, two spaces before the medium spoiler, and
# the racer/krom rim labels the other way round from their names.
FRAME_745 = [
    "Spesiallakert BMW 320i med ",
    " lysegrønn fartsstripe,", " rosa fartsstripe,", " hvit fartsstripe", " sort fartsstripe,",
    " liten sporty spoiler,", "  medium-sized fet spoiler,", " stor megarå spoiler,", " den villeste kongespoilern,",
    " kjedelig enkeltløps eksosanlegg,", " frekt dobbeltløps eksosanlegg,", " firedobbelt power-eksosanlegg,",
    " spesialdesignet og forlenget 8-rørs ekso-sanlegg,",
    " standard felger,", " hippe forkrommede felger,", " hippe sportsfelger,", " gullbelagte gangster-boss felger,",
    " standardhorn,", " stort kompressorhorn,", " irriterende Wild Turkey flertonehorn,",
    " standard dekk", " brede contact-plus dekk", " ekstra brede ultra-grip dekk", " superbrede power-cruiser dekk",
    " vanlige bilruter,", " graderte fargede taxiruter,", " tonede wanna-be mafia-ruter,", " superfete speilrefleksruter,",
    " polyester på setene", " kunstig tigerplysj på setene", " skai av beste kvalitet på setene", " pornosmart sebraskinn på setene",
    " og elektrisk soltak.", ", elektrisk soltak og",
    " blinkende neonhjerte i frontruten.", " en velduftende wunderbaum i frontruten.",
    " tidløse og trendy polyester-terninger i frontruten.", " en stilfull, forgyldt minimodell av Taj Mahal i frontruta.",
    "\\n\\nAnlegg: ",
    "små 45 watts høytalere i front", "brakende 140 watts høytalere i front", "øredøvende 350 watts boomers i front",
    "20 watts høytalere i sidedørene", "rungende 60 watts høytalere i sidedørene", "superbass 220 watts sidedørs-boomers",
    "ynkelige 45 watts bakhøytalere", "solide 140 watts bakhøytalere",
    "gigantiske 350 watts bakhøytalere som sperrer utsynet totalt",
    "ingen subwoofer (taper)", "en 200 watts bakhyler av en subwoofer",
    "en 400 watts woofer som kan rykke bilen i stykker", "800 watts psycho-stor woofer som fyller hele bagasjerommet",
]


def test_description_keeps_every_frame_745_string():
    for text in FRAME_745:
        assert f'"{text}"' in CONTROLLER, text


def test_rim_labels_stay_swapped_like_the_original():
    # workshop.rims 1 is `racer` and 2 is `krom`; frame 745 calls racer chrome.
    assert 'if rims == 1.0 { return " hippe forkrommede felger,"; }' in CONTROLLER
    assert 'if rims == 2.0 { return " hippe sportsfelger,"; }' in CONTROLLER


def test_forude_typo_always_appends_comma():
    assert 'text = text + ", ";' in CONTROLLER


def test_showroom_car_is_the_frame_730_placement():
    assert WORKSHOP_CAR == (329.65, 193.9)
    assert SHOWROOM_CAR == (259.4, 180.95)
    dx = (SHOWROOM_CAR[0] - WORKSHOP_CAR[0]) * PX
    dy = (WORKSHOP_CAR[1] - SHOWROOM_CAR[1]) * PX
    assert f"{dx:.4f}" in GARAGE_LAYOUT_VIEWS and f"{dy:.4f}" in GARAGE_LAYOUT_VIEWS
    assert 'Game.get("workshop.view", 0.0)' in GARAGE_LAYOUT_VIEWS
    assert "view == 1.0" in GARAGE_LAYOUT_VIEWS


def test_garage_hook_matches_the_workshop_parity_patch():
    parity = (ROOT / "tools/install_workshop_parity.py").read_text(encoding="utf-8")
    for line in GARAGE_LAYOUT_FIXED.splitlines()[1:-1]:
        assert line.strip() in parity, line


def test_header_numbers_are_live_text_not_pixels():
    for tool in ("refine_workshop_chrome.py", "install_workshop_parity.py"):
        source = (ROOT / "tools" / tool).read_text(encoding="utf-8")
        assert ">5000</text>" not in source
    for key in ("workshop.money", "workshop.street_cred", "game.cool"):
        assert f'"{key}"' in CONTROLLER
    assert 'Game.set("game.cool", this.cool);' in (ROOT / "scripts/game_state.decay").read_text(encoding="utf-8")


def test_controller_finds_what_the_installer_names():
    for name in (
        "Workshop View", "Showroom View", "Showroom Description", "Header Penger",
        "Header BMW", "Header Street Cred", "Nav Verksted", "Nav Showroom", "Nav Kjor",
    ):
        assert f'World.find("{name}")' in CONTROLLER
        assert f'"{name}"' in INSTALLER
    assert 'World.find("Original Mujaffa Logo")' in CONTROLLER

