from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
INSTALL = (ROOT / "tools/install_workshop_interactivity.py").read_text()

def test_horn_camera_wiring():
    for name in ("horn", "camera"):
        source = (ROOT / f"scripts/workshop_{name}_controller.decay").read_text()
        assert f"workshop-{name}-controller" in INSTALL
        assert f"scripts/workshop_{name}_controller.decay" in INSTALL
        assert 'Game.get("workshop.buy.ticket",0.0)+1.0' in source

def test_original_prices():
    horn = (ROOT / "scripts/workshop_horn_controller.decay").read_text()
    camera = (ROOT / "scripts/workshop_camera_controller.decay").read_text()
    assert "900.0" in horn and "1700.0" in horn
    assert "6000.0" in camera and "0.7" in camera
