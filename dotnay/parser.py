from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Union

HEADER = "NAYLA"
SEPARATOR = "---"
EXPIRES_PREFIX = "expires:"

_DURATION = re.compile(r"^(\d+)([smhd])$")
_EXACT_DATE = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{2}):(\d{2})(?::(\d{2}))?$")
_UNIT_SECONDS = {"s": 1, "m": 60, "h": 3600, "d": 86400}


class NaylaError(ValueError):
    pass


@dataclass(frozen=True)
class NaylaDocument:
    content: str
    expires_at: datetime
    expires_spec: str

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        return (now or datetime.now()) >= self.expires_at

    def remaining(self, now: Optional[datetime] = None) -> timedelta:
        return self.expires_at - (now or datetime.now())


def parse_nayla(text: str, created_at: Optional[datetime] = None) -> NaylaDocument:
    if not text:
        raise NaylaError("The file is empty. Line 1 must be 'NAYLA'.")

    text = text.lstrip("\ufeff")
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    first = lines[0].strip()
    if first != HEADER:
        raise NaylaError(f"Line 1 must be '{HEADER}', found {first!r}.")

    if len(lines) < 2 or not lines[1].strip():
        raise NaylaError("Line 2 must be an expiry line, for example 'expires: 24h'.")

    expires_line = lines[1].strip()
    if not expires_line.lower().startswith(EXPIRES_PREFIX):
        raise NaylaError(f"Line 2 must start with '{EXPIRES_PREFIX}', found {expires_line!r}.")

    expires_spec = expires_line[len(EXPIRES_PREFIX):].strip()
    if not expires_spec:
        raise NaylaError("The expiry value is missing. Use '24h' or '2026-11-04 18:00'.")

    if len(lines) < 3 or lines[2].strip() != SEPARATOR:
        found = "end of file" if len(lines) < 3 else repr(lines[2])
        raise NaylaError(f"Line 3 must be '{SEPARATOR}', found {found}.")

    content = "\n".join(lines[3:])
    expires_at = _resolve_expiry(expires_spec, created_at or datetime.now())
    return NaylaDocument(content=content, expires_at=expires_at, expires_spec=expires_spec)


def load_nayla(path: Union[str, Path]) -> NaylaDocument:
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        raise NaylaError(f"File not found: {path}") from None
    except IsADirectoryError:
        raise NaylaError(f"Expected a file, got a folder: {path}") from None
    except UnicodeDecodeError:
        raise NaylaError(f"{path} is not valid UTF-8 text.") from None
    except OSError as exc:
        raise NaylaError(f"Could not read {path}: {exc}") from None
    return parse_nayla(text, created_at=file_creation_time(path))


def file_creation_time(path: Union[str, Path]) -> datetime:
    stat = Path(path).stat()
    stamp = getattr(stat, "st_birthtime", None)
    if stamp is None:
        stamp = stat.st_ctime if os.name == "nt" else stat.st_mtime
    return datetime.fromtimestamp(stamp)


def _resolve_expiry(spec: str, created_at: datetime) -> datetime:
    duration = _DURATION.match(spec.lower())
    if duration:
        amount = int(duration.group(1))
        seconds = amount * _UNIT_SECONDS[duration.group(2)]
        return created_at + timedelta(seconds=seconds)

    exact = _EXACT_DATE.match(spec)
    if exact:
        parts = [int(value) if value is not None else 0 for value in exact.groups()]
        try:
            return datetime(*parts)
        except ValueError:
            raise NaylaError(f"'{spec}' is not a valid date and time.") from None

    raise NaylaError(
        f"Invalid expiry {spec!r}. Use a duration such as '24h', '30m', '7d' "
        "or an exact date such as '2026-11-04 18:00'."
    )
