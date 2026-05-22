"""Match branch tab RAs to Cars+ fuel charges (customer billing)."""

from src.config import cars_loc_label, filter_cars_for_branch
from src.importers.utils import normalize_ra
from src.models import BranchLitresRow, CarsPlusRow, UnmatchedLitres

from .nonrev import is_branch_nonrev
from .ra_match import ra_matches


def reconcile_cars_plus(
    branch_rows: list[BranchLitresRow],
    cars_rows: list[CarsPlusRow],
    *,
    branch: str,
    operational_only: bool = True,
) -> list[UnmatchedLitres]:
    """
    Flag branch tab rows (with a real RA) that have no Cars+ fuel charge on the same date
    at this branch's Cars+ locations (RA Loc Out prefix, e.g. WHN/WNU for Whangarei).
    """
    loc_label = cars_loc_label(branch)
    branch_items = [
        r
        for r in branch_rows
        if r.branch == branch and not (operational_only and is_branch_nonrev(r))
    ]
    branch_items = [
        r
        for r in branch_items
        if r.ra_number and r.ra_number[0].isdigit()
    ]

    loc_cars = filter_cars_for_branch(cars_rows, branch)

    billed_by_date: dict[str, list[tuple[str, CarsPlusRow]]] = {}
    for c in loc_cars:
        if not c.ra_number or not c.ra_number[0].isdigit():
            continue
        d = c.transaction_date.isoformat()
        billed_by_date.setdefault(d, []).append((normalize_ra(c.ra_number), c))

    unmatched: list[UnmatchedLitres] = []
    for row in branch_items:
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
                    branch=branch,
                    ra_number=row.ra_number,
                    vehicle_label=row.vehicle_label,
                    transaction_date=row.transaction_date,
                    litres=row.litres,
                    time=row.time,
                    reason=f"Not billed on Cars+ at {loc_label} (same date & RA)",
                    source="cars_plus",
                    stage="cars_plus",
                )
            )
    return unmatched
