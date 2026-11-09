"""Build and save .nayla files from the app's New nayla screen."""

from __future__ import annotations

from pathlib import Path
from typing import Union

from .parser import HEADER, SEPARATOR


def build_nayla(expires: str, content: str) -> str:
    """Return the text of a .nayla file for the given expiry and note body."""
    text = f"{HEADER}\nexpires: {expires.strip()}\n{SEPARATOR}\n{content}"
    if content and not text.endswith("\n"):
        text += "\n"
    return text


def write_nayla(path: Union[str, Path], expires: str, content: str) -> Path:
    """Write a .nayla file and return its final path.

    If the caller provides no extension, '.nayla' is appended.
    """
    path = Path(path)
    if not path.suffix:
        path = path.with_suffix(".nayla")
    # newline="" keeps the file LF-only, as required by the format.
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(build_nayla(expires, content))
    return path
