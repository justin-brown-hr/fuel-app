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


_PARSERS = {
    "Taupo": _parse_taupo_sheet,
    "Kerikeri": _parse_kerikeri_sheet,
    "Whangarei": _parse_whangarei_sheet,
}


def import_branch_litres(path: Path) -> list[BranchLitresRow]:
    xl = pd.ExcelFile(path)
    all_rows: list[BranchLitresRow] = []
    for sheet in xl.sheet_names:
        parser = _PARSERS.get(sheet)
        if parser is None:
            continue
        df = pd.read_excel(path, sheet_name=sheet, header=None)
        all_rows.extend(parser(df, sheet))
    return all_rows
