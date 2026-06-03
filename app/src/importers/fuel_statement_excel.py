"""Import fuel statements from Excel (any layout with detectable columns)."""

import re
from pathlib import Path

import pandas as pd

from src.config import CLIENT_BRANCHES
from src.models import FuelStatementRow

from .fuel_statement import _branch_from_text, _client_rows
from .utils import normalize_ra, open_data_file, parse_excel_date, parse_time, safe_float


def _norm_col(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name).lower())


def _find_col(col_map: dict[str, str], *candidates: str) -> str | None:
    for key in candidates:
        nk = _norm_col(key)
        if nk in col_map:
            return col_map[nk]
    for nk, original in col_map.items():
        for part in candidates:
            p = _norm_col(part)
            if len(p) < 4:
                continue
            if p in nk or nk in p:
                return original
    return None


def _branch_from_filename(path: Path) -> str | None:
    name = path.stem.lower()
    for branch in CLIENT_BRANCHES:
        if branch.lower() in name:
            return branch
    return _branch_from_text(name)


def _branch_from_row(
    row: pd.Series,
    branch_col: str | None,
    default_branch: str | None,
) -> str:
    if branch_col:
        text = str(row.get(branch_col, "") or "").strip()
        b = _branch_from_text(text)
        if b != "Other":
            return b
        if text and text.title() in CLIENT_BRANCHES:
            return text.title()
    if default_branch:
        return default_branch
    return "Other"


def _supplier_label(path: Path, branch: str) -> str:
    lower = path.stem.lower()
    if "tank" in lower or "branch" in lower or "customa" in lower:
        return f"Branch tank ({branch})"
    return f"Fuel statement ({branch})"


def _read_sheet(
    df: pd.DataFrame,
    path: Path,
    default_branch: str | None,
) -> list[FuelStatementRow]:
    if df.empty or len(df.columns) < 2:
        return []

    # Use first row as header when it looks like labels (not all numeric).
    header_row = 0
    first = df.iloc[0]
    if first.astype(str).str.contains(r"litre|fill|date|time|location|fuel", case=False, regex=True).any():
        df = df.copy()
        df.columns = [str(c).strip() for c in first.tolist()]
        df = df.iloc[1:].reset_index(drop=True)
    else:
        df.columns = [str(c).strip() for c in df.columns]

    col_map = {_norm_col(c): c for c in df.columns}

    litres_col = _find_col(
        col_map,
        "filltotal",
        "fuelcount",
        "litres",
        "liters",
        "volume",
        "quantity",
        "qty",
        "fill",
    )
    date_col = _find_col(
        col_map,
        "timestamp",
        "transactiondate",
        "datetime",
        "datein",
        "date",
        "filldate",
        "txdate",
    )
    branch_col = _find_col(
        col_map,
        "locationname",
        "orgname",
        "systemname",
        "location",
        "branch",
        "sitename",
        "depot",
    )
    product_col = _find_col(col_map, "itemname", "fueltype", "product", "itemabbr")
    vehicle_col = _find_col(
        col_map, "customa", "rego", "vehicle", "equipmentname", "equipment", "assetno"
    )
    ra_col = _find_col(col_map, "ranumber", "tokennumber", "contract")
    time_col = _find_col(col_map, "timein", "timeofday")
    if not time_col and date_col and _norm_col(date_col) == "timestamp":
        time_col = date_col
    total_col = _find_col(col_map, "totalinclgst", "totalamount", "totalcost")

    if not litres_col:
        return []

    rows: list[FuelStatementRow] = []
    for _, r in df.iterrows():
        litres = safe_float(r.get(litres_col))
        if litres is None or litres <= 0:
            continue
        raw_dt = r.get(date_col) if date_col else None
        tx_date = parse_excel_date(raw_dt) if date_col else None
        if tx_date is None:
            continue
        tx_time = None
        if isinstance(raw_dt, pd.Timestamp):
            tx_time = raw_dt.strftime("%H:%M")
        branch = _branch_from_row(r, branch_col, default_branch)
        if branch not in CLIENT_BRANCHES:
            continue
        ra = normalize_ra(r.get(ra_col)) if ra_col else ""
        if ra in ("NAN", "NONE", ""):
            ra = ""
        vehicle = str(r.get(vehicle_col, "") or "").strip() if vehicle_col else ""
        if vehicle.lower() in ("nan", "blank", "no rego"):
            vehicle = ""
        product = str(r.get(product_col, "") or "").strip() if product_col else ""
        if time_col and time_col != date_col:
            tx_time = parse_time(r.get(time_col)) or tx_time
        rows.append(
            FuelStatementRow(
                branch=branch,
                transaction_date=tx_date,
                time=tx_time,
                supplier=_supplier_label(path, branch),
                litres=litres,
                product=product,
                total_incl_gst=safe_float(r.get(total_col)) if total_col else None,
                card_or_invoice="",
                vehicle_name=vehicle or None,
                ra_number=ra or None,
            )
        )
    return rows


def import_fuel_statement_excel(path: Path) -> list[FuelStatementRow]:
    """Parse Excel fuel exports (branch tank, card export, generic)."""
    read_path = open_data_file(path)
    default_branch = _branch_from_filename(path)
    all_rows: list[FuelStatementRow] = []

    xl = pd.ExcelFile(read_path)
    for sheet in xl.sheet_names:
        df = pd.read_excel(read_path, sheet_name=sheet, header=None)
        all_rows.extend(_read_sheet(df, path, default_branch))

    return _client_rows(all_rows)
