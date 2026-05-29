"""Startup checks when running as a PyInstaller frozen Windows app."""

import sys
from pathlib import Path


def _is_onefile() -> bool:
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _show_windows_message(title: str, text: str) -> None:
    try:
        import ctypes

        ctypes.windll.user32.MessageBoxW(0, text, title, 0x10)  # MB_ICONERROR
    except Exception:
        print(f"{title}\n{text}", file=sys.stderr)


def ensure_frozen_layout() -> bool:
    """
    One-file exe: everything unpacks to a temp folder at runtime (_MEIPASS).
    Onedir (legacy): requires _internal next to the exe.
    """
    if not getattr(sys, "frozen", False):
        return True
    if sys.platform != "win32":
        return True

    exe_path = str(Path(sys.executable).resolve()).lower()

    # Opening .exe from inside RAR/zip preview breaks one-file unpack too
    if ".rar" in exe_path or (
        "temp" in exe_path and ".zip" in exe_path and "fuelreconcile" in exe_path
    ):
        _show_windows_message(
            "Fuel Reconcile — save the .exe first",
            "Do not run this program from inside a WinRAR/ZIP window.\n\n"
            "1. Right-click the download → Extract All (or Save As)\n"
            "2. Put FuelReconcile.exe on Desktop or Documents\n"
            "3. Double-click that saved copy\n\n"
            "You only need this one .exe file after you extract it.",
        )
        return False

    if _is_onefile():
        meipass = Path(getattr(sys, "_MEIPASS", ""))
        if meipass.is_dir() and not list(meipass.glob("python3*.dll")):
            _show_windows_message(
                "Fuel Reconcile — startup failed",
                "The app could not unpack its files.\n\n"
                "Try: move FuelReconcile.exe to Desktop, or install\n"
                "Microsoft Visual C++ Redistributable (x64):\n"
                "https://aka.ms/v1/vc/Redist.x64",
            )
            return False
        return True

    # Legacy onedir layout
    exe_dir = Path(sys.executable).resolve().parent
    internal = exe_dir / "_internal"
    if not internal.is_dir():
        _show_windows_message(
            "Fuel Reconcile — incomplete install",
            "The _internal folder is missing.\n\n"
            "Use the single FuelReconcile.exe build, or extract the full folder.",
        )
        return False
    if not list(internal.glob("python3*.dll")):
        _show_windows_message(
            "Fuel Reconcile — missing files",
            "python3*.dll was not found in _internal.\n"
            "Re-download or use the one-file FuelReconcile.exe.",
        )
        return False

    return True
