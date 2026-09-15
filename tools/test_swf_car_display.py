#!/usr/bin/env python3
import unittest
from swf_car_display import IDENT_CX, combine_cxform, svg_filter_values


class CarDisplayColourTransformTests(unittest.TestCase):
    def test_identity(self):
        self.assertEqual(combine_cxform(IDENT_CX, None), IDENT_CX)

    def test_nested_multiply_and_add(self):
        parent = {"mult": [128, 256, 256, 128], "add": [10, 0, 0, 0]}
        child = {"mult": [128, 128, 256, 128], "add": [20, 30, 0, 16]}
        result = combine_cxform(parent, child)
        self.assertAlmostEqual(result["mult"][0], 64)
        self.assertAlmostEqual(result["mult"][1], 128)
        self.assertAlmostEqual(result["mult"][3], 64)
        self.assertAlmostEqual(result["add"][0], 20)
        self.assertAlmostEqual(result["add"][1], 30)
        self.assertAlmostEqual(result["add"][3], 8)

    def test_svg_values_include_rgb_and_alpha(self):
        cx = {"mult": [128, 192, 256, 64], "add": [32, -16, 0, 24]}
        values = svg_filter_values(cx)
        self.assertAlmostEqual(values[0][0], 0.5)
        self.assertAlmostEqual(values[0][1], 32 / 255.0)
        self.assertAlmostEqual(values[1][0], 0.75)
        self.assertAlmostEqual(values[1][1], -16 / 255.0)
        self.assertAlmostEqual(values[3][0], 0.25)
        self.assertAlmostEqual(values[3][1], 24 / 255.0)


if __name__ == "__main__":
    unittest.main()
