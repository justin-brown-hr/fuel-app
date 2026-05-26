"""Filter reconciliation output to items that need follow-up."""

from typing import Any

from src.attention_keys import attention_item_key
from src.config import cars_loc_label
from src.matching.cars_reconcile import CARS_DATE_WINDOW_DAYS
from src.reports.cars_plus_note import cars_section_empty_note


def _is_credit_row(row: dict) -> bool:
    if row.get("is_credit"):
        return True
    try:
        return float(row.get("litres", 0)) < 0
    except (TypeError, ValueError):
        return False


def _override_keys(report: dict[str, Any]) -> set[str]:
    return set(report.get("attention_override_keys") or [])


def _visible(row: dict, overrides: set[str]) -> bool:
    return attention_item_key(row) not in overrides


def extract_attention_items(report: dict[str, Any]) -> dict[str, Any]:
    """
    Actionable items only (excludes manual accepts):
    - Card line with no matching litres on branch tab (Stage 1 genuine gap)
    - Operational branch row with no matching card line
    - Operational branch RA with no Cars+ charge within date window
    """
    overrides = _override_keys(report)
    card_not_on_tab = [
        r
        for r in report.get("unmatched_statement_stage1", [])
        if not _is_credit_row(r) and _visible(r, overrides)
    ]
    tab_not_on_card = [
        r
        for r in report.get("unmatched_branch", [])
        if not r.get("is_nonrev") and not _is_credit_row(r) and _visible(r, overrides)
    ]
    cars_not_charged = [
        r
        for r in report.get("unmatched_cars_plus", [])
        if _visible(r, overrides)
    ]

    credit_count = sum(
        1
        for r in report.get("unmatched_statement_stage1", [])
        if _is_credit_row(r)
    )
    override_count = len(overrides)

    return {
        "card_not_on_tab": card_not_on_tab,
        "tab_not_on_card": tab_not_on_card,
        "cars_not_charged": cars_not_charged,
        "credit_reversal_count": credit_count,
        "manual_accept_count": override_count,
        "total_action_items": (
            len(card_not_on_tab) + len(tab_not_on_card) + len(cars_not_charged)
        ),
    }


def attention_summary_bullets(report: dict[str, Any]) -> list[str]:
    """Summary bullet lines (HTML <b> for PDF; same counts as client report layout)."""
    branch = report.get("branch", "Unknown")
    s1 = report.get("summary", {}).get("stage1", {})
    att = extract_attention_items(report)
    matched = s1.get("matched_count", 0)
    total = s1.get("statement_total", 0)
    n_card = len(att["card_not_on_tab"])
    n_tab = len(att["tab_not_on_card"])
    n_cars = len(att["cars_not_charged"])
    n_cred = att["credit_reversal_count"]
    loc = cars_loc_label(branch)

    bullets = [
        (
            f"<b>{matched}</b> of <b>{total}</b> card fill-ups match the branch tab "
            f"(incl. NONREV). Tables below list only follow-ups."
        ),
        (
            f"<b>{n_card}</b> fuel card line(s) — on Farmlands, not on branch tab "
            f"(add to spreadsheet or investigate)"
        ),
        (
            f"<b>{n_tab}</b> branch tab row(s) — on branch sheet, no matching card line"
        ),
        (
            f"<b>{n_cars}</b> operational fill(s) — no Cars+ RA match within "
            f"<b>{CARS_DATE_WINDOW_DAYS} days</b> "
            f"({loc} or another confirmed client location)"
        ),
        (
            f"<b>{n_cred}</b> credit reversal(s) on statement "
            f"(informational — no action)"
        ),
    ]

    cars_total = report.get("cars_plus_imported_total", 0)
    if cars_total == 0:
        bullets[3] = (
            "<b>Cars+</b> — file not loaded (re-import; copy spreadsheet off OneDrive "
            "if locked)"
        )
    elif n_cars == 0:
        note = cars_section_empty_note(report)
        if note:
            bullets[3] = f"<b>0</b> Cars+ billing gaps — {note}"

    return bullets


def format_attention_summary_text(report: dict[str, Any]) -> str:
    branch = report.get("branch", "Unknown")
    lines = [f"### {branch} — Items needing attention", ""]
    for b in attention_summary_bullets(report):
        plain = b.replace("<b>", "**").replace("</b>", "**").replace("&amp;", "&")
        lines.append(f"* {plain}")
    att = extract_attention_items(report)
    if att.get("manual_accept_count"):
        lines.append(
            f"* <b>{att['manual_accept_count']}</b> item(s) manually accepted "
            f"(hidden from this report)"
        )
    if att["total_action_items"] == 0:
        lines.append("* No action items — reconciliation clean for this branch.")
    return "\n".join(lines)


def attention_rows_for_table(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Flat rows for UI: category, date, litres, detail, action."""
    att = extract_attention_items(report)
    rows: list[dict[str, Any]] = []
    for r in att["card_not_on_tab"]:
        rows.append(
            {
                "item_key": attention_item_key(r),
                "category": "Card → tab",
                "transaction_date": r["transaction_date"],
                "litres": r["litres"],
                "detail": r.get("fuel_type") or "",
                "action": "Add to branch tab or investigate",
            }
        )
    for r in att["tab_not_on_card"]:
        rows.append(
            {
                "item_key": attention_item_key(r),
                "category": "Tab → card",
                "transaction_date": r["transaction_date"],
                "litres": r["litres"],
                "detail": r.get("ra_number") or "",
                "action": "Confirm card line or correct tab entry",
            }
        )
    for r in att["cars_not_charged"]:
        rows.append(
            {
                "item_key": attention_item_key(r),
                "category": "Cars+ billing",
                "transaction_date": r["transaction_date"],
                "litres": r["litres"],
                "detail": r.get("ra_number") or "",
                "action": r.get("reason") or "Charge customer on Cars+",
            }
        )
    rows.sort(key=lambda x: (x["category"], x["transaction_date"]))
    return rows
