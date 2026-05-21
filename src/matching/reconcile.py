from dataclasses import dataclass, field

from src.models import (
    BranchLitresRow,
    CarsPlusRow,
    FuelStatementRow,
    UnmatchedLitres,
)

from src.config import branch_tab_code
from src.importers.utils import normalize_ra

from .credits import is_credit_litres
from .fuel_type import normalize_fuel_type

# Allow small rounding differences between sheet and statement
LITRE_TOLERANCE = 0.05


@dataclass
class BranchSummary:
    branch: str
    statement_total: int = 0
    matched_count: int = 0
    statement_unmatched_count: int = 0
    branch_unmatched_count: int = 0
    credit_reversal_count: int = 0
    genuine_missing_count: int = 0


@dataclass
class ReconcileResult:
    unmatched: list[UnmatchedLitres]
    credits_skipped_branch: int = 0
    credits_skipped_statement: int = 0
    branch_summaries: dict[str, BranchSummary] = field(default_factory=dict)


def is_branch_credit(row: BranchLitresRow) -> bool:
    return is_credit_litres(row.litres)


def is_statement_credit(row: FuelStatementRow) -> bool:
    return is_credit_litres(
        row.litres,
        product=row.product,
        supplier=row.supplier,
    )


def _credit_offset_keys(rows: list[FuelStatementRow]) -> set[tuple]:
    keys: set[tuple] = set()
    for r in rows:
        if r.litres < 0:
            keys.add(
                (
                    r.branch,
                    r.transaction_date.isoformat(),
                    round(abs(r.litres), 2),
                    normalize_fuel_type(r.product),
                )
            )
    return keys


def _strip_credit_offset_pairs(rows: list[FuelStatementRow]) -> list[FuelStatementRow]:
    """Drop positive fill-ups that pair with a same-day credit reversal."""
    offsets = _credit_offset_keys(rows)
    return [
        r
        for r in rows
        if not (
            r.litres > 0
            and (
                r.branch,
                r.transaction_date.isoformat(),
                round(r.litres, 2),
                normalize_fuel_type(r.product),
            )
            in offsets
        )
    ]


def count_credits(
    branch_rows: list[BranchLitresRow],
    statement_rows: list[FuelStatementRow],
) -> tuple[int, int]:
    branch_credits = sum(1 for r in branch_rows if is_branch_credit(r))
    statement_credits = sum(1 for r in statement_rows if is_statement_credit(r))
    return branch_credits, statement_credits


def _litres_match(a: float, b: float) -> bool:
    return abs(a - b) <= LITRE_TOLERANCE


def _ra_matches(branch_ra: str, other_ra: str) -> bool:
    if not branch_ra or not other_ra:
        return True
    if branch_ra == other_ra:
        return True
    shorter, longer = (
        (branch_ra, other_ra) if len(branch_ra) <= len(other_ra) else (other_ra, branch_ra)
    )
    if len(shorter) >= 6 and longer.startswith(shorter):
        return True
    return False


def _date_proximity_score(branch_date, statement_date) -> int:
    days = abs((branch_date - statement_date).days)
    if days == 0:
        return 100
    if days <= 3:
        return 50 - days
    if days <= 7:
        return 20 - days
    return max(0, 10 - days)


def _match_score(branch: BranchLitresRow, statement: FuelStatementRow) -> int:
    if branch.branch != statement.branch:
        return -1
    if not _litres_match(branch.litres, statement.litres):
        return -1
    bra = normalize_ra(branch.ra_number)
    stmt_ra = normalize_ra(statement.ra_number or "")
    if stmt_ra and bra and not _ra_matches(bra, stmt_ra):
        return -1
    return 1000 + _date_proximity_score(branch.transaction_date, statement.transaction_date)


def _match_branch_pool(
    branch_items: list[BranchLitresRow],
    statement_items: list[FuelStatementRow],
) -> tuple[list[BranchLitresRow], list[FuelStatementRow], int]:
    used_stmt: set[int] = set()
    matched_count = 0
    unmatched_branch: list[BranchLitresRow] = []

    for br in branch_items:
        best_i = -1
        best_score = -1
        for i, st in enumerate(statement_items):
            if i in used_stmt:
                continue
            score = _match_score(br, st)
            if score > best_score:
                best_score = score
                best_i = i
        if best_i >= 0:
            used_stmt.add(best_i)
            matched_count += 1
        else:
            unmatched_branch.append(br)

    unmatched_stmt = [
        statement_items[i] for i in range(len(statement_items)) if i not in used_stmt
    ]
    return unmatched_branch, unmatched_stmt, matched_count


def _fuel_type_label(product: str, litres: float) -> str:
    ft = normalize_fuel_type(product)
    if ft:
        return ft
    return "91" if litres > 0 else ""


def reconcile(
    branch_rows: list[BranchLitresRow],
    statement_rows: list[FuelStatementRow],
    cars_rows: list[CarsPlusRow] | None = None,
) -> ReconcileResult:
    """
    Match litres between branch fuel sheets and fuel card statements (per branch).
    Matching is primarily by litres within the branch; dates may differ between sources.
    Credit lines are listed separately and excluded from the matched count.
    """
    del cars_rows

    credits_branch, credits_statement = count_credits(branch_rows, statement_rows)
    branch_active = [r for r in branch_rows if not is_branch_credit(r)]

    branches = sorted(
        {r.branch for r in branch_rows}
        | {r.branch for r in statement_rows}
    )

    unmatched: list[UnmatchedLitres] = []
    summaries: dict[str, BranchSummary] = {}

    for branch in branches:
        stmt_branch = [r for r in statement_rows if r.branch == branch]
        stmt_all = _strip_credit_offset_pairs(stmt_branch)
        stmt_credits = [r for r in stmt_branch if is_statement_credit(r)]
        stmt_active = [r for r in stmt_all if not is_statement_credit(r)]
        branch_items = [r for r in branch_active if r.branch == branch]

        um_branch, um_stmt, matched = _match_branch_pool(branch_items, stmt_active)

        tab = branch_tab_code(branch)

        for row in um_branch:
            note = f"Not found on {tab} tab"
            if row.vehicle_label and "NONREV" in row.vehicle_label.upper():
                note += " (NONREV)"
            unmatched.append(
                UnmatchedLitres(
                    branch=row.branch,
                    ra_number=row.ra_number,
                    vehicle_label=row.vehicle_label,
                    transaction_date=row.transaction_date,
                    litres=row.litres,
                    time=row.time,
                    reason=note,
                    source="branch_sheet",
                )
            )

        for row in um_stmt:
            unmatched.append(
                UnmatchedLitres(
                    branch=row.branch,
                    ra_number=row.ra_number or "",
                    vehicle_label=row.vehicle_name or row.product or row.supplier,
                    transaction_date=row.transaction_date,
                    litres=row.litres,
                    time=row.time,
                    reason=f"Not found in {tab} tab",
                    source="fuel_statement",
                    supplier=row.supplier,
                    fuel_type=_fuel_type_label(row.product, row.litres),
                )
            )

        for row in stmt_credits:
            unmatched.append(
                UnmatchedLitres(
                    branch=row.branch,
                    ra_number=row.ra_number or "",
                    vehicle_label=row.product or row.supplier,
                    transaction_date=row.transaction_date,
                    litres=row.litres,
                    time=row.time,
                    reason="Credit/reversal entry",
                    source="fuel_statement",
                    supplier=row.supplier,
                    fuel_type=_fuel_type_label(row.product, row.litres),
                    is_credit=True,
                )
            )

        stmt_unmatched_ops = len(um_stmt)
        summaries[branch] = BranchSummary(
            branch=branch,
            statement_total=len(stmt_all),
            matched_count=matched,
            statement_unmatched_count=stmt_unmatched_ops + len(stmt_credits),
            branch_unmatched_count=len(um_branch),
            credit_reversal_count=len(stmt_credits),
            genuine_missing_count=stmt_unmatched_ops,
        )

    return ReconcileResult(
        unmatched=unmatched,
        credits_skipped_branch=credits_branch,
        credits_skipped_statement=credits_statement,
        branch_summaries=summaries,
    )
