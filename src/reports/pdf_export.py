from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from src.config import cars_loc_help_text

from .attention import extract_attention_items, format_attention_summary_text
from .cars_plus_note import cars_section_empty_note, cars_section_title


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
            "On fuel card; not on branch tab",
        ]
        for r in rows
    ]


def _branch_rows(rows: list[dict]) -> list[list]:
    return [
        [
            _fmt_date(r["transaction_date"]),
            f"{r['litres']:.2f}L",
            r.get("ra_number") or "",
            "On branch tab; no matching card line",
        ]
        for r in rows
    ]


def _cars_rows(rows: list[dict]) -> list[list]:
    return [
        [
            _fmt_date(r["transaction_date"]),
            f"{r['litres']:.2f}L",
            r.get("ra_number") or "",
            r.get("reason") or "No Cars+ fuel charge on this date",
        ]
        for r in rows
    ]


def export_branch_pdf(report: dict[str, Any], output_path: Path) -> None:
    att = extract_attention_items(report)
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
        Paragraph("Fuel Reconciliation — Action items", title_style),
        Paragraph(f"Branch: <b>{branch}</b>", styles["Normal"]),
        Paragraph(
            f"Generated: {datetime.now().strftime('%d %b %Y %H:%M')}",
            styles["Normal"],
        ),
        Spacer(1, 0.3 * cm),
        Paragraph(
            format_attention_summary_text(report).replace("\n", "<br/>"),
            styles["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    def add_section(heading: str, headers: list[str], rows: list[list]) -> None:
        story.append(Paragraph(heading, styles["Heading2"]))
        if not rows:
            story.append(Paragraph("None.", styles["Italic"]))
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

    card = att["card_not_on_tab"]
    add_section(
        f"1. Fuel card not on branch tab ({len(card)})",
        ["Date", "Litres", "Fuel type", "Action"],
        _stmt_rows(card),
    )

    tab = att["tab_not_on_card"]
    add_section(
        f"2. Branch tab without matching card line ({len(tab)})",
        ["Date", "Litres", "RA #", "Action"],
        _branch_rows(tab),
    )

    cars = att["cars_not_charged"]
    add_section(
        cars_section_title(branch, len(cars)),
        ["Date", "Litres", "RA #", "Notes"],
        _cars_rows(cars),
    )
    cars_note = cars_section_empty_note(report)
    if cars_note:
        story.append(Paragraph(f"<i>{cars_note}</i>", styles["Italic"]))
        story.append(Spacer(1, 0.2 * cm))
    story.append(
        Paragraph(f"<i>{cars_loc_help_text(branch)}</i>", styles["Italic"])
    )
    story.append(Spacer(1, 0.3 * cm))

    if att["credit_reversal_count"]:
        story.append(
            Paragraph(
                f"<i>{att['credit_reversal_count']} credit reversal(s) on the statement "
                "— already netted in the match count; no table.</i>",
                styles["Italic"],
            )
        )

    doc.build(story)
