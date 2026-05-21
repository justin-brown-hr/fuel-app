from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QDragEnterEvent, QDropEvent
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGroupBox,
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
from src.reports.branch_summary import format_branch_summary_text
from src.reports.pdf_export import export_branch_pdf
from src.services.import_service import ImportService


class DropZone(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setAlignment(Qt.AlignCenter)
        self.setText(
            "Drag & drop files here\n"
            "(fuel statement PDF/Excel, branch litres .xlsx, cars+ .xlsx)\n"
            "or use Browse"
        )
        self.setStyleSheet(
            "QLabel { border: 2px dashed #7f8c8d; border-radius: 8px; "
            "padding: 24px; color: #566573; background: #f8f9fa; }"
        )
        self.setMinimumHeight(120)
        self.dropped_paths: list[Path] = []

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = []
        for url in event.mimeData().urls():
            p = Path(url.toLocalFile())
            if p.is_file():
                paths.append(p)
        if paths:
            self.dropped_paths = paths
            names = "\n".join(p.name for p in paths)
            self.setText(f"Dropped {len(paths)} file(s):\n{names}")
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
        self.resize(1000, 700)
        self.db = Database()
        self.import_service = ImportService(self.db)
        self.current_batch_id: int | None = None
        self._build_ui()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        btn_row = QHBoxLayout()
        browse_btn = QPushButton("Browse files…")
        browse_btn.clicked.connect(self._browse_files)
        import_btn = QPushButton("Import & reconcile")
        import_btn.setStyleSheet("font-weight: bold;")
        import_btn.clicked.connect(self._run_import)
        btn_row.addWidget(browse_btn)
        btn_row.addWidget(import_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.status_label = QLabel("Ready — drop three files or browse, then import.")
        layout.addWidget(self.status_label)

        batch_box = QGroupBox("Import history")
        batch_layout = QHBoxLayout(batch_box)
        self.batch_combo = QComboBox()
        self.batch_combo.currentIndexChanged.connect(self._on_batch_changed)
        batch_layout.addWidget(QLabel("Batch:"))
        batch_layout.addWidget(self.batch_combo, 1)
        layout.addWidget(batch_box)

        branch_row = QHBoxLayout()
        branch_row.addWidget(QLabel("Branch:"))
        self.branch_combo = QComboBox()
        self.branch_combo.currentTextChanged.connect(self._load_branch_table)
        branch_row.addWidget(self.branch_combo, 1)
        export_btn = QPushButton("Export PDF")
        export_btn.clicked.connect(self._export_pdf)
        branch_row.addWidget(export_btn)
        layout.addLayout(branch_row)

        self.summary_label = QLabel("")
        self.summary_label.setWordWrap(True)
        self.summary_label.setStyleSheet(
            "QLabel { background: #eef2f3; padding: 10px; border-radius: 6px; }"
        )
        layout.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table, 1)

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
            self.drop_zone.setText(
                f"Selected {len(paths)} file(s):\n" + "\n".join(Path(p).name for p in paths)
            )

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
        # Fallback: assign by extension order if names unclear
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
        result = self.import_service.process_files(fuel, branch, cars, label=label)
        self.current_batch_id = result.batch_id
        self._refresh_batches()
        self.batch_combo.setCurrentIndex(0)

        credits_total = result.credits_skipped_branch + result.credits_skipped_statement
        msg = (
            f"Branch litres: {result.branch_litres_count} | "
            f"Cars+: {result.cars_plus_count} | "
            f"Statement: {result.fuel_statement_count} | "
            f"Unmatched: {result.unmatched_count} | "
            f"NONREV skipped: {result.nonrev_skipped_branch} | "
            f"Credits skipped: {credits_total} "
            f"(sheet {result.credits_skipped_branch}, "
            f"statement {result.credits_skipped_statement})"
        )
        if result.errors:
            msg += "\nWarnings: " + "; ".join(result.errors)
        self.status_label.setText(msg)
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
                f"Credits skipped (this import): {cb + cs} "
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
        stmt_um = report.get("unmatched_statement_stage2", report.get("unmatched_statement", []))
        stmt_um = [r for r in stmt_um if not r.get("is_credit")]

        self.summary_label.setText(format_branch_summary_text(report))

        rows = stmt_um if stmt_um else report.get("litres", [])
        if stmt_um:
            headers = ["Date", "Litres", "Fuel type", "Notes"]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                vals = [
                    r["transaction_date"],
                    f"{r['litres']:.2f}L",
                    r.get("fuel_type") or "",
                    r.get("reason", ""),
                ]
                for j, v in enumerate(vals):
                    self.table.setItem(i, j, QTableWidgetItem(str(v)))
        else:
            headers = ["Date", "RA #", "Vehicle", "Litres", "Time"]
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(rows))
            for i, r in enumerate(rows):
                vals = [
                    r["transaction_date"],
                    r.get("ra_number", ""),
                    r.get("vehicle_label", ""),
                    f"{r['litres']:.2f}",
                    r.get("time") or "",
                ]
                for j, v in enumerate(vals):
                    self.table.setItem(i, j, QTableWidgetItem(str(v)))

        cars_um = report.get("unmatched_cars_plus", [])
        extra = []
        if branch_um:
            extra.append(f"Stage 2 branch-only: {len(branch_um)}")
        if cars_um:
            extra.append(f"Cars+ not charged: {len(cars_um)}")
        s1_miss = report.get("unmatched_statement_stage1", [])
        s1_genuine = [r for r in s1_miss if not r.get("is_credit")]
        if s1_genuine:
            extra.append(f"Stage 1 stmt missing (incl. NONREV check): {len(s1_genuine)}")
        if extra:
            self.summary_label.setText(
                self.summary_label.text() + "\n\n" + " | ".join(extra) + " (see PDF)"
            )
        self.table.resizeColumnsToContents()

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
