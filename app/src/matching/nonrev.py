"""NONREV rows on branch sheets."""

from src.models import BranchLitresRow


def is_branch_nonrev(row: BranchLitresRow) -> bool:
    if getattr(row, "is_nonrev", False):
        return True
    text = f"{row.ra_number or ''} {row.vehicle_label or ''}".upper()
    return "NONREV" in text
