"""Normalize fuel product names for matching."""

import re


def normalize_fuel_type(product: str) -> str:
    if not product:
        return ""
    p = product.strip()
    if re.search(r"\b91\b", p, re.I) or "unleaded" in p.lower():
        return "91"
    if "diesel" in p.lower():
        return "Diesel"
    return p
