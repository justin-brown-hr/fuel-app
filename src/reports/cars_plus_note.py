"""Explain Cars+ section counts in reports."""

from typing import Any

from src.config import cars_loc_help_text, cars_loc_label


def cars_section_title(branch: str, unbilled_count: int) -> str:
    return (
        f"3. Cars+ — customer not billed at {cars_loc_label(branch)} "
        f"({unbilled_count})"
    )


def cars_section_empty_note(report: dict[str, Any]) -> str:
    """Why section 3 has no rows — avoids looking like Cars+ was ignored."""
    branch = report.get("branch", "")
    total = report.get("cars_plus_imported_total", 0)
    at_branch = report.get("cars_plus_at_branch_loc", 0)
    unbilled = len(report.get("unmatched_cars_plus", []))

    if total == 0:
        return (
            "Cars+ file was not loaded for this import. "
            "Copy cars+ statement.xlsx to Desktop (not open in OneDrive preview), "
            "re-import all three files, and check the status line for errors."
        )
    if at_branch == 0:
        return (
            f"No Cars+ rows with {cars_loc_label(branch)} location codes in the export. "
            "Check the RA Loc Out column matches your branch, or send a sample file "
            "to update the importer."
        )
    if unbilled == 0:
        return (
            f"Cars+ loaded ({at_branch} charges at {cars_loc_label(branch)}). "
            "No gaps — every operational branch-tab fill has a matching Cars+ "
            "fuel charge on the same date and RA."
        )
    return ""
