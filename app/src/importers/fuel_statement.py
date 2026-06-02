import re
from pathlib import Path

import pdfplumber

from src.models import FuelStatementRow
from src.config import CLIENT_BRANCHES

from .utils import parse_excel_date, safe_float

_MOBIL_LINE = re.compile(
    r"^(\d{2}/\d{2}/\d{2})\s+(\d{1,2}:\d{2})\s+(.+?)\s+\d+\s+"
    r"(\d+(?:\.\d+)?)\s*L\s+",
    re.IGNORECASE,
)

_MOBIL_CARD = re.compile(r"NAME:\s*(HERTZ\s+[\w\s\d]+)", re.IGNORECASE)

_FARMLANDS_HEADER = re.compile(
    r"^(\d{2}\s+\w{3}\s+\d{2})\s+\d+\s+Inv:\s*\d+\s+(.+?)\s*$",
    re.IGNORECASE,
)

_FARMLANDS_CRD_HEADER = re.compile(
    r"^(\d{2}\s+\w{3}\s+\d{2})\s+\d+\s+Crd:\s*\d+\s+(.+?)\s*$",
    re.IGNORECASE,
)

# Farmlands detail line: product code, litres, product name, amounts…
_FARMLANDS_LITRES = re.compile(
    r"^\d{4}\s+(-?\d+(?:\.\d+)?)\s*L\s+(.+?)\s+(-?\d+(?:\.\d+)?)",
    re.IGNORECASE,
)

_BRANCH_FROM_SUPPLIER = {
    "kerikeri": "Kerikeri",
    "whangārei": "Whangarei",
    "whangarei": "Whangarei",
    "wanganui": "Whanganui",
    "whanganui": "Whanganui",
    "taupō": "Taupo",
    "taupo": "Taupo",
    "te ngae": "Rotorua",
    "te ngāe": "Rotorua",
    "rotorua": "Rotorua",
    "mt maunganui": "Tauranga",
    "mount maunganui": "Tauranga",
    "hewletts": "Tauranga",
    "tauranga": "Tauranga",
    "new plymouth": "New Plymouth",
    "np ": "New Plymouth",
    "whakatane": "Whakatane",
    "whk": "Whakatane",
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


def _client_rows(rows: list[FuelStatementRow]) -> list[FuelStatementRow]:
    return [r for r in rows if r.branch in CLIENT_BRANCHES]


def _append_farmlands_row(
    rows: list[FuelStatementRow],
    tx_date,
    supplier: str,
    litres: float,
    product: str,
    total_incl_gst,
) -> None:
    if tx_date is None or not supplier:
        return
    rows.append(
        FuelStatementRow(
            branch=_branch_from_text(supplier),
            transaction_date=tx_date,
            time=None,
            supplier=supplier,
            litres=litres,
            product=product,
            total_incl_gst=total_incl_gst,
            card_or_invoice="",
        )
    )


def _parse_farmlands(text: str) -> list[FuelStatementRow]:
    """
    Farmlands PDFs use two layouts:
    - Caltex branches: dated Inv header, then card line, then litres line.
    - Tauranga (Z Hewletts): site name, card, litres line, then dated Inv header.
    """
    rows: list[FuelStatementRow] = []
    pending_date = None
    pending_supplier = None
    # Litres line seen before its dated Inv line (common for Z Hewletts Rd).
    deferred_litres: tuple[float, str, float | None] | None = None

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("Card number"):
            continue

        hm = _FARMLANDS_HEADER.match(line)
        cm = _FARMLANDS_CRD_HEADER.match(line) if not hm else None
        if hm or cm:
            m = hm or cm
            tx_date = parse_excel_date(m.group(1))
            supplier = m.group(2).strip()
            if deferred_litres:
                litres, product, total = deferred_litres
                _append_farmlands_row(rows, tx_date, supplier, litres, product, total)
                deferred_litres = None
            else:
                pending_date = tx_date
                pending_supplier = supplier
            continue

        lm = _FARMLANDS_LITRES.match(line)
        if not lm:
            continue
        litres = float(lm.group(1))
        product = lm.group(2).strip()
        total = safe_float(lm.group(3))
        if pending_date and pending_supplier:
            _append_farmlands_row(
                rows, pending_date, pending_supplier, litres, product, total
            )
            pending_date = None
            pending_supplier = None
        else:
            deferred_litres = (litres, product, total)

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
        return _client_rows(rows)

    text_parts: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text()
            if t:
                text_parts.append(t)
    full_text = "\n".join(text_parts)
    fmt = _detect_format(full_text)
    if fmt == "farmlands":
        return _client_rows(_parse_farmlands(full_text))
    if fmt == "mobil":
        return _client_rows(_parse_mobil(full_text))
    return _client_rows(_parse_farmlands(full_text) + _parse_mobil(full_text))
