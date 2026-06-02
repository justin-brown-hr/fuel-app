from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from src.config import cars_loc_help_text

from .attention import (
    attention_summary_bullets,
    extract_attention_items,
)
from .cars_plus_note import cars_section_empty_note, cars_section_title
from .fuel_card_labels import card_not_on_tab_action, tab_not_on_card_action


def _fmt_date(iso: str) -> str:
    if not iso:
        return ""
    try:
        return datetime.strptime(iso[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except ValueError:
        return iso


def _pdf_styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "PdfTitle",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#111111"),
            spaceAfter=10,
            alignment=TA_LEFT,
        ),
        "meta": ParagraphStyle(
            "PdfMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#333333"),
            spaceAfter=3,
        ),
        "section": ParagraphStyle(
            "PdfSection",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#111111"),
            spaceBefore=4,
            spaceAfter=10,
        ),
        "bullet": ParagraphStyle(
            "PdfBullet",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=14,
            textColor=colors.HexColor("#222222"),
            leftIndent=18,
            bulletIndent=8,
            spaceAfter=7,
        ),
        "h2": ParagraphStyle(
            "PdfH2",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=15,
            textColor=colors.HexColor("#1a5276"),
            spaceBefore=14,
            spaceAfter=8,
        ),
        "italic": ParagraphStyle(
            "PdfItalic",
            parent=base["Italic"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#555555"),
        ),
    }


def _pdf_cover_section(report: dict[str, Any], styles: dict) -> list:
    """Header + summary block matching client PDF layout."""
    branch = report.get("branch", "Unknown")
    story = [
        Paragraph("Fuel Reconciliation — Action Items", styles["title"]),
        Paragraph(f"<b>Branch:</b> {branch}", styles["meta"]),
        Paragraph(
            f"<b>Generated:</b> {datetime.now().strftime('%d %b %Y %H:%M')}",
            styles["meta"],
        ),
        Spacer(1, 0.25 * cm),
        HRFlowable(
            width="100%",
            thickness=0.75,
            color=colors.HexColor("#b0b8c4"),
            spaceBefore=2,
            spaceAfter=12,
        ),
        Paragraph(f"{branch} — Items needing attention", styles["section"]),
    ]
    for line in attention_summary_bullets(report):
        story.append(Paragraph(f"• {line}", styles["bullet"]))
    story.append(Spacer(1, 0.45 * cm))
    return story


def _stmt_rows(report: dict[str, Any], rows: list[dict]) -> list[list]:
    action = card_not_on_tab_action(report)
    return [
        [
            _fmt_date(r["transaction_date"]),
            f"{r['litres']:.2f}L",
            r.get("fuel_type") or "",
            action,
        ]
        for r in rows
    ]


def _branch_rows(report: dict[str, Any], rows: list[dict]) -> list[list]:
    action = tab_not_on_card_action(report)
    return [
        [
            _fmt_date(r["transaction_date"]),
            f"{r['litres']:.2f}L",
            r.get("ra_number") or "",
            action,
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
    styles = _pdf_styles()
    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=2 * cm,
        leftMargin=2 * cm,
        topMargin=1.8 * cm,
        bottomMargin=2 * cm,
    )
    branch = report.get("branch", "Unknown")
    story = _pdf_cover_section(report, styles)

    def add_section(heading: str, headers: list[str], rows: list[list]) -> None:
        story.append(Paragraph(heading, styles["h2"]))
        if not rows:
            story.append(Paragraph("None.", styles["italic"]))
            story.append(Spacer(1, 0.3 * cm))
            return
        data = [headers] + rows
        table = Table(data, repeatRows=1, colWidths=None)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1a5276")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
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
        story.append(Spacer(1, 0.45 * cm))

    card = att["card_not_on_tab"]
    add_section(
        f"1. Fuel card not on branch tab ({len(card)})",
        ["Date", "Litres", "Fuel type", "Action"],
        _stmt_rows(report, card),
    )

    tab = att["tab_not_on_card"]
    add_section(
        f"2. Branch tab without matching card line ({len(tab)})",
        ["Date", "Litres", "RA #", "Action"],
        _branch_rows(report, tab),
    )

    cars = att["cars_not_charged"]
    add_section(
        cars_section_title(branch, len(cars)),
        ["Date", "Litres", "RA #", "Notes"],
        _cars_rows(cars),
    )
    cars_note = cars_section_empty_note(report)
    if cars_note:
        story.append(Paragraph(f"<i>{cars_note}</i>", styles["italic"]))
        story.append(Spacer(1, 0.15 * cm))
    story.append(Paragraph(f"<i>{cars_loc_help_text(branch)}</i>", styles["italic"]))

    doc.build(story)
