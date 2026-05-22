from pathlib import Path

import pandas as pd

from src.config import branch_from_loc
from src.models import CarsPlusRow

from .utils import normalize_ra, open_data_file, parse_excel_date, parse_time, safe_float


def _find_column(col_map: dict[str, str], *candidates: str) -> str | None:
    for name in candidates:
        key = name.lower()
        if key in col_map:
            return col_map[key]
    for key, original in col_map.items():
        for part in candidates:
            if part.lower() in key:
                return original
    return None


def import_cars_plus(path: Path) -> list[CarsPlusRow]:
    read_path = open_data_file(path)
    df = pd.read_excel(read_path, sheet_name=0, header=0)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}

    loc_out = _find_column(
        col_map,
        "ra loc out",
        "ra loc",
        "loc out",
        "location out",
        "location",
        "out loc",
    )
    loc_in = _find_column(col_map, "ra loc in", "loc in", "location in")
    ra_col = _find_column(col_map, "ra number", "ra", "ra #", "rental agreement", "contract")
    date_col = _find_column(
        col_map, "date in", "date out", "date", "checkout date", "check out date"
    )
    time_col = _find_column(col_map, "time in", "time", "time out")
    charge_col = _find_column(
        col_map,
        "fuel charges",
        "fuel charge",
        "fuel chg",
        "fuel",
        "charge",
    )
    type_col = _find_column(col_map, "fuel type", "fuel", "product")

    if not loc_out or not ra_col or not date_col:
        raise ValueError(
            f"Cars+ columns not found. Need location, RA, and date. "
            f"Found columns: {', '.join(df.columns[:12])}..."
        )
    if not charge_col:
        raise ValueError(
            f"Cars+ fuel charge column not found. Columns: {', '.join(df.columns[:12])}..."
        )

    rows: list[CarsPlusRow] = []
    for _, r in df.iterrows():
        loc = str(r.get(loc_out, "") if loc_out else "").strip()
        if not loc or loc.lower().startswith("ra loc"):
            continue
        branch = branch_from_loc(loc) or "Other"
        ra = normalize_ra(r.get(ra_col) if ra_col else "")
        if not ra:
            continue
        tx_date = parse_excel_date(r.get(date_col) if date_col else None)
        if tx_date is None:
            continue
        charge = safe_float(r.get(charge_col) if charge_col else None)
        if charge is None:
            continue
        fuel_type = ""
        if type_col and type_col != charge_col:
            fuel_type = str(r.get(type_col, "") or "").strip()
        rows.append(
            CarsPlusRow(
                branch=branch,
                ra_loc_out=loc,
                ra_loc_in=str(r.get(loc_in, loc) if loc_in else loc).strip(),
                ra_number=ra,
                transaction_date=tx_date,
                time=parse_time(r.get(time_col) if time_col else None) or "",
                fuel_charge=charge,
                fuel_type=fuel_type,
            )
        )
    return rows
