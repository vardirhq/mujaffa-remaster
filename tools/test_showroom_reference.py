from pathlib import Path
import json
import tempfile
import unittest


class ShowroomReferenceTests(unittest.TestCase):
    def test_documented_showroom_character_is_canonical(self):
        # Keep the acceptance contract explicit: frame 730's room art is
        # character 934, recovered by the scene-map work in PR #15.
        doc = Path('docs/original-showroom.md').read_text(encoding='utf-8')
        self.assertIn('character `934`', doc)
        self.assertIn('frame 730', doc)


if __name__ == '__main__':
    unittest.main()
