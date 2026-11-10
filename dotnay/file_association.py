"""Register the .nayla file type for the current Windows user."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

from .resources import asset_dir, executable_path, is_frozen

ASSOCIATION_ID = "dotnay.nayla"
FILE_EXTENSION = ".nayla"
REGISTRY_CLASSES = r"Software\Classes"
ASSET_DIR = asset_dir()
PROJECT_ROOT = ASSET_DIR.parent.parent


def build_open_command(executable: str | Path, project_root: Path = PROJECT_ROOT) -> str:
    """Build an Explorer command for a source checkout or a frozen app."""
    if is_frozen():
        return f'"{executable}" "%1"'

    code = (
        f"import sys; sys.path.insert(0, {str(project_root)!r}); "
        "from dotnay.app import main; "
        "raise SystemExit(main([sys.argv[1]]))"
    )
    command = subprocess.list2cmdline([str(executable), "-c", code])
    return f'{command} "%1"'


def _icon_source() -> str:
    """A stable icon path: the .exe itself when frozen, else the bundled .ico."""
    if is_frozen():
        return f'"{executable_path()}",0'
    return f'"{ASSET_DIR / "nayla.ico"}",0'


def _launcher() -> Path:
    if is_frozen():
        return executable_path()
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    return pythonw if pythonw.exists() else Path(sys.executable)


def register() -> None:
    """Register the note icon and open command in the current user's registry."""
    if os.name != "nt":
        raise RuntimeError("The .nayla file association can only be registered on Windows.")

    import winreg

    classes = REGISTRY_CLASSES
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{classes}\\{FILE_EXTENSION}") as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, ASSOCIATION_ID)

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, f"{classes}\\{ASSOCIATION_ID}") as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, "Nayla note")

    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, f"{classes}\\{ASSOCIATION_ID}\\DefaultIcon"
    ) as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, _icon_source())

    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        f"{classes}\\{ASSOCIATION_ID}\\shell\\open\\command",
    ) as key:
        winreg.SetValueEx(
            key,
            None,
            0,
            winreg.REG_SZ,
            build_open_command(_launcher(), PROJECT_ROOT),
        )

    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def _report(message: str, error: bool = False) -> None:
    """Print in a console, or show a dialog in a windowed frozen app."""
    if os.environ.get("DOTNAY_NO_UI"):
        return
    stream = sys.stderr if error else sys.stdout
    if stream is not None:
        try:
            print(message, file=stream)
            return
        except Exception:
            pass
    if os.name == "nt":
        flags = 0x10 if error else 0x40
        try:
            ctypes.windll.user32.MessageBoxW(None, message, "dotnay", flags)
        except Exception:
            pass


def main() -> int:
    try:
        register()
    except (OSError, RuntimeError) as exc:
        _report(f"Could not register .nayla files: {exc}", error=True)
        return 1
    _report("Registered .nayla files for this Windows user.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
