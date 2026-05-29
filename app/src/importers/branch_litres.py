from pathlib import Path

import pandas as pd

from src.models import BranchLitresRow

from .utils import normalize_ra, parse_excel_date, parse_time, safe_float


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
}

_BRANCH_PARSERS = {
    "Taupo": _parse_taupo_sheet,
    "Kerikeri": _parse_kerikeri_sheet,
    "Whangarei": _parse_whangarei_sheet,
    "Whanganui": _parse_whangarei_sheet,
    "Rotorua": _parse_kerikeri_sheet,
    "Tauranga": _parse_kerikeri_sheet,
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
        parser = _BRANCH_PARSERS[branch]
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        all_rows.extend(parser(df, branch))
    return all_rows
