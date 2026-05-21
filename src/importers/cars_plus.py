from pathlib import Path

import pandas as pd

from src.config import branch_from_loc
from src.models import CarsPlusRow

from .utils import normalize_ra, parse_excel_date, parse_time, safe_float


def import_cars_plus(path: Path) -> list[CarsPlusRow]:
    df = pd.read_excel(path, sheet_name=0, header=0)
    df.columns = [str(c).strip() for c in df.columns]
    col_map = {c.lower(): c for c in df.columns}

    def col(*names: str) -> str | None:
        for n in names:
            key = n.lower()
            if key in col_map:
                return col_map[key]
        return None

    loc_out = col("ra loc out", "ra loc")
    loc_in = col("ra loc in")
    ra_col = col("ra number", "ra")
    date_col = col("date in", "date")
    time_col = col("time in", "time")
    charge_col = col("fuel charges", "fuel charge")
    type_col = col("fuel", "fuel type")

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
        rows.append(
            CarsPlusRow(
                branch=branch,
                ra_loc_out=loc,
                ra_loc_in=str(r.get(loc_in, loc) if loc_in else loc).strip(),
                ra_number=ra,
                transaction_date=tx_date,
                time=parse_time(r.get(time_col) if time_col else None) or "",
                fuel_charge=charge,
                fuel_type=str(r.get(type_col, "") if type_col else "").strip(),
            )
        )
    return rows
