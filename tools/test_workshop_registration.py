from __future__ import annotations

import unittest
from pathlib import Path

from register_showroom_car import CAR_MATRIX, WORKSHOP_FRAME
from swf_scene_map import main_timeline
from swf_showroom_extract import WORKSHOP


class WorkshopRegistrationTest(unittest.TestCase):
    def test_runtime_registration_matches_original_kob_frame(self):
        swf = Path(__file__).resolve().parents[1] / "mujaffa_3juni_2003.swf"
        labels, snapshots = main_timeline(swf)
        self.assertIn("køb", labels[WORKSHOP_FRAME])

        display = snapshots[WORKSHOP_FRAME]
        by_name = {item.get("name"): item for item in display if item.get("name")}
        by_character = {item.get("character"): item for item in display if item.get("character") is not None}

        self.assertEqual(tuple(by_name["bil"]["matrix"]), CAR_MATRIX)
        self.assertEqual(tuple(by_name["mujaffa"]["matrix"]), tuple(WORKSHOP["mujaffa"]["matrix"]))
        self.assertEqual(by_character[867]["character"], WORKSHOP["room"]["character"])
        self.assertEqual(tuple(by_character[867]["matrix"]), tuple(WORKSHOP["room"]["matrix"]))
        self.assertEqual(by_name["oversigt"]["character"], WORKSHOP["panel"]["character"])
        self.assertEqual(tuple(by_name["oversigt"]["matrix"]), tuple(WORKSHOP["panel"]["matrix"]))

        logo = by_character[1]
        self.assertEqual(tuple(logo["matrix"]), tuple(WORKSHOP["logo"]["matrix"]))


if __name__ == "__main__":
    unittest.main()
