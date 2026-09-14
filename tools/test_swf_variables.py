import struct
import unittest

from swf_variables import analyze, push_values


def long_action(code: int, payload: bytes) -> bytes:
    return bytes([code]) + struct.pack("<H", len(payload)) + payload


def push_string(value: str) -> bytes:
    return bytes([0]) + value.encode("utf-8") + b"\0"


def push_int(value: int) -> bytes:
    return bytes([7]) + struct.pack("<i", value)


class SwfVariableTests(unittest.TestCase):
    def test_decodes_constant_pool_reference_and_integer(self) -> None:
        self.assertEqual(push_values(bytes([8, 1, 7]) + struct.pack("<i", 42), ["zero", "name"]), ["name", 42])

    def test_records_simple_assignment(self) -> None:
        payload = b"".join(
            [
                long_action(0x96, push_string("cool") + push_int(10)),
                bytes([0x1D]),
                b"\0",
            ]
        )
        report = analyze(payload)
        self.assertEqual(report["writes"], [{"name": "cool", "value": "10", "offset": 14}])

    def test_records_random_expression(self) -> None:
        payload = b"".join(
            [
                long_action(0x96, push_string("fetter_1") + push_int(4)),
                bytes([0x30]),
                long_action(0x96, push_int(1)),
                bytes([0x47]),
                bytes([0x1D]),
                b"\0",
            ]
        )
        report = analyze(payload)
        self.assertEqual(report["writes"][0]["name"], "fetter_1")
        self.assertEqual(report["writes"][0]["value"], "(random(4) + 1)")
        self.assertEqual(report["random_expressions"], ["random(4)"])

    def test_preserves_boolean_range_expression(self) -> None:
        payload = b"".join(
            [
                long_action(0x96, push_string("cool")),
                bytes([0x1C]),
                long_action(0x96, push_int(199)),
                bytes([0x67]),
                long_action(0x96, push_string("cool")),
                bytes([0x1C]),
                long_action(0x96, push_int(600)),
                bytes([0x48]),
                bytes([0x10]),
                bytes([0x12]),
                long_action(0x9D, struct.pack("<h", 0)),
                b"\0",
            ]
        )
        report = analyze(payload)
        self.assertEqual(
            report["conditions"][0]["condition"],
            "!((var(cool) > 199) && (var(cool) < 600))",
        )


if __name__ == "__main__":
    unittest.main()
