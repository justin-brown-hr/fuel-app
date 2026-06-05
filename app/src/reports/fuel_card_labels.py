"""Branch-aware labels for Farmlands/Caltex vs Mobil fuel card statements."""

from typing import Any


def _statement_suppliers(report: dict[str, Any]) -> list[str]:
    return [
        (r.get("supplier") or "").lower()
        for r in report.get("statement", [])
        if r.get("supplier")
    ]


def fuel_card_label_for_branch(report: dict[str, Any]) -> str:
    """
    Name shown in summaries for the fuel card source at this branch.
    Taupo uses Mobil; most other branches use Farmlands/Caltex.
    """
    suppliers = _statement_suppliers(report)
    if not suppliers:
        return "fuel card"

    mobil = sum(1 for s in suppliers if "mobil" in s)
    caltex = sum(1 for s in suppliers if "caltex" in s or "farmlands" in s)
    tank = sum(1 for s in suppliers if "branch tank" in s)

    if tank and caltex:
        return "Farmlands + branch tank"
    if tank and mobil:
        return "Mobil + branch tank"
    if tank and not caltex and not mobil:
        return "branch tank"
    if mobil and not caltex:
        return "Mobil"
    if caltex and not mobil:
        return "Caltex/Farmlands"
    if mobil and caltex:
        return "fuel card"
    return "fuel card"


def statement_source_summary(report: dict[str, Any]) -> str:
    """Plain breakdown of imported statement lines for this branch."""
    rows = report.get("statement") or []
    if not rows:
        return ""
    caltex = sum(
        1
        for r in rows
        if "caltex" in (r.get("supplier") or "").lower()
        or "farmlands" in (r.get("supplier") or "").lower()
    )
    mobil = sum(1 for r in rows if "mobil" in (r.get("supplier") or "").lower())
    tank = sum(1 for r in rows if "branch tank" in (r.get("supplier") or "").lower())
    parts: list[str] = []
    if caltex:
        parts.append(f"{caltex} Farmlands/Caltex")
    if mobil:
        parts.append(f"{mobil} Mobil")
    if tank:
        parts.append(f"{tank} branch tank")
    return " + ".join(parts)


def card_not_on_tab_summary_text(report: dict[str, Any], count: int) -> str:
    source = fuel_card_label_for_branch(report)
    return (
        f"<b>{count}</b> fuel card line(s) — on <b>{source}</b>, not on branch tab "
        f"(add to spreadsheet or investigate)"
    )


def tab_not_on_card_summary_text(report: dict[str, Any], count: int) -> str:
    source = fuel_card_label_for_branch(report)
    if source == "fuel card":
        line = "no matching fuel card line"
    else:
        line = f"no matching {source} card line"
    return f"<b>{count}</b> branch tab row(s) — on branch sheet, {line}"


def card_not_on_tab_action(report: dict[str, Any]) -> str:
    source = fuel_card_label_for_branch(report)
    if source == "fuel card":
        return "On fuel card; not on branch tab"
    return f"On {source}; not on branch tab"


def tab_not_on_card_action(report: dict[str, Any]) -> str:
    source = fuel_card_label_for_branch(report)
    if source == "fuel card":
        return "On branch tab; no matching fuel card line"
    return f"On branch tab; no matching {source} card line"
