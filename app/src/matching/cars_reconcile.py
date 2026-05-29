"""Match branch tab RAs to Cars+ fuel charges (customer billing)."""

from src.config import cars_loc_label, filter_cars_for_branch
from src.importers.utils import normalize_ra
from src.models import BranchLitresRow, CarsPlusRow, UnmatchedLitres

from .nonrev import is_branch_nonrev
from .ra_match import ra_matches

# Branch tab vs Cars+ dates often differ (fill / return / export)
CARS_DATE_WINDOW_DAYS = 14


def _best_ra_date_match(
    row: BranchLitresRow, candidates: list[CarsPlusRow]
) -> tuple[bool, int]:
    """Best RA match within date window (does not consume charges — each row checked)."""
    bra = normalize_ra(row.ra_number)
    if not bra:
        return False, 0
    best_days = CARS_DATE_WINDOW_DAYS + 1
    for c in candidates:
        if not c.ra_number or not c.ra_number[0].isdigit():
            continue
        if not ra_matches(bra, normalize_ra(c.ra_number)):
            continue
        days = abs((row.transaction_date - c.transaction_date).days)
        if days < best_days:
            best_days = days
    return best_days <= CARS_DATE_WINDOW_DAYS, best_days


def _cars_billing_found(
    row: BranchLitresRow,
    branch_cars: list[CarsPlusRow],
    all_cars: list[CarsPlusRow],
) -> tuple[bool, str]:
    """
    Tier 1: RA + date at branch loc (Out or In).
    Tier 2: RA + date at another confirmed client Cars+ location.
    """
    found, _ = _best_ra_date_match(row, branch_cars)
    if found:
        return True, "branch"
    found, _ = _best_ra_date_match(row, all_cars)
    if found:
        return True, "anywhere"
    return False, ""


def reconcile_cars_plus(
    branch_rows: list[BranchLitresRow],
    cars_rows: list[CarsPlusRow],
    *,
    branch: str,
    operational_only: bool = True,
) -> list[UnmatchedLitres]:
    """
    Flag operational branch rows with no Cars+ fuel charge for the RA within
    CARS_DATE_WINDOW_DAYS. Cars+ rows are imported only for confirmed client
    locations, so national locations like Auckland/Wellington are ignored.
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

    branch_cars = filter_cars_for_branch(cars_rows, branch)

    unmatched: list[UnmatchedLitres] = []
    for row in branch_items:
        found, _ = _cars_billing_found(row, branch_cars, cars_rows)
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
                        f"Not billed on Cars+ for RA {row.ra_number} "
                        f"(within {CARS_DATE_WINDOW_DAYS} days at {loc_label} "
                        f"or another confirmed client location)"
                    ),
                    source="cars_plus",
                    stage="cars_plus",
                )
            )
    return unmatched
