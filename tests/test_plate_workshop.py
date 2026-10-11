from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
plate=(ROOT/"scripts/workshop_plate_controller.decay").read_text()
state=(ROOT/"scripts/workshop_state.decay").read_text()
installer=(ROOT/"tools/install_workshop_interactivity.py").read_text()
router=(ROOT/"scripts/workshop_category_controller.decay").read_text()

def test_plate_native_text_entry():
    assert '"sindri.ui.text_input"' in installer
    assert 'Ui.input_text(this.field)' in plate
    assert 'Ui.submitted(this.field)' in plate
    assert 'Ui.set_text(this.plate_display,value)' in plate
    assert 'Game.set("workshop.plate.text",value)' not in plate

def test_plate_original_economy():
    assert 'Game.set("workshop.buy.price",3000.0)' in plate
    assert 'value=="moused"' in plate
    assert 'this.street_cred = this.street_cred + 0.3' in state
    assert 'this.money = this.money + 20000.0' in state

def test_plate_click_owner():
    assert 'Ui.is_pressed(this.plate_buy)' in router
    assert 'Ui.is_pressed(this.edit)' not in plate
