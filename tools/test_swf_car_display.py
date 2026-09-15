#!/usr/bin/env python3
import unittest
from swf_car_display import combine_alpha


class CarDisplayAlphaTests(unittest.TestCase):
    def test_multiplies_nested_alpha(self):
        cx = {"mult": [256, 256, 256, 128], "add": [0, 0, 0, 0]}
        self.assertAlmostEqual(combine_alpha(1.0, cx), 0.5)
        self.assertAlmostEqual(combine_alpha(0.5, cx), 0.25)

    def test_identity_without_transform(self):
        self.assertEqual(combine_alpha(0.75, None), 0.75)


if __name__ == "__main__":
    unittest.main()
