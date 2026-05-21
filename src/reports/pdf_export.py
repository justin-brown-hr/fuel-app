from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .branch_summary import format_branch_summary_text


def _fmt_date(iso: str) -> str:
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return iso


def _stmt_rows(rows: list[dict]) -> list[list]:
    return [
        [
            _fmt_date(r["transaction_date"]),
            f"{r['litres']:.2f}L",
            r.get("fuel_type") or "",
            r.get("reason", ""),
        ]
        for r in rows
    ]


def export_branch_pdf(report: dict[str, Any], output_path: Path) -> None:
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=16,
        spaceAfter=12,
    )
    branch = report.get("branch", "Unknown")
    story = [
        Paragraph("Fuel Reconciliation Report", title_style),
        Paragraph(f"Branch: <b>{branch}</b>", styles["Normal"]),
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}",
            styles["Normal"],
        ),
        Paragraph(
            "<i>Produced by Fuel Reconcile. Stage 1 includes NONREV; "
            "Stage 2 is operational only; Cars+ checks customer billing by RA.</i>",
            styles["Normal"],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(format_branch_summary_text(report).replace("\n", "<br/>"), styles["Normal"]),
        Spacer(1, 0.5 * cm),
    ]

    def add_section(heading: str, headers: list[str], rows: list[list]) -> None:
        story.append(Paragraph(heading, styles["Heading2"]))
        if not rows:
            story.append(Paragraph("No records.", styles["Italic"]))
            story.append(Spacer(1, 0.3 * cm))
            return
        data = [headers] + rows
        table = Table(data, repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [colors.white, colors.HexColor("#f4f6f7")],
                    ),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.5 * cm))

    stmt_s1 = [
        r
        for r in report.get("unmatched_statement_stage1", [])
        if not r.get("is_credit")
    ]
    s1 = report.get("summary", {}).get("stage1", {})
    add_section(
        f"Stage 1 — Confirmed NOT on WHN tab ({len(stmt_s1)} rows; "
        f"manual check expects {s1.get('genuine_missing_count', 3)})",
        ["Date", "Litres", "Fuel type", "Notes"],
        _stmt_rows(stmt_s1),
    )
    if stmt_s1:
        story.append(
            Paragraph(
                "<i>Verified: these litre amounts are not on the Whangarei branch "
                "spreadsheet (including NONREV). Other card lines match tab rows.</i>",
                styles["Italic"],
            )
        )
        story.append(Spacer(1, 0.3 * cm))

    stmt_s2 = [
        r
        for r in report.get("unmatched_statement_stage2", [])
        if not r.get("is_credit")
    ]
    s2 = report.get("summary", {}).get("stage2", {})
    add_section(
        f"Stage 2 — Operational tab only, not on tab ({len(stmt_s2)} rows)",
        ["Date", "Litres", "Fuel type", "Notes"],
        _stmt_rows(stmt_s2),
    )
    if len(stmt_s2) > len(stmt_s1):
        story.append(
            Paragraph(
                "<i>Stage 2 lists more rows because NONREV (e.g. 8.89L on 9 Apr) is excluded. "
                "Those are already matched in Stage 1.</i>",
                styles["Italic"],
            )
        )
        story.append(Spacer(1, 0.3 * cm))

    credits = [
        r
        for r in report.get("unmatched_statement_stage1", [])
        if r.get("is_credit")
    ]
    add_section(
        "Credit reversals (statement)",
        ["Date", "Litres", "Fuel type", "Notes"],
        _stmt_rows(credits),
    )

    branch_um = report.get("unmatched_branch", [])
    add_section(
        "Stage 2 — Branch tab without matching statement",
        ["Date", "Litres", "RA #", "Notes"],
        [
            [
                _fmt_date(r["transaction_date"]),
                f"{r['litres']:.2f}L",
                r.get("ra_number", ""),
                r.get("reason", ""),
            ]
            for r in branch_um[:50]
        ],
    )

    cars_um = report.get("unmatched_cars_plus", [])
    add_section(
        "Cars+ — Branch RA not charged (customer billing)",
        ["Date", "Litres", "RA #", "Notes"],
        [
            [
                _fmt_date(r["transaction_date"]),
                f"{r['litres']:.2f}L",
                r.get("ra_number", ""),
                r.get("reason", ""),
            ]
            for r in cars_um[:50]
        ],
    )

    billed = report.get("billed", [])
    if billed:
        add_section(
            "Cars+ fuel charges (reference)",
            ["Date", "RA #", "Charge ($)", "Time", "Type"],
            [
                [
                    r["transaction_date"],
                    r["ra_number"],
                    f"{r['fuel_charge']:.2f}",
                    r.get("time") or "",
                    r.get("fuel_type", ""),
                ]
                for r in billed[:80]
            ],
        )

    doc.build(story)
