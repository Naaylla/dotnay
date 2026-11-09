"""Register the .nayla file type for the current Windows user."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path

ASSOCIATION_ID = "dotnay.nayla"
FILE_EXTENSION = ".nayla"
REGISTRY_CLASSES = r"Software\Classes"
ASSET_DIR = Path(__file__).resolve().parent / "assets"
PROJECT_ROOT = ASSET_DIR.parent.parent


def build_open_command(executable: str | Path, project_root: Path = PROJECT_ROOT) -> str:
    """Build an Explorer command that works without an installed dotnay package."""
    code = (
        f"import sys; sys.path.insert(0, {str(project_root)!r}); "
        "from dotnay.app import main; "
        "raise SystemExit(main([sys.argv[1]]))"
    )
    command = subprocess.list2cmdline([str(executable), "-c", code])
    return f'{command} "%1"'


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

    icon_path = ASSET_DIR / "nayla.ico"
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER, f"{classes}\\{ASSOCIATION_ID}\\DefaultIcon"
    ) as key:
        winreg.SetValueEx(key, None, 0, winreg.REG_SZ, f'"{icon_path}",0')

    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = Path(sys.executable)
    with winreg.CreateKey(
        winreg.HKEY_CURRENT_USER,
        f"{classes}\\{ASSOCIATION_ID}\\shell\\open\\command",
    ) as key:
        winreg.SetValueEx(
            key,
            None,
            0,
            winreg.REG_SZ,
            build_open_command(pythonw, PROJECT_ROOT),
        )

    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def main() -> int:
    try:
        register()
    except (OSError, RuntimeError) as exc:
        print(f"Could not register .nayla files: {exc}", file=sys.stderr)
        return 1
    print("Registered .nayla files for this Windows user.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
