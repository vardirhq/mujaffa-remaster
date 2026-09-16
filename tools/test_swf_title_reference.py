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
        self.assertEqual(result["schema_version"], 5)
        self.assertEqual(result["stage"], [500.0, 500.0])
        self.assertEqual(result["frame_rate"], 12.0)
        labels = result["opening_labels"]
        self.assertEqual([entry["label"] for entry in labels], ["start", "velkommen", "speakDone", "gotoInstruktioner", "gotoGame", "initGame"])
        self.assertEqual([entry["frame"] for entry in labels], sorted(entry["frame"] for entry in labels))

    def test_named_character_evidence_is_well_formed(self):
        characters = extract(ROOT / "mujaffa_3juni_2003.swf")["named_characters"]
        for entry in characters:
            self.assertIsInstance(entry["character_id"], int)
            self.assertTrue(entry["name"])
            self.assertTrue(set(entry["sources"]).issubset({"SymbolClass", "ExportAssets"}))

    def test_title_display_primitives_exist_in_original(self):
        counts = extract(ROOT / "mujaffa_3juni_2003.swf")["title_relevant_tag_counts"]
        self.assertTrue(any(name.startswith("DefineShape") for name in counts))
        self.assertTrue(any(name.startswith("PlaceObject") for name in counts))
        self.assertTrue(any(name.startswith("DefineButton") for name in counts))
        self.assertTrue(any(name in counts for name in ("DefineText", "DefineText2", "DefineEditText")))

    def test_opening_placements_have_decoded_depth_and_transform(self):
        trace = extract(ROOT / "mujaffa_3juni_2003.swf")["opening_display_trace"]
        placements = [entry for entry in trace if entry["tag"].startswith("PlaceObject")]
        self.assertTrue(placements)
        self.assertTrue(all(isinstance(entry["depth"], int) for entry in placements))
        matrices = [entry["matrix"] for entry in placements if "matrix" in entry]
        self.assertTrue(matrices)
        for matrix in matrices:
            self.assertEqual(set(matrix), {"scale_x", "scale_y", "rotate_skew_0", "rotate_skew_1", "translate_x", "translate_y"})
            self.assertTrue(all(isinstance(value, float) for value in matrix.values()))

    def test_opening_trace_recovers_character_ids(self):
        placements = [entry for entry in extract(ROOT / "mujaffa_3juni_2003.swf")["opening_display_trace"] if entry["tag"].startswith("PlaceObject")]
        self.assertTrue(any("character_id" in entry for entry in placements))
        self.assertTrue(all(entry["character_id"] > 0 for entry in placements if "character_id" in entry))


if __name__ == "__main__":
    unittest.main()
