"""Filter reconciliation output to items that need follow-up."""

from typing import Any


def _is_credit_row(row: dict) -> bool:
    if row.get("is_credit"):
        return True
    try:
        return float(row.get("litres", 0)) < 0
    except (TypeError, ValueError):
        return False


def extract_attention_items(report: dict[str, Any]) -> dict[str, Any]:
    """
    Actionable items only:
    - Card line with no matching litres on branch tab (Stage 1 genuine gap)
    - Operational branch row with no matching card line
    - Operational branch RA with no Cars+ charge that date
    """
    card_not_on_tab = [
        r
        for r in report.get("unmatched_statement_stage1", [])
        if not _is_credit_row(r)
    ]
    tab_not_on_card = [
        r
        for r in report.get("unmatched_branch", [])
        if not r.get("is_nonrev") and not _is_credit_row(r)
    ]
    cars_not_charged = list(report.get("unmatched_cars_plus", []))

    credit_count = sum(
        1
        for r in report.get("unmatched_statement_stage1", [])
        if _is_credit_row(r)
    )

    return {
        "card_not_on_tab": card_not_on_tab,
        "tab_not_on_card": tab_not_on_card,
        "cars_not_charged": cars_not_charged,
        "credit_reversal_count": credit_count,
        "total_action_items": (
            len(card_not_on_tab) + len(tab_not_on_card) + len(cars_not_charged)
        ),
    }


def format_attention_summary_text(report: dict[str, Any]) -> str:
    branch = report.get("branch", "Unknown")
    s = report.get("summary", {})
    s1 = s.get("stage1", {})
    att = extract_attention_items(report)

    lines = [
        f"### {branch} — Items needing attention",
        "",
        f"**{s1.get('matched_count', 0)}** of **{s1.get('statement_total', 0)}** "
        "card fill-ups match the branch tab (incl. NONREV). "
        "Tables below list only follow-ups.",
        "",
    ]

    n_card = len(att["card_not_on_tab"])
    n_tab = len(att["tab_not_on_card"])
    n_cars = len(att["cars_not_charged"])
    n_cred = att["credit_reversal_count"]

    if n_card:
        lines.append(
            f"* **{n_card}** fuel card line(s) — on Farmlands, not on branch tab "
            "(add to spreadsheet or investigate)"
        )
    if n_tab:
        lines.append(
            f"* **{n_tab}** branch tab row(s) — on branch sheet, no matching card line"
        )
    from src.config import cars_loc_label
    from src.reports.cars_plus_note import cars_section_empty_note

    cars_total = report.get("cars_plus_imported_total", 0)
    cars_at_loc = report.get("cars_plus_at_branch_loc", 0)
    if n_cars:
        lines.append(
            f"* **{n_cars}** operational fill(s) — not billed on Cars+ at "
            f"**{cars_loc_label(branch)}** (same date & RA)"
        )
    elif cars_total == 0:
        lines.append(
            "* **Cars+** — file not loaded (re-import; copy xlsx off OneDrive if locked)"
        )
    elif cars_at_loc > 0:
        lines.append(
            f"* **Cars+** — **0** billing gaps ({cars_at_loc} {cars_loc_label(branch)} "
            "charges loaded; all matched)"
        )
    else:
        lines.append(
            f"* **Cars+** — no {cars_loc_label(branch)} rows in export (check RA Loc Out)"
        )
    note = cars_section_empty_note(report)
    if note and not n_cars:
        lines.append(f"* _{note}_")
    if n_cred:
        lines.append(
            f"* **{n_cred}** credit reversal(s) on statement (informational — no action)"
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
                "category": "Cars+ billing",
                "transaction_date": r["transaction_date"],
                "litres": r["litres"],
                "detail": r.get("ra_number") or "",
                "action": r.get("reason") or "Charge customer on Cars+",
            }
        )
    rows.sort(key=lambda x: (x["category"], x["transaction_date"]))
    return rows
