import unittest
from datetime import timedelta

from dotnay.timefmt import format_remaining


class FormatRemainingTests(unittest.TestCase):
    def test_hours_minutes_seconds(self):
        self.assertEqual(format_remaining(timedelta(hours=3, minutes=12, seconds=59)), "03:12:59")

    def test_days_are_shown_separately(self):
        self.assertEqual(
            format_remaining(timedelta(days=2, hours=4, minutes=12, seconds=9)),
            "2d 04:12:09",
        )

    def test_seconds_are_rounded_up(self):
        self.assertEqual(format_remaining(timedelta(seconds=0.2)), "00:00:01")

    def test_negative_values_clamp_to_zero(self):
        self.assertEqual(format_remaining(timedelta(seconds=-45)), "00:00:00")


if __name__ == "__main__":
    unittest.main()
