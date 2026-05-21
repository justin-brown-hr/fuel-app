"""Command-line interface (no GUI) for import, summary, and PDF export."""

import argparse
import sys
from pathlib import Path

from src.db.database import Database
from src.reports.attention import extract_attention_items, format_attention_summary_text
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


def _print_rows(title: str, rows: list[dict], cols: tuple[str, ...]) -> None:
    if not rows:
        return
    print(f"\n{title} ({len(rows)}):")
    hdr = f"{'Date':<12} {'Litres':>8}  "
    if "fuel" in cols:
        print(hdr + f"{'Fuel':<8}  Action")
        for r in rows:
            print(
                f"{r['transaction_date']:<12} {r['litres']:>7.2f}L  "
                f"{(r.get('fuel_type') or ''):<8}  On card; not on tab"
            )
    elif "ra" in cols:
        print(hdr + f"{'RA #':<12}  Action")
        for r in rows:
            print(
                f"{r['transaction_date']:<12} {r['litres']:>7.2f}L  "
                f"{(r.get('ra_number') or ''):<12}  "
                f"{r.get('reason', 'On tab; no card line')[:40]}"
            )


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
            s1 = s.get("stage1", {})
            print(
                f"  {b}: matched={s1.get('matched_count', '?')}/"
                f"{s1.get('statement_total', '?')} "
                f"action gaps={s1.get('genuine_missing_count', '?')}"
            )

    report = db.get_branch_report(result.batch_id, branch)
    att = extract_attention_items(report)
    print("\n" + format_attention_summary_text(report))

    _print_rows("1. Card not on branch tab", att["card_not_on_tab"], ("fuel",))
    _print_rows("2. Branch tab without card", att["tab_not_on_card"], ("ra",))
    _print_rows("3. Cars+ not charged", att["cars_not_charged"], ("ra",))

    if args.export:
        export_branch_pdf(report, args.export)
        print(f"\nPDF saved: {args.export} ({att['total_action_items']} action items)")

    return 0
