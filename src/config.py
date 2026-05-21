import os
import sys
from pathlib import Path

APP_NAME = "Fuel Reconcile"
APP_VERSION = "0.1.0"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    """Directory containing the app (source tree or folder with FuelReconcile.exe)."""
    if _is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def user_data_dir() -> Path:
    """Writable data directory (database, logs). Persists across app updates."""
    if _is_frozen():
        if sys.platform == "win32":
            base = os.environ.get("LOCALAPPDATA")
            if not base:
                base = str(Path.home() / "AppData" / "Local")
            return Path(base) / "FuelReconcile"
        return Path.home() / ".fuel_reconcile"
    return app_root() / "data"


PROJECT_ROOT = app_root()
DOCS_DIR = PROJECT_ROOT / "docs"
DATA_DIR = user_data_dir() if _is_frozen() else (app_root() / "data")
DB_PATH = DATA_DIR / "fuel_app.db"

# Location code prefix -> branch name (from branch litres sheets + Cars+ codes)
LOC_TO_BRANCH: dict[str, str] = {
    "TUO": "Taupo",
    "KKE": "Kerikeri",
    "KKZ": "Kerikeri",
    "WHN": "Whangarei",
    "WNU": "Whangarei",
    "WHK": "Whakatane",
    "RTR": "Rotorua",
    "TRG": "Tauranga",
    "NPY": "Napier",
    "AUC": "Auckland",
    "HML": "Hamilton",
    "PMR": "Palmerston North",
    "WEL": "Wellington",
    "FPO": "Other",
}


# Branch name -> short tab label on branch litres workbook
BRANCH_TAB_CODE: dict[str, str] = {
    "Taupo": "TUO",
    "Kerikeri": "KKE",
    "Whangarei": "WHN",
    "Whakatane": "WHK",
    "Rotorua": "RTR",
    "Tauranga": "TRG",
}


def branch_tab_code(branch: str) -> str:
    return BRANCH_TAB_CODE.get(branch, branch[:3].upper())


def branch_from_loc(loc: str) -> str | None:
    if not loc:
        return None
    prefix = loc[:3].upper()
    return LOC_TO_BRANCH.get(prefix)


# Cars+ RA Loc Out prefixes that count as "this branch" for billing checks
BRANCH_CARS_LOC_PREFIXES: dict[str, tuple[str, ...]] = {
    "Taupo": ("TUO",),
    "Kerikeri": ("KKE", "KKZ"),
    "Whangarei": ("WHN", "WNU"),
    "Whakatane": ("WHK",),
    "Rotorua": ("RTR",),
    "Tauranga": ("TRG",),
    "Napier": ("NPY",),
    "Auckland": ("AUC",),
    "Hamilton": ("HML",),
    "Wellington": ("WEL",),
    "Palmerston North": ("PMR",),
}


def cars_loc_prefixes(branch: str) -> tuple[str, ...]:
    return BRANCH_CARS_LOC_PREFIXES.get(branch, (branch_tab_code(branch),))


def cars_row_at_branch_location(ra_loc_out: str, branch: str) -> bool:
    loc = (ra_loc_out or "").strip().upper()
    if not loc:
        return False
    return any(loc.startswith(p) for p in cars_loc_prefixes(branch))


def filter_cars_for_branch(rows: list, branch: str) -> list:
    """Keep only Cars+ charges at this branch's RA Loc Out codes."""
    return [r for r in rows if cars_row_at_branch_location(r.ra_loc_out, branch)]
