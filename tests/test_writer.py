import tempfile
import unittest
from pathlib import Path

from dotnay.parser import parse_nayla
from dotnay.writer import build_nayla, write_nayla


class WriterTests(unittest.TestCase):
    def test_build_creates_a_valid_document(self):
        text = build_nayla("24h", "hello\nworld")
        self.assertTrue(text.startswith("NAYLA\nexpires: 24h\n---\n"))
        self.assertEqual(parse_nayla(text).content, "hello\nworld\n")

    def test_write_adds_extension_and_uses_lf(self):
        with tempfile.TemporaryDirectory() as folder:
            path = write_nayla(Path(folder) / "note", "30m", "hi")
            self.assertEqual(path.suffix, ".nayla")
            self.assertEqual(path.read_bytes(), b"NAYLA\nexpires: 30m\n---\nhi\n")


if __name__ == "__main__":
    unittest.main()
