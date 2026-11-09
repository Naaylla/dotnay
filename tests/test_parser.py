import unittest
from datetime import datetime, timedelta

from dotnay.parser import NaylaError, parse_nayla


class ParseNaylaTests(unittest.TestCase):
    def test_duration_counts_from_creation_time(self):
        created = datetime(2026, 11, 3, 12, 0, 0)
        document = parse_nayla("NAYLA\nexpires: 24h\n---\nhello", created_at=created)
        self.assertEqual(document.expires_at, created + timedelta(hours=24))
        self.assertEqual(document.content, "hello")

    def test_each_unit(self):
        created = datetime(2026, 11, 3, 12, 0, 0)
        expected = {"10s": 10, "5m": 300, "2h": 7200, "3d": 259200}
        for spec, seconds in expected.items():
            with self.subTest(spec=spec):
                document = parse_nayla(f"NAYLA\nexpires: {spec}\n---\nx", created_at=created)
                self.assertEqual(document.expires_at, created + timedelta(seconds=seconds))

    def test_exact_date(self):
        document = parse_nayla("NAYLA\nexpires: 2026-11-04 18:00\n---\nnote")
        self.assertEqual(document.expires_at, datetime(2026, 11, 4, 18, 0))

    def test_exact_date_with_seconds(self):
        document = parse_nayla("NAYLA\nexpires: 2026-11-04 18:00:30\n---\nnote")
        self.assertEqual(document.expires_at, datetime(2026, 11, 4, 18, 0, 30))

    def test_content_keeps_blank_lines_and_trailing_newline(self):
        document = parse_nayla("NAYLA\nexpires: 1d\n---\nline one\n\nline three\n")
        self.assertEqual(document.content, "line one\n\nline three\n")

    def test_crlf_and_utf8_bom(self):
        document = parse_nayla("\ufeffNAYLA\r\nexpires: 1h\r\n---\r\nbody", created_at=datetime(2026, 1, 1))
        self.assertEqual(document.content, "body")

    def test_expiry_and_remaining(self):
        document = parse_nayla("NAYLA\nexpires: 1h\n---\nx", created_at=datetime(2026, 1, 1, 10, 0))
        self.assertFalse(document.is_expired(now=datetime(2026, 1, 1, 10, 59)))
        self.assertTrue(document.is_expired(now=datetime(2026, 1, 1, 11, 0)))
        self.assertEqual(document.remaining(now=datetime(2026, 1, 1, 10, 30)), timedelta(minutes=30))

    def test_header_is_required(self):
        with self.assertRaisesRegex(NaylaError, "Line 1"):
            parse_nayla("hello\nexpires: 24h\n---\nnote")

    def test_expiry_line_is_required(self):
        with self.assertRaisesRegex(NaylaError, "Line 2"):
            parse_nayla("NAYLA\n---\nnote")

    def test_separator_is_required(self):
        with self.assertRaisesRegex(NaylaError, "Line 3"):
            parse_nayla("NAYLA\nexpires: 24h\nnote")

    def test_invalid_duration(self):
        with self.assertRaisesRegex(NaylaError, "Invalid expiry"):
            parse_nayla("NAYLA\nexpires: 24x\n---\nnote")

    def test_invalid_date(self):
        with self.assertRaisesRegex(NaylaError, "not a valid date"):
            parse_nayla("NAYLA\nexpires: 2026-02-30 10:00\n---\nnote")

    def test_empty_file(self):
        with self.assertRaisesRegex(NaylaError, "empty"):
            parse_nayla("")


if __name__ == "__main__":
    unittest.main()
