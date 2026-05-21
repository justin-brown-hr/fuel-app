"""Detect fuel credit rows that are excluded from litre matching."""

import re

_CREDIT_KEYWORDS = re.compile(
    r"credit|rebate|refund|payment|reversal|adjustment",
    re.IGNORECASE,
)


def is_credit_litres(
    litres: float,
    *,
    product: str = "",
    fuel_type: str = "",
    supplier: str = "",
) -> bool:
    """
    Client rule: credit fuel litres do not need to match.
    Negative litres or credit-related descriptions are skipped.
    """
    if litres < 0:
        return True
    text = " ".join((product, fuel_type, supplier)).strip()
    return bool(text and _CREDIT_KEYWORDS.search(text))
