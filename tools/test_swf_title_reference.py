import sys,unittest
from pathlib import Path
TOOLS=Path(__file__).resolve().parent;ROOT=TOOLS.parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from swf_title_reference import extract
class TitleReferenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.result=extract(ROOT/"mujaffa_3juni_2003.swf")
 def test_original_opening_landmarks_are_recovered_in_order(self):
  r=self.result;self.assertEqual(r["schema_version"],8);self.assertEqual(r["stage"],[500.,500.]);self.assertEqual(r["frame_rate"],12.);labels=r["opening_labels"];self.assertEqual([e["label"] for e in labels],["start","velkommen","speakDone","gotoInstruktioner","gotoGame","initGame"]);self.assertEqual([e["frame"] for e in labels],sorted(e["frame"] for e in labels))
 def test_named_character_evidence_is_well_formed(self):
  for e in self.result["named_characters"]:self.assertIsInstance(e["character_id"],int);self.assertTrue(e["name"]);self.assertTrue(set(e["sources"]).issubset({"SymbolClass","ExportAssets"}))
 def test_title_display_primitives_exist_in_original(self):
  c=self.result["title_relevant_tag_counts"];self.assertTrue(any(n.startswith("DefineShape") for n in c));self.assertTrue(any(n.startswith("PlaceObject") for n in c));self.assertTrue(any(n.startswith("DefineButton") for n in c));self.assertTrue(any(n in c for n in ("DefineText","DefineText2","DefineEditText")))
 def test_opening_placements_have_decoded_depth_and_transform(self):
  p=[e for e in self.result["opening_display_trace"] if e["tag"].startswith("PlaceObject")];self.assertTrue(p);self.assertTrue(all(isinstance(e["depth"],int) for e in p));m=[e["matrix"] for e in p if "matrix" in e];self.assertTrue(m)
  for x in m:self.assertEqual(set(x),{"scale_x","scale_y","rotate_skew_0","rotate_skew_1","translate_x","translate_y"});self.assertTrue(all(isinstance(v,float) for v in x.values()))
 def test_opening_trace_recovers_character_ids(self):
  p=[e for e in self.result["opening_display_trace"] if e["tag"].startswith("PlaceObject")];self.assertTrue(any("character_id" in e for e in p));self.assertTrue(all(e["character_id"]>0 for e in p if "character_id" in e))
 def test_opening_labels_have_resolved_display_snapshots(self):
  s=self.result["opening_display_snapshots"];self.assertEqual([x["label"] for x in s],[e["label"] for e in self.result["opening_labels"]])
  for x in s:
   d=[e["depth"] for e in x["display_list"]];self.assertEqual(d,sorted(d));self.assertEqual(len(d),len(set(d)));self.assertTrue(all("character_id" in e for e in x["display_list"]));self.assertTrue(all("definition" in e for e in x["display_list"]))
 def test_color_transforms_are_structured_when_present(self):
  for x in [e["color_transform"] for e in self.result["opening_display_trace"] if "color_transform" in e]:self.assertEqual(set(x),{"multiply","add"});self.assertEqual(set(x["multiply"]),set("rgba"));self.assertEqual(set(x["add"]),set("rgba"))
 def test_character_definition_index_covers_display_kinds(self):
  defs=self.result["character_definitions"];self.assertTrue(defs);self.assertTrue(set(e["kind"] for e in defs.values()).issubset({"shape","button","text","edit_text","sprite"}));placed={str(e["character_id"]) for s in self.result["opening_display_snapshots"] for e in s["display_list"]};self.assertTrue(placed.issubset(defs.keys()))
if __name__=="__main__":unittest.main()
