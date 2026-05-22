"""Application-wide visual theme (Qt stylesheets)."""

import re

from PySide6.QtGui import QColor, QFont, QPalette
from PySide6.QtWidgets import QApplication

# Slate + sky accent (modern SaaS)
COLORS = {
    "bg": "#f1f5f9",
    "surface": "#ffffff",
    "surface_alt": "#f8fafc",
    "border": "#e2e8f0",
    "border_strong": "#cbd5e1",
    "text": "#0f172a",
    "text_muted": "#64748b",
    "primary": "#0ea5e9",
    "primary_hover": "#0284c7",
    "primary_pressed": "#0369a1",
    "accent_soft": "#e0f2fe",
    "success": "#10b981",
    "warning": "#f59e0b",
    "header": "#0f172a",
}

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLORS["bg"]};
}}
QWidget {{
    color: {COLORS["text"]};
    font-family: "Segoe UI", "SF Pro Text", "Helvetica Neue", sans-serif;
    font-size: 13px;
}}
#AppHeader {{
    background-color: {COLORS["header"]};
    border-radius: 12px;
    min-height: 56px;
}}
#AppTitle {{
    color: #f8fafc;
    font-size: 20px;
    font-weight: 600;
    padding-left: 4px;
}}
#AppSubtitle {{
    color: #94a3b8;
    font-size: 12px;
}}
#Card {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 12px;
}}
#CardTitle {{
    color: {COLORS["text"]};
    font-size: 14px;
    font-weight: 600;
}}
#DropZone {{
    background-color: {COLORS["surface_alt"]};
    border: 2px dashed {COLORS["border_strong"]};
    border-radius: 14px;
    color: {COLORS["text_muted"]};
    font-size: 13px;
    padding: 12px 16px;
}}
QSplitter::handle {{
    background-color: {COLORS["border"]};
    margin: 0 4px;
    border-radius: 2px;
}}
QSplitter::handle:horizontal {{
    width: 4px;
}}
QSplitter::handle:vertical {{
    height: 4px;
}}
QSplitter::handle:hover {{
    background-color: {COLORS["primary"]};
}}
QScrollArea {{
    background: transparent;
    border: none;
}}
#DropZone[hasFiles="true"] {{
    background-color: {COLORS["accent_soft"]};
    border: 2px solid {COLORS["primary"]};
    color: {COLORS["text"]};
}}
#DropZone[dragActive="true"] {{
    background-color: {COLORS["accent_soft"]};
    border: 2px solid {COLORS["primary"]};
}}
#DropZoneTitle {{
    font-size: 15px;
    font-weight: 600;
    color: {COLORS["text"]};
}}
#StatusPill {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 8px;
    color: {COLORS["text_muted"]};
    padding: 10px 14px;
    font-size: 12px;
}}
#SummaryPanel {{
    background-color: {COLORS["surface_alt"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    padding: 14px 16px;
}}
#SummaryPanel QLabel {{
    background: transparent;
}}
QPushButton {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border_strong"]};
    border-radius: 8px;
    padding: 10px 18px;
    font-weight: 500;
    min-height: 20px;
}}
QPushButton:hover {{
    background-color: {COLORS["surface_alt"]};
    border-color: {COLORS["text_muted"]};
}}
QPushButton:pressed {{
    background-color: {COLORS["border"]};
}}
QPushButton#PrimaryButton {{
    background-color: {COLORS["primary"]};
    color: #ffffff;
    border: none;
    font-weight: 600;
}}
QPushButton#PrimaryButton:hover {{
    background-color: {COLORS["primary_hover"]};
}}
QPushButton#PrimaryButton:pressed {{
    background-color: {COLORS["primary_pressed"]};
}}
QPushButton#AccentButton {{
    background-color: {COLORS["accent_soft"]};
    color: {COLORS["primary_pressed"]};
    border: 1px solid {COLORS["primary"]};
    font-weight: 600;
}}
QPushButton#AccentButton:hover {{
    background-color: #bae6fd;
}}
QPushButton#AcceptButton {{
    background-color: {COLORS["surface"]};
    color: {COLORS["text"]};
    border: 1px solid {COLORS["border_strong"]};
    padding: 4px 10px;
    font-size: 12px;
}}
QPushButton#AcceptButton:hover {{
    background-color: {COLORS["accent_soft"]};
    border-color: {COLORS["primary"]};
}}
QComboBox {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border_strong"]};
    border-radius: 8px;
    padding: 8px 12px;
    min-height: 20px;
}}
QComboBox:hover {{
    border-color: {COLORS["primary"]};
}}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    selection-background-color: {COLORS["accent_soft"]};
    selection-color: {COLORS["text"]};
    outline: none;
}}
QLabel#FieldLabel {{
    color: {COLORS["text_muted"]};
    font-size: 12px;
    font-weight: 500;
}}
QTableWidget {{
    background-color: {COLORS["surface"]};
    border: 1px solid {COLORS["border"]};
    border-radius: 10px;
    gridline-color: {COLORS["border"]};
    selection-background-color: {COLORS["accent_soft"]};
    selection-color: {COLORS["text"]};
    outline: none;
}}
QTableWidget::item {{
    padding: 8px 10px;
    border-bottom: 1px solid {COLORS["border"]};
}}
QHeaderView::section {{
    background-color: {COLORS["surface_alt"]};
    color: {COLORS["text_muted"]};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    padding: 10px 12px;
    border: none;
    border-bottom: 2px solid {COLORS["border"]};
}}
QScrollBar:vertical {{
    background: {COLORS["surface_alt"]};
    width: 10px;
    border-radius: 5px;
    margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS["border_strong"]};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: {COLORS["text_muted"]};
}}
#EmptyState {{
    color: {COLORS["text_muted"]};
    font-size: 14px;
    padding: 48px;
}}
QMessageBox {{
    background-color: {COLORS["surface"]};
}}
"""


def apply_app_theme(app: QApplication) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)
    font = QFont()
    if app.font().family():
        font.setFamily(app.font().family())
    font.setPointSize(10)
    app.setFont(font)
    palette = app.palette()
    palette.setColor(QPalette.Window, QColor(COLORS["bg"]))
    palette.setColor(QPalette.WindowText, QColor(COLORS["text"]))
    palette.setColor(QPalette.Base, QColor(COLORS["surface"]))
    palette.setColor(QPalette.AlternateBase, QColor(COLORS["surface_alt"]))
    palette.setColor(QPalette.Highlight, QColor(COLORS["primary"]))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    app.setPalette(palette)


def _bold_html(segment: str) -> str:
    def repl(m: re.Match) -> str:
        return f"<b style='color:{COLORS['text']}'>{m.group(1)}</b>"

    return re.sub(r"\*\*(.+?)\*\*", repl, segment)


def summary_to_html(text: str) -> str:
    """Light formatting for attention summary in the UI."""
    lines: list[str] = []
    for raw in text.split("\n"):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("### "):
            lines.append(
                f"<p style='margin:12px 0 6px;font-size:15px;font-weight:600;"
                f"color:{COLORS['text']}'>{line[4:]}</p>"
            )
        elif line.startswith("* "):
            body = _bold_html(line[2:])
            lines.append(
                f"<p style='margin:4px 0 4px 12px;color:{COLORS['text']};"
                f"line-height:1.45'>• {body}</p>"
            )
        else:
            lines.append(
                f"<p style='margin:4px 0;color:{COLORS['text_muted']};"
                f"line-height:1.45'>{_bold_html(line)}</p>"
            )
    return "".join(lines) if lines else "<p style='color:#64748b'>No summary yet.</p>"
