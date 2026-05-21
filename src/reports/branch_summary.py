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
        f"* **Statement fill-ups:** **{s1.get('statement_total', 0)}**",
        f"* **Matched (incl. NONREV rows):** **{s1.get('matched_count', 0)}**",
        f"* **Genuine missing on WHN tab:** **{s1.get('genuine_missing_count', 0)}**",
        "",
        "### Stage 2 — Operational (excl. NONREV) vs fuel statement",
        "",
        f"* **Statement fill-ups:** **{s2.get('statement_total', 0)}**",
        f"* **Matched:** **{s2.get('matched_count', 0)}**",
        f"* **Genuine missing on WHN tab:** **{s2.get('genuine_missing_count', 0)}**",
        f"* **Credit reversals (listed separately):** **{s.get('credit_reversal_count', 0)}**",
        "",
    ]
    if s.get("nonrev_row_count"):
        lines.append(
            f"* **{s['nonrev_row_count']}** NONREV rows on branch tab "
            "(included in Stage 1 only)"
        )
        lines.append("")
    if s.get("cars_plus_unbilled"):
        lines.append(
            f"* **{s['cars_plus_unbilled']}** branch tab rows with RA "
            "**not charged on Cars+** (same date)"
        )
        lines.append("")
    lines.extend(
        [
            "**How this report works:**",
            "",
            "* **Stage 1** — All branch tab litres including NONREV (matches card statement).",
            "* **Stage 2** — Operational rows only; NONREV excluded from missing-litre checks.",
            "* **Cars+** — Checks branch RA numbers against Cars+ fuel charges (customer billing).",
            "",
        ]
    )
    return "\n".join(lines)
