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
    "WZZ": "Whangarei",
    "WNU": "Whanganui",
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
    "Whanganui": "WNU",
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
    "Whangarei": ("WHN", "WZZ"),
    "Whanganui": ("WNU",),
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


# Plain-language labels for PDF / UI (not raw codes only)
BRANCH_CARS_LOC_LABEL: dict[str, str] = {
    "Whangarei": "Whangarei (Cars+ WHN50/60 & WZZ52)",
    "Whanganui": "Whanganui (Cars+ WNU50/60)",
    "Taupo": "Taupo (Cars+ code TUO)",
    "Kerikeri": "Kerikeri (Cars+ codes KKE & KKZ)",
}


def cars_loc_label(branch: str) -> str:
    return BRANCH_CARS_LOC_LABEL.get(
        branch, f"{branch} ({'/'.join(cars_loc_prefixes(branch))})"
    )


def cars_loc_help_text(branch: str) -> str:
    if branch == "Whangarei":
        return (
            "Whangarei on Cars+: WHN50/60 or WZZ52 on RA Loc Out or RA Loc In "
            "(return location). WNU = Whanganui — not counted for Whangarei."
        )
    if branch == "Whanganui":
        return (
            "Whanganui on Cars+: WNU50, WNU60. "
            "WHN/WZZ codes are Whangarei, not Whanganui."
        )
    prefixes = ", ".join(cars_loc_prefixes(branch))
    return f"Cars+ RA Loc Out must start with: {prefixes} for this branch."


def _loc_matches_branch(loc: str, branch: str) -> bool:
    loc = (loc or "").strip().upper()
    if not loc:
        return False
    return any(loc.startswith(p) for p in cars_loc_prefixes(branch))


def cars_row_at_branch_location(
    ra_loc_out: str, branch: str, ra_loc_in: str = ""
) -> bool:
    """
    Cars+ fuel is often billed at return (RA Loc In = WHN60) while Loc Out is
    another depot (e.g. AUC50). Match either column for branch billing checks.
    """
    return _loc_matches_branch(ra_loc_out, branch) or _loc_matches_branch(ra_loc_in, branch)


def filter_cars_for_branch(rows: list, branch: str) -> list:
    """Keep Cars+ charges where Out or In location matches this branch."""
    return [
        r
        for r in rows
        if cars_row_at_branch_location(r.ra_loc_out, branch, r.ra_loc_in)
    ]
