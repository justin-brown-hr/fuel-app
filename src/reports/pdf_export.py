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
    summary = report.get("summary", {})
    story = [
        Paragraph("Fuel Reconciliation Report", title_style),
        Paragraph(f"Branch: <b>{branch}</b>", styles["Normal"]),
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}",
            styles["Normal"],
        ),
        Paragraph(
            "<i>Produced by Fuel Reconcile app. "
            "Litres matching uses branch tab vs fuel statement only; "
            "Cars+ does not determine missing litres.</i>",
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

    stmt_um = report.get("unmatched_statement", report.get("unmatched", []))
    add_section(
        "Potential missing / unmatched (fuel statement)",
        ["Date", "Litres", "Fuel type", "Notes"],
        [
            [
                _fmt_date(r["transaction_date"]),
                f"{r['litres']:.2f}L",
                r.get("fuel_type") or "",
                r.get("reason", ""),
            ]
            for r in stmt_um
        ],
    )

    branch_um = [
        r
        for r in report.get("unmatched_branch", [])
        if "NONREV" not in (r.get("ra_number") or "").upper()
        and "NONREV" not in (r.get("vehicle_label") or "").upper()
    ]
    add_section(
        "Branch tab entries without matching statement (excludes NONREV)",
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
    if len(branch_um) > 50:
        story.append(
            Paragraph(f"(Showing first 50 of {len(branch_um)} rows)", styles["Italic"])
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
                for r in billed[:100]
            ],
        )

    doc.build(story)
