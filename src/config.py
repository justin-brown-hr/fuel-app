from pathlib import Path

APP_NAME = "Fuel Reconcile"
APP_VERSION = "0.1.0"

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = PROJECT_ROOT / "docs"
DATA_DIR = PROJECT_ROOT / "data"
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
