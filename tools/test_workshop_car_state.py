from __future__ import annotations
import unittest
from pathlib import Path
from swf_car_display import Movie


class WorkshopCarStateTest(unittest.TestCase):
    def setUp(self):
        swf = Path(__file__).resolve().parents[1] / "mujaffa_3juni_2003.swf"
        self.movie = Movie(swf)

    def test_root_contains_original_under_car_art(self):
        root = self.movie.display(875, 1)
        depth_one = next(item for item in root if item["depth"] == 1)
        self.assertEqual(depth_one.get("character"), 61)

    def test_resting_body_excludes_mujaffa_animation_shapes(self):
        resting = {item.get("character") for item in self.movie.display(775, 1)}
        animated = {item.get("character") for item in self.movie.display(775, 5)}
        self.assertNotIn(773, resting)
        self.assertNotIn(774, resting)
        self.assertIn(773, animated)
        self.assertIn(774, animated)


if __name__ == "__main__":
    unittest.main()
