"""Match branch tab RAs to Cars+ fuel charges (customer billing)."""

from src.importers.utils import normalize_ra
from src.models import BranchLitresRow, CarsPlusRow, UnmatchedLitres

from .nonrev import is_branch_nonrev
from .ra_match import ra_matches


def reconcile_cars_plus(
    branch_rows: list[BranchLitresRow],
    cars_rows: list[CarsPlusRow],
    *,
    operational_only: bool = True,
) -> list[UnmatchedLitres]:
    """
    Flag branch tab rows (with a real RA) that have no Cars+ fuel charge on the same date.
    NONREV rows are skipped when operational_only is True.
    """
    branch_items = [
        r
        for r in branch_rows
        if not is_branch_nonrev(r) or not operational_only
    ]
    branch_items = [
        r
        for r in branch_items
        if r.ra_number and r.ra_number[0].isdigit()
    ]

    billed_by_date: dict[str, list[tuple[str, CarsPlusRow]]] = {}
    for c in cars_rows:
        if not c.ra_number or not c.ra_number[0].isdigit():
            continue
        d = c.transaction_date.isoformat()
        billed_by_date.setdefault(d, []).append((normalize_ra(c.ra_number), c))

    unmatched: list[UnmatchedLitres] = []
    for row in branch_items:
        if is_branch_nonrev(row):
            continue
        bra = normalize_ra(row.ra_number)
        if not bra:
            continue
        d = row.transaction_date.isoformat()
        found = False
        for billed_ra, _ in billed_by_date.get(d, []):
            if ra_matches(bra, billed_ra):
                found = True
                break
        if not found:
            unmatched.append(
                UnmatchedLitres(
                    branch=row.branch,
                    ra_number=row.ra_number,
                    vehicle_label=row.vehicle_label,
                    transaction_date=row.transaction_date,
                    litres=row.litres,
                    time=row.time,
                    reason="Branch tab litres — not charged on Cars+ (same RA/date)",
                    source="cars_plus",
                    stage="cars_plus",
                )
            )
    return unmatched
