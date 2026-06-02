from pathlib import Path

import pandas as pd

from src.models import BranchLitresRow

from .utils import normalize_ra, parse_excel_date, parse_time, safe_float


def _is_new_simple_format(df: pd.DataFrame) -> bool:
    """
    New client format (May): two columns with header row:
      RA Number | Fuel Litres
    """
    if df.shape[1] < 2:
        return False
    a = str(df.iloc[0, 0] or "").strip().lower()
    b = str(df.iloc[0, 1] or "").strip().lower()
    return a in {"ra number", "ra"} and "litre" in b


def _parse_simple_two_col(df: pd.DataFrame, branch: str) -> list[BranchLitresRow]:
    rows: list[BranchLitresRow] = []
    # Expect header row at index 0
    for i in range(1, len(df.index)):
        ra_raw = str(df.iloc[i, 0] or "").strip()
        litres = safe_float(df.iloc[i, 1])
        if not ra_raw and litres is None:
            continue
        if litres is None or litres <= 0:
            continue
        ra_norm = normalize_ra(ra_raw)
        upper = ra_raw.upper()
        is_nonrev = upper.startswith("NR") or "NONREV" in upper
        rows.append(
            BranchLitresRow(
                branch=branch,
                vehicle_label="",
                ra_number=("NONREV" if is_nonrev else (ra_norm or ra_raw)),
                transaction_date=None,
                litres=litres,
                time=None,
                amount=None,
                day_of_month=None,
                is_nonrev=is_nonrev,
            )
        )
    return rows


def _parse_taupo_sheet(df: pd.DataFrame, branch: str) -> list[BranchLitresRow]:
    rows: list[BranchLitresRow] = []
    for _, r in df.iterrows():
        litres = safe_float(r.iloc[4])
        if litres is None or litres <= 0:
            continue
        tx_date = parse_excel_date(r.iloc[5])
        if tx_date is None:
            continue
        ra = normalize_ra(r.iloc[2])
        if not ra or not ra[0].isdigit():
            ra = normalize_ra(r.iloc[0])
        rows.append(
            BranchLitresRow(
                branch=branch,
                vehicle_label=str(r.iloc[0] or "").strip(),
                ra_number=ra or str(r.iloc[0] or "").strip(),
                transaction_date=tx_date,
                litres=litres,
                time=parse_time(r.iloc[6]),
                day_of_month=int(r.iloc[3]) if safe_float(r.iloc[3]) else None,
            )
        )
    return rows


def _parse_kerikeri_sheet(df: pd.DataFrame, branch: str) -> list[BranchLitresRow]:
    rows: list[BranchLitresRow] = []
    for _, r in df.iterrows():
        litres = safe_float(r.iloc[2])
        amount = safe_float(r.iloc[3])
        if litres is None or litres <= 0:
            continue
        tx_date = parse_excel_date(r.iloc[5])
        if tx_date is None:
            continue
        ra = normalize_ra(r.iloc[0])
        rows.append(
            BranchLitresRow(
                branch=branch,
                vehicle_label="",
                ra_number=ra,
                transaction_date=tx_date,
                litres=litres,
                time=parse_time(r.iloc[4]),
                amount=amount,
            )
        )
    return rows


def _parse_whangarei_sheet(df: pd.DataFrame, branch: str) -> list[BranchLitresRow]:
    rows: list[BranchLitresRow] = []
    for _, r in df.iterrows():
        litres = safe_float(r.iloc[2])
        amount = safe_float(r.iloc[3])
        if litres is None or litres <= 0:
            continue
        tx_date = parse_excel_date(r.iloc[6])
        if tx_date is None:
            continue
        col4 = str(r.iloc[4] or "").strip()
        is_nonrev = "NONREV" in col4.upper()
        ra = "" if is_nonrev else normalize_ra(r.iloc[4])
        rows.append(
            BranchLitresRow(
                branch=branch,
                vehicle_label=str(r.iloc[0] or "").strip(),
                ra_number=ra if ra else ("NONREV" if is_nonrev else ""),
                transaction_date=tx_date,
                litres=litres,
                time=parse_time(r.iloc[5]),
                amount=amount,
                is_nonrev=is_nonrev,
            )
        )
    return rows


# Excel tab name (any alias) -> canonical branch name
SHEET_TO_BRANCH: dict[str, str] = {
    "Taupo": "Taupo",
    "Kerikeri": "Kerikeri",
    "Whangarei": "Whangarei",
    "Whanganui": "Whanganui",
    "Wanganui": "Whanganui",
    "Rotorua": "Rotorua",
    "Te Ngae": "Rotorua",
    "Tauranga": "Tauranga",
    "Mt Maunganui": "Tauranga",
    "Mount Maunganui": "Tauranga",
    "Z Hewletts Rd": "Tauranga",
    "Z Hewletts": "Tauranga",
    "New Plymouth": "New Plymouth",
    "Whakatane": "Whakatane",
}

_BRANCH_PARSERS = {
    "Taupo": _parse_taupo_sheet,
    "Kerikeri": _parse_kerikeri_sheet,
    "Whangarei": _parse_whangarei_sheet,
    "Whanganui": _parse_whangarei_sheet,
    "Rotorua": _parse_kerikeri_sheet,
    "Tauranga": _parse_kerikeri_sheet,
    # Legacy layouts if provided; May format is auto-detected.
    "New Plymouth": _parse_kerikeri_sheet,
    "Whakatane": _parse_kerikeri_sheet,
}


def _canonical_branch_from_sheet(sheet_name: str) -> str | None:
    name = sheet_name.strip()
    if name in _BRANCH_PARSERS:
        return name
    if name in SHEET_TO_BRANCH:
        return SHEET_TO_BRANCH[name]
    lower = name.lower()
    for key, branch in SHEET_TO_BRANCH.items():
        if key.lower() == lower:
            return branch
    return None


def import_branch_litres(path: Path) -> list[BranchLitresRow]:
    xl = pd.ExcelFile(path)
    all_rows: list[BranchLitresRow] = []
    for sheet in xl.sheet_names:
        branch = _canonical_branch_from_sheet(sheet)
        if branch is None:
            continue
        # Read once without headers to detect the format.
        raw = pd.read_excel(path, sheet_name=sheet, header=None)
        if _is_new_simple_format(raw):
            all_rows.extend(_parse_simple_two_col(raw, branch))
            continue
        parser = _BRANCH_PARSERS[branch]
        all_rows.extend(parser(raw, branch))
    return all_rows
