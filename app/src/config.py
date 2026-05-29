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

# Client-approved branches only. Other national locations must not appear in
# branch lists or reports for this app.
CLIENT_BRANCHES: tuple[str, ...] = (
    "Kerikeri",
    "Whangarei",
    "Rotorua",
    "Taupo",
    "Whanganui",
    "Tauranga",
)


def sort_client_branches(names: set[str] | list[str]) -> list[str]:
    """Stable branch dropdown order — only confirmed client locations."""
    allowed = set(names)
    return [b for b in CLIENT_BRANCHES if b in allowed]


# Location code prefix -> branch name (from branch litres sheets + Cars+ codes)
LOC_TO_BRANCH: dict[str, str] = {
    "TUO": "Taupo",
    "TUZ": "Taupo",
    "KKE": "Kerikeri",
    "KKZ": "Kerikeri",
    "WHN": "Whangarei",
    "WZZ": "Whangarei",
    "WNU": "Whanganui",
    "WJZ": "Whanganui",
    "RTR": "Rotorua",
    "RTZ": "Rotorua",
    "TRG": "Tauranga",
    "TRZ": "Tauranga",
}


# Branch name -> short tab label on branch litres workbook
BRANCH_TAB_CODE: dict[str, str] = {
    "Taupo": "TUO",
    "Kerikeri": "KKE",
    "Whangarei": "WHN",
    "Whanganui": "WNU",
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


def branch_from_cars_locations(ra_loc_out: str, ra_loc_in: str = "") -> str | None:
    """Return a client branch if either Cars+ location belongs to one."""
    return branch_from_loc(ra_loc_out) or branch_from_loc(ra_loc_in)


# Cars+ location prefixes that count as client branch locations.
BRANCH_CARS_LOC_PREFIXES: dict[str, tuple[str, ...]] = {
    "Taupo": ("TUO", "TUZ"),
    "Kerikeri": ("KKE", "KKZ"),
    "Whangarei": ("WHN", "WZZ"),
    "Whanganui": ("WNU", "WJZ"),
    "Rotorua": ("RTR", "RTZ"),
    "Tauranga": ("TRG", "TRZ"),
}


def cars_loc_prefixes(branch: str) -> tuple[str, ...]:
    return BRANCH_CARS_LOC_PREFIXES.get(branch, (branch_tab_code(branch),))


# Plain-language labels for PDF / UI (not raw codes only)
BRANCH_CARS_LOC_LABEL: dict[str, str] = {
    "Whangarei": "Whangarei (Cars+ WHN50/60 & WZZ52)",
    "Whanganui": "Whanganui/Wanganui (Cars+ WNU/WJZ)",
    "Taupo": "Taupo (Cars+ TUO/TUZ)",
    "Kerikeri": "Kerikeri (Cars+ codes KKE & KKZ)",
    "Rotorua": "Rotorua Te Ngae (Cars+ RTR/RTZ)",
    "Tauranga": "Mount Maunganui / Tauranga - Z Hewletts Rd (Cars+ TRG/TRZ)",
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
            "Whanganui/Wanganui on Cars+: WNU/WJZ. "
            "WHN/WZZ codes are Whangarei, not Whanganui."
        )
    prefixes = ", ".join(cars_loc_prefixes(branch))
    return f"Cars+ RA Loc Out or In must start with: {prefixes} for this branch."


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
