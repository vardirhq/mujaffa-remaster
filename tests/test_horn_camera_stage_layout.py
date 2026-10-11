from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ROUTER=(ROOT/"scripts/workshop_category_controller.decay").read_text()
INSTALL=(ROOT/"tools/install_workshop_interactivity.py").read_text()

def test_horn_camera_share_category_layout_pass():
    assert "layout_controls(); layout_new_purchases();" in ROUTER
    for name in ("Workshop Horn 1","Workshop Horn 2","Workshop Camera 1"):
        assert f'World.find("{name}")' in ROUTER
        assert f'"{name}"' in INSTALL

def test_purchases_use_square_stage_aspect_scale():
    assert "let unit=0.004*min(Viewport.aspect,1.0);" in ROUTER
    assert "this.horn_buy1.transform.position.y=(250.0-418.0)*unit;" in ROUTER
    assert "this.horn_buy2.transform.position.y=(250.0-418.0)*unit;" in ROUTER
    assert "this.camera_buy1.transform.position.y=(250.0-418.0)*unit;" in ROUTER
