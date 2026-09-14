import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from swf_inventory import inventory, parse_header, verify_mujaffa_reference


def bits(value: int, width: int) -> str:
    if value < 0:
        value = (1 << width) + value
    return f"{value:0{width}b}"


def rect(width_px: int, height_px: int) -> bytes:
    values = (0, width_px * 20, 0, height_px * 20)
    nbits = max(2, max(abs(value).bit_length() + 1 for value in values))
    stream = f"{nbits:05b}" + "".join(bits(value, nbits) for value in values)
    stream += "0" * ((8 - len(stream) % 8) % 8)
    return int(stream, 2).to_bytes(len(stream) // 8, "big")


def make_swf(signature: bytes = b"FWS") -> bytes:
    body = rect(100, 50)
    body += struct.pack("<HH", 24 * 256, 1)
    body += struct.pack("<H", 1 << 6)  # ShowFrame, empty payload
    body += struct.pack("<H", 0)  # End
    length = 8 + len(body)
    if signature == b"FWS":
        return signature + bytes([6]) + struct.pack("<I", length) + body
    if signature == b"CWS":
        return signature + bytes([6]) + struct.pack("<I", length) + zlib.compress(body)
    raise ValueError(signature)


class SwfInventoryTests(unittest.TestCase):
    def test_reads_uncompressed_movie_header_and_tags(self) -> None:
        raw = make_swf()
        _, header = parse_header(raw)
        self.assertEqual(header.version, 6)
        self.assertEqual(header.width, 100.0)
        self.assertEqual(header.height, 50.0)
        self.assertEqual(header.fps, 24.0)
        self.assertEqual(header.frame_count, 1)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.swf"
            path.write_bytes(raw)
            report = inventory(path)

        self.assertEqual(report["summary"]["tag_count"], 2)
        self.assertEqual(report["tags"][0]["name"], "End")
        self.assertEqual(report["tags"][1]["name"], "ShowFrame")

    def test_reads_zlib_compressed_swf(self) -> None:
        raw = make_swf(b"CWS")
        data, header = parse_header(raw)
        self.assertEqual(header.signature, "CWS")
        self.assertEqual(len(data), struct.unpack_from("<I", raw, 4)[0])

    def test_reference_verifier_reports_drift(self) -> None:
        report = {
            "movie": {
                "version": 6,
                "width": 500.0,
                "height": 500.0,
                "fps": 12.0,
                "frame_count": 810,
            },
            "summary": {
                "bitmap_definitions": 0,
                "shapes": 514,
                "sprites": 258,
                "script_blocks": 67,
            },
        }
        failures = verify_mujaffa_reference(report)
        self.assertTrue(any("frame_count" in failure for failure in failures))


if __name__ == "__main__":
    unittest.main()
