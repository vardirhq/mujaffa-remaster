import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parent
ROOT = TOOLS.parent
if str(TOOLS) not in sys.path:
    sys.path.insert(0, str(TOOLS))

from swf_title_reference import extract


class TitleReferenceTests(unittest.TestCase):
    def test_original_opening_landmarks_are_recovered_in_order(self):
        result = extract(ROOT / "mujaffa_3juni_2003.swf")

        self.assertEqual(result["schema_version"], 2)
        self.assertEqual(result["stage"], [500.0, 500.0])
        self.assertEqual(result["frame_rate"], 12.0)

        labels = result["opening_labels"]
        self.assertEqual(
            [entry["label"] for entry in labels],
            [
                "start",
                "velkommen",
                "speakDone",
                "gotoInstruktioner",
                "gotoGame",
                "initGame",
            ],
        )
        self.assertEqual(
            [entry["frame"] for entry in labels],
            sorted(entry["frame"] for entry in labels),
        )

    def test_named_character_evidence_is_well_formed(self):
        result = extract(ROOT / "mujaffa_3juni_2003.swf")
        characters = result["named_characters"]
        self.assertIsInstance(characters, list)
        for entry in characters:
            self.assertIsInstance(entry["character_id"], int)
            self.assertTrue(entry["name"])
            self.assertTrue(entry["sources"])
            self.assertTrue(set(entry["sources"]).issubset({"SymbolClass", "ExportAssets"}))


if __name__ == "__main__":
    unittest.main()
