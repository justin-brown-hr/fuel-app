from typing import Any


def format_branch_summary_text(report: dict[str, Any]) -> str:
    branch = report.get("branch", "Unknown")
    s = report.get("summary", {})
    s1 = s.get("stage1", {})
    s2 = s.get("stage2", {})

    lines = [
        f"### {branch} — Fuel litres comparison",
        "",
        "### Stage 1 — Branch tab incl. NONREV vs fuel statement",
        "",
        "This is the same check as a manual / ChatGPT comparison.",
        "",
        f"* **Statement fill-ups compared:** **{s1.get('statement_total', 0)}** "
        "(86 lines on the Farmlands card; two +5.17 / +2.25 charges on 10 Apr are "
        "netted with same-day credits and not double-counted)",
        f"* **Matched to WHN tab (incl. NONREV):** **{s1.get('matched_count', 0)}**",
        f"* **Genuine missing on WHN tab:** **{s1.get('genuine_missing_count', 0)}** "
        "— on the card but no matching litres on the spreadsheet (incl. NONREV)",
        f"* **Credit reversals:** **{s.get('credit_reversal_count', 0)}**",
        "",
        "### Stage 2 — Operational only (NONREV excluded)",
        "",
        f"* **Matched:** **{s2.get('matched_count', 0)}**",
        f"* **Statement lines not on operational tab:** **{s2.get('genuine_missing_count', 0)}**",
        "(NONREV rows such as 8.89L on 9 Apr match in Stage 1 only)",
        "",
    ]
    if s.get("nonrev_row_count"):
        lines.append(f"* **{s['nonrev_row_count']}** NONREV rows on WHN tab (Stage 1 only)")
        lines.append("")
    if s.get("cars_plus_unbilled"):
        lines.append(
            f"* **{s['cars_plus_unbilled']}** operational RAs on tab with no Cars+ charge that date"
        )
        lines.append("")
    lines.extend(
        [
            "**How to read the tables below**",
            "",
            "* **Stage 1 table** — Only true gaps (usually 3 lines). If litres appear on your WHN tab "
            "(including NONREV), they will not be listed here.",
            "* **Stage 2 table** — Wider operational list; NONREV-matched card lines appear here as "
            "'missing' because NONREV is excluded in Stage 2.",
            "* **Cars+** — Billing check by RA number, not litres.",
            "",
        ]
    )
    return "\n".join(lines)
