"""Stable keys for attention items (manual accept / PDF filtering)."""

from typing import Any


def attention_item_key(row: dict[str, Any]) -> str:
    """Unique key per follow-up row within a batch + branch."""
    stage = str(row.get("stage") or row.get("source") or "")
    source = str(row.get("source") or "")
    ra = str(row.get("ra_number") or "").strip()
    dt = str(row.get("transaction_date") or "")
    try:
        litres = round(float(row.get("litres", 0)), 2)
    except (TypeError, ValueError):
        litres = 0.0
    extra = str(row.get("fuel_type") or row.get("supplier") or "").strip()
    return f"{stage}|{source}|{dt}|{litres}|{ra}|{extra}"
