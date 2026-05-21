"""Command-line interface (no GUI) for import, summary, and PDF export."""

import argparse
import sys
from pathlib import Path

from src.db.database import Database
from src.reports.branch_summary import format_branch_summary_text
from src.reports.pdf_export import export_branch_pdf
from src.services.import_service import ImportService


def _parse_args(argv: list[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Fuel Reconcile — import and compare branch litres vs fuel statement"
    )
    p.add_argument("--fuel", type=Path, help="Fuel statement PDF or Excel")
    p.add_argument("--branch", type=Path, help="Branch litres .xlsx")
    p.add_argument("--cars", type=Path, help="Cars+ statement .xlsx (optional)")
    p.add_argument(
        "--branch-name",
        help="Branch to report on (default: first branch with data)",
    )
    p.add_argument("--export", type=Path, help="Write branch PDF to this path")
    p.add_argument(
        "--list-branches",
        action="store_true",
        help="List branches and summary counts after import",
    )
    p.add_argument("--label", default="CLI import", help="Import batch label")
    return p.parse_args(argv)


def run_cli(argv: list[str] | None = None) -> int:
    args = _parse_args(argv or sys.argv[1:])
    if not args.fuel or not args.branch:
        print("Error: --fuel and --branch are required.", file=sys.stderr)
        print("Example:", file=sys.stderr)
        print(
            "  python3 run.py --cli --fuel docs/'Farmlands Statement April.PDF' "
            "--branch 'docs/branch litres.xlsx' --cars 'docs/cars+ statement.xlsx' "
            "--branch-name Whangarei",
            file=sys.stderr,
        )
        return 1

    svc = ImportService()
    result = svc.process_files(
        args.fuel,
        args.branch,
        args.cars,
        label=args.label,
    )
    print(f"Import batch #{result.batch_id}")
    print(
        f"  Branch litres: {result.branch_litres_count} | "
        f"Statement: {result.fuel_statement_count} | "
        f"Cars+: {result.cars_plus_count} | "
        f"Unmatched: {result.unmatched_count}"
    )
    if result.errors:
        print("  Warnings:", "; ".join(result.errors))
    if result.credits_skipped_branch or result.credits_skipped_statement:
        print(
            f"  Credits skipped: sheet {result.credits_skipped_branch}, "
            f"statement {result.credits_skipped_statement}"
        )

    if not result.branches:
        print("No branches found.")
        return 1

    db = Database()
    branch = args.branch_name or result.branches[0]
    if branch not in result.branches:
        print(f"Unknown branch '{branch}'. Available: {', '.join(result.branches)}")
        return 1

    if args.list_branches:
        print("\nBranches:")
        for b in result.branches:
            s = db.get_branch_summary(result.batch_id, b) or {}
            print(
                f"  {b}: statement={s.get('statement_total', '?')} "
                f"matched={s.get('matched_count', '?')} "
                f"unmatched={s.get('statement_unmatched_count', '?')}"
            )

    report = db.get_branch_report(result.batch_id, branch)
    print("\n" + format_branch_summary_text(report))

    stmt_um = report.get("unmatched_statement", [])
    if stmt_um:
        print("\nStatement unmatched:")
        print(f"{'Date':<12} {'Litres':>8}  {'Fuel':<8}  Notes")
        for r in stmt_um:
            print(
                f"{r['transaction_date']:<12} {r['litres']:>7.2f}L  "
                f"{(r.get('fuel_type') or ''):<8}  {r.get('reason', '')}"
            )

    if args.export:
        export_branch_pdf(report, args.export)
        print(f"\nPDF saved: {args.export}")

    return 0
