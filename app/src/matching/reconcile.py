from dataclasses import dataclass, field

from src.models import (
    BranchLitresRow,
    CarsPlusRow,
    FuelStatementRow,
    UnmatchedLitres,
)

from src.config import branch_tab_code, sort_client_branches
from src.importers.utils import normalize_ra

from .cars_reconcile import reconcile_cars_plus
from .ra_match import ra_matches
from .credits import is_credit_litres
from .fuel_type import normalize_fuel_type
from .nonrev import is_branch_nonrev

LITRE_TOLERANCE = 0.05
# Branch spreadsheet is often filled in days after the Farmlands card line
MAX_BRANCH_AFTER_STATEMENT_DAYS = 14
MIN_MATCH_SCORE = 1000


@dataclass
class StageSummary:
    statement_total: int = 0
    matched_count: int = 0
    statement_unmatched_count: int = 0
    branch_unmatched_count: int = 0
    credit_reversal_count: int = 0
    genuine_missing_count: int = 0
    branch_rows_included: int = 0


@dataclass
class BranchSummary:
    branch: str
    stage1: StageSummary = field(default_factory=StageSummary)
    stage2: StageSummary = field(default_factory=StageSummary)
    cars_plus_unbilled: int = 0
    nonrev_row_count: int = 0


@dataclass
class ReconcileResult:
    unmatched: list[UnmatchedLitres]
    credits_skipped_branch: int = 0
    credits_skipped_statement: int = 0
    nonrev_skipped_branch: int = 0
    branch_summaries: dict[str, BranchSummary] = field(default_factory=dict)


def is_branch_credit(row: BranchLitresRow) -> bool:
    return is_credit_litres(row.litres)


def is_statement_credit(row: FuelStatementRow) -> bool:
    return is_credit_litres(
        row.litres,
        product=row.product,
        supplier=row.supplier,
    )


def count_credits(
    branch_rows: list[BranchLitresRow],
    statement_rows: list[FuelStatementRow],
) -> tuple[int, int]:
    branch_credits = sum(1 for r in branch_rows if is_branch_credit(r))
    statement_credits = sum(1 for r in statement_rows if is_statement_credit(r))
    return branch_credits, statement_credits


def count_nonrev(branch_rows: list[BranchLitresRow]) -> int:
    return sum(1 for r in branch_rows if is_branch_nonrev(r))


def _credit_offset_keys(stmt_branch: list[FuelStatementRow]) -> set[tuple]:
    keys: set[tuple] = set()
    for r in stmt_branch:
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


def _strip_charge_before_reversal(
    rows: list[FuelStatementRow], stmt_branch: list[FuelStatementRow]
) -> list[FuelStatementRow]:
    """Remove same-day positive charge lines that pair with a credit reversal (refer manual count)."""
    offsets = _credit_offset_keys(stmt_branch)
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


def _has_same_day_credit_twin(row: FuelStatementRow, stmt_branch: list[FuelStatementRow]) -> bool:
    if row.litres <= 0:
        return False
    key = (
        row.branch,
        row.transaction_date.isoformat(),
        round(abs(row.litres), 2),
        normalize_fuel_type(row.product),
    )
    for other in stmt_branch:
        if other.litres < 0:
            other_key = (
                other.branch,
                other.transaction_date.isoformat(),
                round(abs(other.litres), 2),
                normalize_fuel_type(other.product),
            )
            if key == other_key:
                return True
    return False


def _litres_match(a: float, b: float) -> bool:
    return abs(a - b) <= LITRE_TOLERANCE


def _date_proximity_score(branch_date, statement_date) -> int:
    """
    Prefer the closest calendar date within the allowed window (card before or
    after tab entry). Same litres on a later-dated tab row must not steal a
    statement line from the correct earlier tab row.
    """
    days = abs((branch_date - statement_date).days)
    if days > MAX_BRANCH_AFTER_STATEMENT_DAYS:
        return -1
    if days == 0:
        return 100
    return max(10, 100 - days * 5)


def _match_score(branch: BranchLitresRow, statement: FuelStatementRow) -> int:
    if branch.branch != statement.branch:
        return -1
    if not _litres_match(branch.litres, statement.litres):
        return -1
    bra = normalize_ra(branch.ra_number)
    stmt_ra = normalize_ra(statement.ra_number or "")
    if stmt_ra and bra and not ra_matches(bra, stmt_ra):
        return -1
    # May branch tabs: RA + litres only (no date) — match on litres (+ RA when present).
    if not branch.transaction_date:
        return 1000
    prox = _date_proximity_score(branch.transaction_date, statement.transaction_date)
    if prox < 0:
        return -1
    return 1000 + prox


def _match_branch_pool(
    branch_items: list[BranchLitresRow],
    statement_items: list[FuelStatementRow],
) -> tuple[list[BranchLitresRow], list[FuelStatementRow], int]:
    """Match each card line to the best branch row (same litres, RA when present)."""
    used_branch: set[int] = set()
    matched_count = 0
    unmatched_stmt: list[FuelStatementRow] = []

    for st in statement_items:
        best_j = -1
        best_score = -1
        for j, br in enumerate(branch_items):
            if j in used_branch:
                continue
            score = _match_score(br, st)
            if score > best_score:
                best_score = score
                best_j = j
        if best_j >= 0 and best_score >= MIN_MATCH_SCORE:
            used_branch.add(best_j)
            matched_count += 1
        else:
            unmatched_stmt.append(st)

    unmatched_branch = [
        branch_items[j] for j in range(len(branch_items)) if j not in used_branch
    ]
    return unmatched_branch, unmatched_stmt, matched_count


def _fuel_type_label(product: str, litres: float) -> str:
    ft = normalize_fuel_type(product)
    if ft:
        return ft
    return "91" if litres > 0 else ""


def _branch_items_for_stage(
    branch_rows: list[BranchLitresRow], branch: str, include_nonrev: bool
) -> list[BranchLitresRow]:
    items = [
        r
        for r in branch_rows
        if r.branch == branch and not is_branch_credit(r)
    ]
    if not include_nonrev:
        items = [r for r in items if not is_branch_nonrev(r)]
    return items


def _reconcile_branch_stage(
    branch: str,
    branch_rows: list[BranchLitresRow],
    statement_rows: list[FuelStatementRow],
    *,
    stage: str,
    include_nonrev: bool,
) -> tuple[list[UnmatchedLitres], StageSummary]:
    stmt_branch = [r for r in statement_rows if r.branch == branch]
    stmt_credits = [r for r in stmt_branch if is_statement_credit(r)]
    stmt_positive = [r for r in stmt_branch if not is_statement_credit(r)]
    if include_nonrev:
        stmt_active = _strip_charge_before_reversal(stmt_positive, stmt_branch)
    else:
        stmt_active = stmt_positive
    branch_items = _branch_items_for_stage(branch_rows, branch, include_nonrev)

    um_branch, um_stmt, matched = _match_branch_pool(branch_items, stmt_active)
    tab = branch_tab_code(branch)
    unmatched: list[UnmatchedLitres] = []
    stage_label = "Stage 1 (incl. NONREV)" if include_nonrev else "Stage 2 (operational)"

    unmatched = []
    # No statement for this branch — cannot flag tab rows as "missing on card".
    if not stmt_active:
        um_branch = []

    for row in um_branch:
        nonrev = is_branch_nonrev(row)
        unmatched.append(
            UnmatchedLitres(
                branch=row.branch,
                ra_number=row.ra_number or ("NONREV" if nonrev else ""),
                vehicle_label=row.vehicle_label,
                transaction_date=row.transaction_date,
                litres=row.litres,
                time=row.time,
                reason=(
                    "On branch tab; no matching fuel card line"
                    + (" (NONREV)" if nonrev else "")
                ),
                source="branch_sheet",
                stage=stage,
                is_nonrev=nonrev,
            )
        )

    for row in um_stmt:
        if _has_same_day_credit_twin(row, stmt_branch):
            continue
        unmatched.append(
            UnmatchedLitres(
                branch=row.branch,
                ra_number=row.ra_number or "",
                vehicle_label=row.vehicle_name or row.product or row.supplier,
                transaction_date=row.transaction_date,
                litres=row.litres,
                time=row.time,
                reason=(
                    f"No matching litres on {tab} tab (Stage 1 incl. NONREV)"
                    if include_nonrev
                    else f"No matching litres on {tab} tab (operational only)"
                ),
                source="fuel_statement",
                supplier=row.supplier,
                fuel_type=_fuel_type_label(row.product, row.litres),
                stage=stage,
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
                stage=stage,
            )
        )

    stmt_unmatched_ops = sum(
        1 for row in um_stmt if not _has_same_day_credit_twin(row, stmt_branch)
    )
    summary = StageSummary(
        statement_total=len(stmt_active),
        matched_count=matched,
        statement_unmatched_count=stmt_unmatched_ops + len(stmt_credits),
        branch_unmatched_count=len(um_branch),
        credit_reversal_count=len(stmt_credits),
        genuine_missing_count=stmt_unmatched_ops,
        branch_rows_included=len(branch_items),
    )
    return unmatched, summary


def reconcile(
    branch_rows: list[BranchLitresRow],
    statement_rows: list[FuelStatementRow],
    cars_rows: list[CarsPlusRow] | None = None,
) -> ReconcileResult:
    """
    Stage 1: branch tab (including NONREV) vs fuel statement.
    Stage 2: operational branch rows only (excludes NONREV) vs fuel statement.
    Cars+: branch RA vs Cars+ fuel charges (operational RAs only).
    """
    dated_branch_rows = [r for r in branch_rows if r.transaction_date]
    credits_branch, credits_statement = count_credits(dated_branch_rows, statement_rows)
    nonrev_branch = count_nonrev(branch_rows)

    branch_set = {r.branch for r in branch_rows} | {r.branch for r in statement_rows}
    if cars_rows:
        branch_set |= {r.branch for r in cars_rows}
    branches = sort_client_branches(branch_set)

    all_unmatched: list[UnmatchedLitres] = []
    summaries: dict[str, BranchSummary] = {}

    for branch in branches:
        if statement_rows:
            u1, s1 = _reconcile_branch_stage(
                branch, branch_rows, statement_rows, stage="stage1", include_nonrev=True
            )
            u2, s2 = _reconcile_branch_stage(
                branch, branch_rows, statement_rows, stage="stage2", include_nonrev=False
            )
        else:
            u1, s1 = ([], StageSummary())
            u2, s2 = ([], StageSummary())
        all_unmatched.extend(u1)
        all_unmatched.extend(u2)

        cars_um: list[UnmatchedLitres] = []
        if cars_rows:
            cars_um = reconcile_cars_plus(
                branch_rows,
                cars_rows,
                branch=branch,
                operational_only=True,
            )
            all_unmatched.extend(cars_um)

        summaries[branch] = BranchSummary(
            branch=branch,
            stage1=s1,
            stage2=s2,
            cars_plus_unbilled=len(cars_um),
            nonrev_row_count=sum(
                1 for r in branch_rows if r.branch == branch and is_branch_nonrev(r)
            ),
        )

    return ReconcileResult(
        unmatched=all_unmatched,
        credits_skipped_branch=credits_branch,
        credits_skipped_statement=credits_statement,
        nonrev_skipped_branch=nonrev_branch,
        branch_summaries=summaries,
    )
