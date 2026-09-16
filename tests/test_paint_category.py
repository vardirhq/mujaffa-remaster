from pathlib import Path


def test_paint_slice_has_dedicated_controller():
    source = Path("scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert "script WorkshopPaintController" in source
    # LAKKERING is the original's two-step flow: `skift` opens the native RGB
    # mixer and OK commits it. The older single-step `next_paint()` cycle it
    # replaced is gone, which is what this used to assert.
    assert "set_mixer(true);" in source
    assert "set_mixer(false);" in source
    assert "Ui.slider_value(" in source
    assert source.count("set_stripe(") >= 6


def test_paint_reaches_the_body_through_the_colour_transform():
    source = Path("scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
    # `paint-tintable` is a flat RGB(49,49,49) silhouette mask, so multiplying
    # by a tint caps every paint job at 49/255 — a fifth of the colour asked
    # for, which is why the car used to come out nearly black whatever the
    # sliders said. The transform is what makes the slider value land: a zero
    # multiply drops the mask's grey and the offset supplies the colour whole.
    assert "color_multiply.r = 0.0" in source
    assert "color_offset.r = this.red / 255.0" in source
    assert "color_offset.g = this.green / 255.0" in source
    assert "color_offset.b = this.blue / 255.0" in source
    # The alpha channels stay at the identity. The mask's alpha is the car's
    # silhouette, and an offset there would fill its transparent corners with
    # a visible rectangle.
    assert "color_offset.a" not in source
    assert "color_multiply.a" not in source


def test_paint_slice_does_not_fake_economy_values():
    source = Path("scripts/workshop_paint_controller.decay").read_text(encoding="utf-8")
    assert "purchase(" not in source
    assert "street_cred" not in source
    assert "money" not in source
