"""Small helpers for turning a remaining time into display text."""

from __future__ import annotations

import math
from datetime import timedelta


def format_remaining(delta: timedelta) -> str:
    """Return a zero-padded countdown such as '03:12:59' or '2d 04:12:59'.

    Seconds are rounded up so the display only reaches 00:00:00 when the
    note is actually due. Negative values are clamped to zero.
    """
    total = max(0, math.ceil(delta.total_seconds()))
    days, rest = divmod(total, 86_400)
    hours, rest = divmod(rest, 3_600)
    minutes, seconds = divmod(rest, 60)
    clock = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return f"{days}d {clock}" if days else clock
