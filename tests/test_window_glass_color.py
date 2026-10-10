"""Glass raster regression: keep linework and alpha while correcting brown tint."""
from pathlib import Path
import importlib.util

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("runtime_art", ROOT / "tools/prepare_runtime_art.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_gradient_removes_brown_without_touching_alpha_or_ink(tmp_path):
    path = tmp_path / "gradient.png"
    image = Image.new("RGBA", (3, 1))
    image.putdata([(150, 90, 70, 190), (15, 10, 15, 255), (150, 90, 70, 0)])
    image.save(path)
    module.normalize_window_glass(path, "gradient")
    pixels = list(Image.open(path).getdata())
    assert pixels[0][2] > pixels[0][0] > pixels[0][1]
    assert pixels[0][3] == 190
    assert pixels[1] == (15, 10, 15, 255)
    assert pixels[2][3] == 0


def test_other_variants_remain_original(tmp_path):
    for variant in ("standard", "tonede", "spejlrefleks"):
        path = tmp_path / f"{variant}.png"
        Image.new("RGBA", (1, 1), (150, 90, 70, 190)).save(path)
        module.normalize_window_glass(path, variant)
        assert Image.open(path).getpixel((0, 0)) == (150, 90, 70, 190)
