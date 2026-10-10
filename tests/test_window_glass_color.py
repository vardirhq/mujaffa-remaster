"""Regression checks for original Flash window CXFORM extraction."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXTRACTOR = (ROOT / "tools/swf_car_layers_alpha.py").read_text()
PREPARER = (ROOT / "tools/prepare_runtime_art.py").read_text()


def test_flash_rgb_is_baked_into_png_not_ignored_svg_filter():
    assert "raster_cxform(element, values)" in EXTRACTOR
    assert "channel.point(lut)" in EXTRACTOR
    assert "feComponentTransfer" not in EXTRACTOR.split("replacement = needle +", 1)[1]
    assert 'needs_rgb or needs_alpha_add' in EXTRACTOR


def test_window_variants_no_longer_use_guessed_purple_palette():
    assert "normalize_window_glass" not in PREPARER
    assert '("standard", "gradient", "tonede", "spejlrefleks")' in PREPARER
