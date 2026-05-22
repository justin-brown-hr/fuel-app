"""Match branch tab RAs to Cars+ fuel charges (customer billing)."""

from src.config import cars_loc_label, filter_cars_for_branch
from src.importers.utils import normalize_ra
from src.models import BranchLitresRow, CarsPlusRow, UnmatchedLitres

from .nonrev import is_branch_nonrev
from .ra_match import ra_matches

# Billing can post on Cars+ a few days before/after the branch tab date
CARS_DATE_WINDOW_DAYS = 7


def _cars_billing_found(
    row: BranchLitresRow, loc_cars: list[CarsPlusRow]
) -> tuple[bool, int]:
    """Return (found, best day offset) for RA match within branch loc codes."""
    bra = normalize_ra(row.ra_number)
    if not bra:
        return False, 0
    best_days = CARS_DATE_WINDOW_DAYS + 1
    for c in loc_cars:
        if not c.ra_number or not c.ra_number[0].isdigit():
            continue
        if not ra_matches(bra, normalize_ra(c.ra_number)):
            continue
        days = abs((row.transaction_date - c.transaction_date).days)
        if days < best_days:
            best_days = days
    return best_days <= CARS_DATE_WINDOW_DAYS, best_days


def reconcile_cars_plus(
    branch_rows: list[BranchLitresRow],
    cars_rows: list[CarsPlusRow],
    *,
    branch: str,
    operational_only: bool = True,
) -> list[UnmatchedLitres]:
    """
    Flag branch tab rows (with a real RA) with no Cars+ fuel charge at this branch's
    location codes (WHN/WZZ for Whangarei, etc.) within CARS_DATE_WINDOW_DAYS.
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

    unmatched: list[UnmatchedLitres] = []
    for row in branch_items:
        found, _ = _cars_billing_found(row, loc_cars)
        if not found:
            unmatched.append(
                UnmatchedLitres(
                    branch=branch,
                    ra_number=row.ra_number,
                    vehicle_label=row.vehicle_label,
                    transaction_date=row.transaction_date,
                    litres=row.litres,
                    time=row.time,
                    reason=(
                        f"Not billed on Cars+ at {loc_label} "
                        f"(RA match within {CARS_DATE_WINDOW_DAYS} days)"
                    ),
                    source="cars_plus",
                    stage="cars_plus",
                )
            )
    return unmatched
