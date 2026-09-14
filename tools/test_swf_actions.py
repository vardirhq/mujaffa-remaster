import struct
import unittest

from swf_actions import action_records, direct_strings, strings_from_constant_pool, strings_from_push


class SwfActionTests(unittest.TestCase):
    def test_reads_push_string_literals(self) -> None:
        payload = b"\x00score\x00\x05\x01\x00level1\x00"
        self.assertEqual(strings_from_push(payload), ["score", "level1"])

    def test_reads_constant_pool(self) -> None:
        payload = struct.pack("<H", 3) + b"car\x00cash\x00garage\x00"
        self.assertEqual(strings_from_constant_pool(payload), ["car", "cash", "garage"])

    def test_splits_long_action_records(self) -> None:
        push = b"\x00hello\x00"
        block = bytes([0x96]) + struct.pack("<H", len(push)) + push + bytes([0x06, 0x00])
        records = action_records(block)
        self.assertEqual([record[0] for record in records], [0x96, 0x06])
        self.assertEqual(direct_strings(*records[0][:2]), ["hello"])


if __name__ == "__main__":
    unittest.main()
