from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.config import APP_NAME, APP_VERSION
from src.db.database import Database
from src.reports.attention import (
    attention_rows_for_table,
    format_attention_summary_text,
)
from src.reports.pdf_export import export_branch_pdf
from src.services.import_service import ImportService
from src.ui.theme import summary_to_html


class DropZone(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("DropZone")
        self.setAcceptDrops(True)
        self.setProperty("hasFiles", False)
        self.setProperty("dragActive", False)
        self.dropped_paths: list[Path] = []

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(6)

        self.title = QLabel("Drop monthly files here")
        self.title.setObjectName("DropZoneTitle")
        self.title.setAlignment(Qt.AlignCenter)
        self.hint = QLabel(
            "Fuel statement (PDF) · Branch litres (Excel) · Cars+ (Excel)"
        )
        self.hint.setAlignment(Qt.AlignCenter)
        self.hint.setWordWrap(True)
        self.files = QLabel("")
        self.files.setAlignment(Qt.AlignCenter)
        self.files.setWordWrap(True)
        self.files.hide()

        layout.addWidget(self.title)
        layout.addWidget(self.hint)
        layout.addWidget(self.files)

        self._set_idle_text()

    def _set_idle_text(self) -> None:
        self.title.setText("Drop monthly files here")
        self.hint.setText(
            "Fuel statement (PDF) · Branch litres (Excel) · Cars+ (Excel)"
        )
        self.hint.show()
        self.files.hide()
        self.setProperty("hasFiles", False)
        self._repolish()

    def _repolish(self) -> None:
        style = self.style()
        style.unpolish(self)
        style.polish(self)

    def _show_files(self, paths: list[Path]) -> None:
        self.title.setText(f"{len(paths)} file(s) ready")
        self.hint.hide()
        self.files.setText("\n".join(f"✓  {p.name}" for p in paths))
        self.files.show()
        self.setProperty("hasFiles", True)
        self._repolish()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            self.setProperty("dragActive", True)
            self._repolish()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self.setProperty("dragActive", False)
        self._repolish()
        super().dragLeaveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        self.setProperty("dragActive", False)
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_file():
                paths.append(p)
        if paths:
            self.dropped_paths = paths
            self._show_files(paths)
        self._repolish()
        event.acceptProposedAction()


def _classify_file(path: Path) -> str | None:
    name = path.name.lower()
    if "litre" in name or "liters" in name or "branch" in name:
        return "branch"
    if "cars" in name or "car+" in name:
        return "cars"
    if path.suffix.lower() in (".pdf", ".xlsx", ".xls"):
        if "statement" in name or "farmlands" in name or "mobil" in name or "fuel" in name:
            return "fuel"
        if path.suffix.lower() == ".pdf":
            return "fuel"
    if path.suffix.lower() in (".xlsx", ".xls"):
        return "branch"
    return None


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        self.resize(1100, 760)
        self.setMinimumSize(900, 600)
        self.db = Database()
        self.import_service = ImportService(self.db)
        self.current_batch_id: int | None = None
        self._build_ui()

    def _card(self, title: str) -> tuple[QFrame, QVBoxLayout]:
        frame = QFrame()
        frame.setObjectName("Card")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(14)
        heading = QLabel(title)
        heading.setObjectName("CardTitle")
        layout.addWidget(heading)
        return frame, layout

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(24, 24, 24, 24)
        root.setSpacing(16)

        header = QFrame()
        header.setObjectName("AppHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 14, 20, 14)
        title_block = QVBoxLayout()
        title_block.setSpacing(2)
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        subtitle = QLabel(f"Fuel reconciliation · v{APP_VERSION}")
        subtitle.setObjectName("AppSubtitle")
        title_block.addWidget(title)
        title_block.addWidget(subtitle)
        header_layout.addLayout(title_block)
        header_layout.addStretch()
        root.addWidget(header)

        import_card, import_layout = self._card("Import data")
        self.drop_zone = DropZone()
        self.drop_zone.setMinimumHeight(140)
        import_layout.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)
        browse_btn = QPushButton("Browse files")
        browse_btn.clicked.connect(self._browse_files)
        import_btn = QPushButton("Import && reconcile")
        import_btn.setObjectName("PrimaryButton")
        import_btn.setCursor(Qt.PointingHandCursor)
        import_btn.clicked.connect(self._run_import)
        browse_btn.setCursor(Qt.PointingHandCursor)
        btn_row.addWidget(browse_btn)
        btn_row.addWidget(import_btn)
        btn_row.addStretch()
        import_layout.addLayout(btn_row)
        root.addWidget(import_card)

        self.status_label = QLabel("Ready — add your three files, then import.")
        self.status_label.setObjectName("StatusPill")
        self.status_label.setWordWrap(True)
        root.addWidget(self.status_label)

        review_card, review_layout = self._card("Review && export")

        controls = QHBoxLayout()
        controls.setSpacing(16)

        batch_col = QVBoxLayout()
        batch_col.setSpacing(4)
        batch_lbl = QLabel("Import batch")
        batch_lbl.setObjectName("FieldLabel")
        self.batch_combo = QComboBox()
        self.batch_combo.currentIndexChanged.connect(self._on_batch_changed)
        batch_col.addWidget(batch_lbl)
        batch_col.addWidget(self.batch_combo)
        controls.addLayout(batch_col, 2)

        branch_col = QVBoxLayout()
        branch_col.setSpacing(4)
        branch_lbl = QLabel("Branch")
        branch_lbl.setObjectName("FieldLabel")
        self.branch_combo = QComboBox()
        self.branch_combo.currentTextChanged.connect(self._load_branch_table)
        branch_col.addWidget(branch_lbl)
        branch_col.addWidget(self.branch_combo)
        controls.addLayout(branch_col, 1)

        export_col = QVBoxLayout()
        export_col.setSpacing(4)
        export_col.addWidget(QLabel(""))
        export_btn = QPushButton("Export PDF")
        export_btn.setObjectName("AccentButton")
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_pdf)
        export_col.addWidget(export_btn)
        controls.addLayout(export_col, 0)
        review_layout.addLayout(controls)

        self.summary_label = QLabel()
        self.summary_label.setObjectName("SummaryPanel")
        self.summary_label.setWordWrap(True)
        self.summary_label.setTextFormat(Qt.RichText)
        self.summary_label.setText(
            "<p style='color:#64748b'>Import files to see the action summary.</p>"
        )
        self.summary_label.setMinimumHeight(80)
        review_layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setMinimumHeight(220)
        review_layout.addWidget(self.table, 1)

        self.empty_label = QLabel(
            "No action items yet.\n"
            "Import your files and select a branch to see follow-ups."
        )
        self.empty_label.setObjectName("EmptyState")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.empty_label.hide()
        review_layout.addWidget(self.empty_label)

        root.addWidget(review_card, 1)
        self._refresh_batches()

    def _browse_files(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files",
            str(Path.home()),
            "Data files (*.pdf *.xlsx *.xls);;All files (*)",
        )
        if paths:
            self.drop_zone.dropped_paths = [Path(p) for p in paths]
            self.drop_zone._show_files(self.drop_zone.dropped_paths)

    def _assign_files(self, paths: list[Path]) -> tuple[Path | None, Path | None, Path | None]:
        fuel, branch, cars = None, None, None
        for p in paths:
            kind = _classify_file(p)
            if kind == "fuel" and fuel is None:
                fuel = p
            elif kind == "branch" and branch is None:
                branch = p
            elif kind == "cars" and cars is None:
                cars = p
        remaining = [p for p in paths if p not in (fuel, branch, cars)]
        for p in remaining:
            if p.suffix.lower() == ".pdf" and fuel is None:
                fuel = p
            elif "litre" in p.name.lower() and branch is None:
                branch = p
            elif cars is None and p.suffix.lower() in (".xlsx", ".xls"):
                if branch is None:
                    branch = p
                else:
                    cars = p
        return fuel, branch, cars

    def _run_import(self) -> None:
        paths = self.drop_zone.dropped_paths
        if not paths:
            QMessageBox.warning(self, "No files", "Drop or browse for files first.")
            return
        fuel, branch, cars = self._assign_files(paths)
        missing = []
        if not branch:
            missing.append("branch litres (.xlsx)")
        if not cars:
            missing.append("cars+ statement (.xlsx)")
        if not fuel:
            missing.append("fuel statement (.pdf/.xlsx)")
        if missing:
            QMessageBox.warning(
                self,
                "Missing files",
                "Could not identify:\n• " + "\n• ".join(missing)
                + "\n\nRename files or drop all three together.",
            )
            if not branch or not cars:
                return

        label = f"Import {paths[0].parent.name}"
        self.status_label.setText("Importing and reconciling…")
        result = self.import_service.process_files(fuel, branch, cars, label=label)
        self.current_batch_id = result.batch_id
        self._refresh_batches()
        self.batch_combo.setCurrentIndex(0)

        credits_total = result.credits_skipped_branch + result.credits_skipped_statement
        self.status_label.setText(
            f"Import complete · {result.branch_litres_count} branch rows · "
            f"{result.fuel_statement_count} statement lines · "
            f"{result.cars_plus_count} Cars+ charges · "
            f"{result.unmatched_count} flags · "
            f"{credits_total} credits skipped"
        )
        if result.errors:
            self.status_label.setText(
                self.status_label.text() + " · Warnings: " + "; ".join(result.errors)
            )
        self.branch_combo.clear()
        self.branch_combo.addItems(result.branches)
        if result.branches:
            self._load_branch_table()

    def _refresh_batches(self) -> None:
        self.batch_combo.blockSignals(True)
        self.batch_combo.clear()
        for b in self.db.list_batches():
            self.batch_combo.addItem(f"{b.label} ({b.created_at})", b.id)
        self.batch_combo.blockSignals(False)
        if self.batch_combo.count() and self.current_batch_id is None:
            self.current_batch_id = self.batch_combo.currentData()

    def _on_batch_changed(self) -> None:
        self.current_batch_id = self.batch_combo.currentData()
        if self.current_batch_id:
            cb, cs = self.db.get_batch_credits(self.current_batch_id)
            self.status_label.setText(
                f"Viewing batch · {cb + cs} credit lines skipped "
                f"(sheet {cb}, statement {cs})"
            )
            branches = self.db.get_branches(self.current_batch_id)
            self.branch_combo.clear()
            self.branch_combo.addItems(branches)
            if branches:
                self._load_branch_table()

    def _load_branch_table(self) -> None:
        if not self.current_batch_id or not self.branch_combo.currentText():
            return
        report = self.db.get_branch_report(
            self.current_batch_id, self.branch_combo.currentText()
        )
        self.summary_label.setText(summary_to_html(format_attention_summary_text(report)))

        rows = attention_rows_for_table(report)
        headers = ["Type", "Date", "Litres", "RA / fuel", "Action"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        has_rows = bool(rows)
        self.table.setVisible(has_rows)
        self.empty_label.setVisible(not has_rows)

        for i, r in enumerate(rows):
            vals = [
                r["category"],
                r["transaction_date"],
                f"{r['litres']:.2f}L",
                r.get("detail") or "",
                r.get("action") or "",
            ]
            for j, v in enumerate(vals):
                item = QTableWidgetItem(str(v))
                if j == 0:
                    item.setForeground(Qt.darkBlue)
                self.table.setItem(i, j, item)
        self.table.resizeColumnsToContents()
        if self.table.columnCount() > 4:
            self.table.setColumnWidth(4, max(self.table.columnWidth(4), 280))

    def _export_pdf(self) -> None:
        if not self.current_batch_id or not self.branch_combo.currentText():
            QMessageBox.warning(self, "Export", "Select a batch and branch first.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save branch report",
            f"fuel_report_{self.branch_combo.currentText()}.pdf",
            "PDF (*.pdf)",
        )
        if not path:
            return
        report = self.db.get_branch_report(
            self.current_batch_id, self.branch_combo.currentText()
        )
        try:
            export_branch_pdf(report, Path(path))
            QMessageBox.information(self, "Export", f"Saved:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))
