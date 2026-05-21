from typing import Any


def format_branch_summary_text(report: dict[str, Any]) -> str:
    """Format comparison summary like docs/refer_value.md."""
    branch = report.get("branch", "Unknown")
    s = report.get("summary", {})
    lines = [
        f"### {branch} — Fuel litres comparison",
        "",
        "### Summary",
        "",
        f"* **Total fill-ups on fuel statement:** **{s.get('statement_total', 0)}**",
        f"* **Matched against {branch} branch tab:** **{s.get('matched_count', 0)}**",
        f"* **Potentially missing / unmatched:** "
        f"**{s.get('statement_unmatched_count', 0)} statement entries**",
        "",
    ]
    if s.get("genuine_missing_count", 0) or s.get("credit_reversal_count", 0):
        lines.extend(
            [
                "Operationally:",
                "",
                f"* **{s.get('statement_total', 0)}** supplier fills",
                f"* **{s.get('matched_count', 0)}** matched",
                f"* **{s.get('genuine_missing_count', 0)}** likely genuine missing branch records",
                f"* **{s.get('credit_reversal_count', 0)}** credit reversals",
                "",
            ]
        )
    if s.get("branch_unmatched_count", 0):
        lines.append(
            f"* **{s.get('branch_unmatched_count', 0)}** entries on branch tab "
            "without a matching statement line"
        )
        lines.append("")
    nonrev = report.get("nonrev_skipped_branch", 0)
    if nonrev:
        lines.append(f"* **{nonrev}** NONREV rows on branch tab excluded from matching")
        lines.append("")
    lines.extend(
        [
            "**How this report works:**",
            "",
            "* Compares **branch litres tab** vs **fuel card statement** (litres only).",
            "* **NONREV** rows on the branch tab are excluded (not fuel fills).",
            "* **Credit/reversal** lines on the statement are listed but not counted as missing fuel.",
            "* **Cars+** is shown for reference only — billing in dollars is **not** used to decide missing litres.",
            "",
        ]
    )
    return "\n".join(lines)
