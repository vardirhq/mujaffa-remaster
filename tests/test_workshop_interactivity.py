from pathlib import Path
from tools.workshop_catalog import CATEGORIES

def test_interactivity_foundation():
    ids=[f"workshop-category-{e['id']}" for e in CATEGORIES]; assert len(ids)==len(set(ids))==13; assert all('price' not in e for e in CATEGORIES)
def test_category_controls_render_their_own_art():
    s=Path('tools/install_workshop_interactivity.py').read_text(); assert '"sindri.ui.image"' in s; assert '"sindri.ui.button"' in s; assert "category-{entry['id']}.png" in s
def test_baked_chrome_does_not_duplicate_category_buttons():
    chrome=Path('tools/refine_workshop_chrome.py').read_text(); assert 'Category controls are separate real UI entities' in chrome
    for e in CATEGORIES: assert e['label'] not in chrome
def test_category_layout_tracks_square_stage_on_portrait_viewports():
    c=Path('scripts/workshop_category_controller.decay').read_text(); assert 'min(Viewport.aspect,1.0)' in c or 'min(Viewport.aspect, 1.0)' in c; assert '145.0*unit' in c or '145.0 * unit' in c
def test_paint_uses_original_rgb_mixer_model():
    installer=Path('tools/install_workshop_interactivity.py').read_text(); controller=Path('scripts/workshop_paint_controller.decay').read_text()
    for asset in ('rgb-mixer.png','rgb-red.png','rgb-green.png','rgb-blue.png','rgb-ok.png'): assert asset in installer
    assert 'paint_index' not in controller; assert 'next_paint' not in controller
    assert 'workshop.paint.red' in controller and 'workshop.paint.green' in controller and 'workshop.paint.blue' in controller
    assert 'this.red / 255.0' in controller and 'this.green / 255.0' in controller and 'this.blue / 255.0' in controller
    assert 'Ui.is_pressed(this.change_paint)' in controller and 'set_mixer(true)' in controller and 'Ui.is_pressed(this.ok)' in controller
def test_paint_rgb_tracks_are_native_vertical_sliders():
    installer=Path('tools/install_workshop_interactivity.py').read_text(); controller=Path('scripts/workshop_paint_controller.decay').read_text()
    assert '"sindri.ui.slider"' in installer and '"orientation":"vertical"' in installer
    assert '"min":0.0' in installer and '"max":255.0' in installer and '"step":1.0' in installer
    assert 'Ui.slider_value(this.red_track)' in controller and 'Ui.slider_value(this.green_track)' in controller and 'Ui.slider_value(this.blue_track)' in controller
    assert 'Ui.set_slider_value(this.red_track, this.red)' in controller
    assert 'cycle_red' not in controller and 'cycle_green' not in controller and 'cycle_blue' not in controller
def test_stripes_remain_on_normal_lakkering_panel():
    c=Path('scripts/workshop_paint_controller.decay').read_text(); assert 'World.set_active(this.stripe_none, !value)' in c; assert 'Garage Car farvestribe-hvid' in c; assert 'Garage Car farvestribe-pink' in c
def test_rgb_controls_are_scoped_to_lakkering():
    r=Path('scripts/workshop_category_controller.decay').read_text(); assert 'Workshop RGB Mixer' in r; assert 'World.set_active(this.mixer,false)' in r or 'World.set_active(this.mixer, false)' in r
