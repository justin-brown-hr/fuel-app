import re
from pathlib import Path

import pdfplumber

from src.models import FuelStatementRow

from .utils import parse_excel_date, safe_float

_MOBIL_LINE = re.compile(
    r"^(\d{2}/\d{2}/\d{2})\s+(\d{1,2}:\d{2})\s+(.+?)\s+\d+\s+"
    r"(\d+(?:\.\d+)?)\s*L\s+",
    re.IGNORECASE,
)

_MOBIL_CARD = re.compile(r"NAME:\s*(HERTZ\s+[\w\s\d]+)", re.IGNORECASE)

_FARMLANDS_HEADER = re.compile(
    r"^(\d{2}\s+\w{3}\s+\d{2})\s+\d+\s+Inv:.*?(Caltex\s+.+?)\s*$",
    re.IGNORECASE,
)

_FARMLANDS_CRD_HEADER = re.compile(
    r"^(\d{2}\s+\w{3}\s+\d{2})\s+\d+\s+Crd:\s*\d+\s+(Caltex\s+.+?)\s*$",
    re.IGNORECASE,
)


_FARMLANDS_LITRES = re.compile(
    r"(-?\d+(?:\.\d+)?)\s*L\s+(.+?)\s+(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_BRANCH_FROM_SUPPLIER = {
    "kerikeri": "Kerikeri",
    "whangarei": "Whangarei",
    "whanganui": "Whanganui",
    "taupo": "Taupo",
    "rotorua": "Rotorua",
    "tauranga": "Tauranga",
    "napier": "Napier",
    "auckland": "Auckland",
    "hamilton": "Hamilton",
    "wellington": "Wellington",
}


def _branch_from_text(text: str) -> str:
    lower = text.lower()
    for key, branch in _BRANCH_FROM_SUPPLIER.items():
        if key in lower:
            return branch
    m = re.search(r"hertz\s+(\w+)", lower)
    if m:
        return m.group(1).title()
    return "Other"


def _parse_farmlands(text: str) -> list[FuelStatementRow]:
    rows: list[FuelStatementRow] = []
    pending_date = None
    pending_supplier = None

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        hm = _FARMLANDS_HEADER.match(line)
        if hm:
            pending_date = parse_excel_date(hm.group(1))
            pending_supplier = hm.group(2).strip()
            continue
        cm = _FARMLANDS_CRD_HEADER.match(line)
        if cm:
            pending_date = parse_excel_date(cm.group(1))
            pending_supplier = cm.group(2).strip()
            continue
        if pending_date and pending_supplier:
            lm = _FARMLANDS_LITRES.search(line)
            if lm:
                litres = float(lm.group(1))
                product = lm.group(2).strip()
                rows.append(
                    FuelStatementRow(
                        branch=_branch_from_text(pending_supplier),
                        transaction_date=pending_date,
                        time=None,
                        supplier=pending_supplier,
                        litres=litres,
                        product=product,
                        total_incl_gst=safe_float(lm.group(3)),
                        card_or_invoice="",
                    )
                )
                pending_date = None
                pending_supplier = None
    return rows


def _parse_mobil(text: str) -> list[FuelStatementRow]:
    rows: list[FuelStatementRow] = []
    current_vehicle = ""
    for vm in _MOBIL_CARD.finditer(text):
        current_vehicle = vm.group(1).strip()

    for line in text.splitlines():
        line = line.strip()
        m = _MOBIL_LINE.match(line)
        if not m:
            continue
        tx_date = parse_excel_date(m.group(1))
        if tx_date is None:
            continue
        supplier = m.group(3).strip()
        litres = float(m.group(4))
        branch = _branch_from_text(current_vehicle or supplier)
        rows.append(
            FuelStatementRow(
                branch=branch,
                transaction_date=tx_date,
                time=m.group(2),
                supplier=supplier,
                litres=litres,
                product="",
                total_incl_gst=None,
                card_or_invoice="",
                vehicle_name=current_vehicle or None,
            )
        )
    return rows


def _detect_format(text: str) -> str:
    if "Farmlands Statement" in text or "Farmlands Co-operative" in text:
        return "farmlands"
    if "Mobil Oil" in text or "Mobilcard" in text:
        return "mobil"
    return "unknown"


def import_fuel_statement(path: Path) -> list[FuelStatementRow]:
    suffix = path.suffix.lower()
    if suffix in (".xlsx", ".xls"):
        import pandas as pd

        df = pd.read_excel(path, header=0)
        rows: list[FuelStatementRow] = []
        for _, r in df.iterrows():
            litres = safe_float(r.get("litres") or r.get("Litres"))
            if litres is None or litres <= 0:
                continue
            tx_date = parse_excel_date(r.get("date") or r.iloc[0])
            if tx_date is None:
                continue
            rows.append(
                FuelStatementRow(
                    branch=str(r.get("branch", "Other")),
                    transaction_date=tx_date,
                    time=None,
                    supplier=str(r.get("supplier", "")),
                    litres=litres,
                    product="",
                    total_incl_gst=safe_float(r.get("total")),
                    card_or_invoice="",
                )
            )
        return rows

    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    full_text = "\n".join(text_parts)
    fmt = _detect_format(full_text)
    if fmt == "farmlands":
        return _parse_farmlands(full_text)
    if fmt == "mobil":
        return _parse_mobil(full_text)
    return _parse_farmlands(full_text) + _parse_mobil(full_text)
