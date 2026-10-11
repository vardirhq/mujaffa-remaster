from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
router=(ROOT/"scripts/workshop_category_controller.decay").read_text()
horn=(ROOT/"scripts/workshop_horn_controller.decay").read_text()
camera=(ROOT/"scripts/workshop_camera_controller.decay").read_text()

def test_visible_button_owner_dispatches_clicks():
    assert 'Ui.is_pressed(this.horn_buy1)' in router
    assert 'Ui.is_pressed(this.horn_buy2)' in router
    assert 'Ui.is_pressed(this.camera_buy1)' in router
    assert 'Game.set("workshop.horn.request",1.0)' in router
    assert 'Game.set("workshop.camera.request",1.0)' in router

def test_purchase_controllers_consume_requests():
    assert 'Game.get("workshop.horn.request",0.0)' in horn
    assert 'Game.get("workshop.camera.request",0.0)' in camera
    assert 'Game.set("workshop.horn.request",0.0)' in horn
    assert 'Game.set("workshop.camera.request",0.0)' in camera
    assert 'Ui.is_pressed(' not in horn
    assert 'Ui.is_pressed(' not in camera
