from __future__ import annotations

import struct
import unittest
from pathlib import Path

import swf_art_extract as base
import swf_art_extract_fixed as fixed


class CorrectedShapeStylesTest(unittest.TestCase):
    def test_mujaffa_complex_shape_uses_all_new_style_blocks(self):
        swf = Path(__file__).resolve().parents[1] / "mujaffa_3juni_2003.swf"
        data, offset = base.parse_swf(swf)
        target = None
        code = None
        for tag_code, payload in base.iter_tags(data, offset):
            if tag_code in (2, 22, 32) and struct.unpack_from("<H", payload, 0)[0] == 21:
                code = tag_code
                target = payload
                break
        self.assertIsNotNone(target)

        character_id, _bounds, fills, _lines, fill_edges, _line_edges = fixed.parse_shape(code, target)
        self.assertEqual(character_id, 21)
        # Shape 21 is the detailed workshop Mujaffa figure. The broken parser
        # collapsed every StateNewStyles block onto fill #1, making the entire
        # character pale. The original uses 167 style blocks and many colours.
        self.assertEqual(len(fills), 167)
        self.assertGreater(len(fill_edges), 100)
        self.assertGreater(max(fill_edges), 100)

        colors = {
            fill.color
            for index in fill_edges
            for fill in [fills[index - 1]]
            if fill.kind == "solid" and fill.color is not None
        }
        self.assertGreater(len(colors), 10)
        self.assertIn((217, 0, 0, 255), colors)      # cap detail
        self.assertIn((166, 118, 19, 255), colors)  # skin/gold palette
        self.assertIn((0, 0, 0, 255), colors)


if __name__ == "__main__":
    unittest.main()
