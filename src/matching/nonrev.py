"""NONREV rows on branch sheets are excluded from litre matching."""

from src.models import BranchLitresRow


def is_branch_nonrev(row: BranchLitresRow) -> bool:
    text = f"{row.ra_number or ''} {row.vehicle_label or ''}".upper()
    return "NONREV" in text
