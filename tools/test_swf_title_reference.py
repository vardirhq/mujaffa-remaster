import sys,unittest
from pathlib import Path
TOOLS=Path(__file__).resolve().parent;ROOT=TOOLS.parent
if str(TOOLS) not in sys.path:sys.path.insert(0,str(TOOLS))
from swf_title_reference import extract
class TitleReferenceTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.result=extract(ROOT/"mujaffa_3juni_2003.swf")
 def test_original_opening_landmarks_are_recovered_in_order(self):
  r=self.result;self.assertEqual(r["schema_version"],11);self.assertEqual(r["stage"],[500.,500.]);self.assertEqual(r["frame_rate"],12.);labels=r["opening_labels"];self.assertEqual([e["label"] for e in labels],["start","velkommen","speakDone","gotoInstruktioner","gotoGame","initGame"]);self.assertEqual([e["frame"] for e in labels],sorted(e["frame"] for e in labels))
 def test_named_character_evidence_is_well_formed(self):
  for e in self.result["named_characters"]:self.assertIsInstance(e["character_id"],int);self.assertTrue(e["name"]);self.assertTrue(set(e["sources"]).issubset({"SymbolClass","ExportAssets"}))
 def test_title_display_primitives_exist_in_original(self):
  c=self.result["title_relevant_tag_counts"];self.assertTrue(any(n.startswith("DefineShape") for n in c));self.assertTrue(any(n.startswith("PlaceObject") for n in c));self.assertTrue(any(n.startswith("DefineButton") for n in c));self.assertTrue(any(n in c for n in ("DefineText","DefineText2","DefineEditText")))
 def test_opening_placements_have_decoded_depth_and_transform(self):
  p=[e for e in self.result["opening_display_trace"] if e["tag"].startswith("PlaceObject")];self.assertTrue(p);self.assertTrue(all(isinstance(e["depth"],int) for e in p));self.assertTrue(any("matrix" in e for e in p))
 def test_opening_labels_have_resolved_display_snapshots(self):
  s=self.result["opening_display_snapshots"];self.assertEqual([x["label"] for x in s],[e["label"] for e in self.result["opening_labels"]])
  for x in s:
   d=[e["depth"] for e in x["display_list"]];self.assertEqual(d,sorted(d));self.assertEqual(len(d),len(set(d)));self.assertTrue(all("character_id" in e and "definition" in e for e in x["display_list"]))
 def test_color_transforms_are_structured_when_present(self):
  for x in [e["color_transform"] for e in self.result["opening_display_trace"] if "color_transform" in e]:self.assertEqual(set(x),{"multiply","add"});self.assertEqual(set(x["multiply"]),set("rgba"));self.assertEqual(set(x["add"]),set("rgba"))
 def test_character_definition_index_covers_display_kinds(self):
  defs=self.result["character_definitions"];self.assertTrue(defs);placed={str(e["character_id"]) for s in self.result["opening_display_snapshots"] for e in s["display_list"]};self.assertTrue(placed.issubset(defs.keys()))
 def test_sprite_definitions_include_nested_timeline_evidence(self):
  sprites=[e for e in self.result["character_definitions"].values() if e["kind"]=="sprite"];self.assertTrue(sprites);self.assertTrue(all(e["frame_count"]>=1 for e in sprites));self.assertTrue(any(e["timeline"] for e in sprites));self.assertTrue(any(any(x["tag"].startswith("PlaceObject") for x in e["timeline"]) for e in sprites))
 def test_direct_title_definitions_expose_original_geometry(self):
  defs=self.result["character_definitions"].values();bounded=[e for e in defs if e["kind"] in {"shape","text","edit_text"}];self.assertTrue(bounded);self.assertTrue(all("bounds" in e for e in bounded))
  for e in bounded:
   b=e["bounds"];self.assertLessEqual(b["x_min"],b["x_max"]);self.assertLessEqual(b["y_min"],b["y_max"])
  static=[e for e in defs if e["kind"]=="text"];self.assertTrue(static);self.assertTrue(all("matrix" in e for e in static))
 def test_shape_definitions_expose_original_vector_records(self):
  shapes=[e for e in self.result["character_definitions"].values() if e["kind"]=="shape"];self.assertTrue(shapes);self.assertTrue(all("shape" in e for e in shapes));self.assertTrue(any(e["shape"]["records"] for e in shapes));self.assertTrue(any(any(r["type"] in {"line","curve"} for r in e["shape"]["records"]) for e in shapes))
  for e in shapes:self.assertEqual(set(e["shape"]),{"fills","lines","records"})
if __name__=="__main__":unittest.main()
