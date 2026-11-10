"""Locate bundled assets in a source checkout and in a frozen build."""

from __future__ import annotations

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True when running from a PyInstaller executable."""
    return bool(getattr(sys, "frozen", False))


def asset_dir() -> Path:
    """Folder holding the icons, whether running from source or an .exe."""
    bundle = getattr(sys, "_MEIPASS", None)
    if bundle:
        return Path(bundle) / "dotnay" / "assets"
    return Path(__file__).resolve().parent / "assets"


def executable_path() -> Path:
    """The app executable: the frozen .exe, or the running Python."""
    return Path(sys.executable).resolve()
