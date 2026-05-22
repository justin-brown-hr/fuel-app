import json
import sqlite3
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any

from src.config import DATA_DIR, DB_PATH, cars_row_at_branch_location
from src.matching.credits import is_credit_litres
from src.matching.reconcile import BranchSummary
from src.models import BranchLitresRow, CarsPlusRow, FuelStatementRow, UnmatchedLitres


def _serialize(obj: Any) -> str:
    if isinstance(obj, (date, datetime)):
        return obj.isoformat()
    return str(obj)


class ImportBatch:
    def __init__(
        self,
        batch_id: int,
        created_at: str,
        label: str,
        credits_skipped_branch: int = 0,
        credits_skipped_statement: int = 0,
    ):
        self.id = batch_id
        self.created_at = created_at
        self.label = label
        self.credits_skipped_branch = credits_skipped_branch
        self.credits_skipped_statement = credits_skipped_statement


class Database:
    def __init__(self, path: Path = DB_PATH):
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS import_batches (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    label TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS branch_litres (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    vehicle_label TEXT,
                    ra_number TEXT NOT NULL,
                    transaction_date TEXT NOT NULL,
                    litres REAL NOT NULL,
                    time TEXT,
                    amount REAL,
                    FOREIGN KEY (batch_id) REFERENCES import_batches(id)
                );
                CREATE TABLE IF NOT EXISTS cars_plus (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    ra_loc_out TEXT,
                    ra_loc_in TEXT,
                    ra_number TEXT NOT NULL,
                    transaction_date TEXT NOT NULL,
                    time TEXT,
                    fuel_charge REAL NOT NULL,
                    fuel_type TEXT,
                    FOREIGN KEY (batch_id) REFERENCES import_batches(id)
                );
                CREATE TABLE IF NOT EXISTS fuel_statement (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    transaction_date TEXT NOT NULL,
                    time TEXT,
                    supplier TEXT,
                    litres REAL NOT NULL,
                    product TEXT,
                    total_incl_gst REAL,
                    card_or_invoice TEXT,
                    vehicle_name TEXT,
                    ra_number TEXT,
                    FOREIGN KEY (batch_id) REFERENCES import_batches(id)
                );
                CREATE TABLE IF NOT EXISTS unmatched (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    ra_number TEXT NOT NULL,
                    vehicle_label TEXT,
                    transaction_date TEXT NOT NULL,
                    litres REAL NOT NULL,
                    time TEXT,
                    reason TEXT NOT NULL,
                    FOREIGN KEY (batch_id) REFERENCES import_batches(id)
                );
                CREATE INDEX IF NOT EXISTS idx_bl_batch_branch
                    ON branch_litres(batch_id, branch);
                CREATE INDEX IF NOT EXISTS idx_cp_batch_branch
                    ON cars_plus(batch_id, branch);
                CREATE TABLE IF NOT EXISTS attention_overrides (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    batch_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    item_key TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    note TEXT,
                    UNIQUE(batch_id, branch, item_key),
                    FOREIGN KEY (batch_id) REFERENCES import_batches(id)
                );
                CREATE TABLE IF NOT EXISTS branch_summaries (
                    batch_id INTEGER NOT NULL,
                    branch TEXT NOT NULL,
                    statement_total INTEGER NOT NULL DEFAULT 0,
                    matched_count INTEGER NOT NULL DEFAULT 0,
                    statement_unmatched_count INTEGER NOT NULL DEFAULT 0,
                    branch_unmatched_count INTEGER NOT NULL DEFAULT 0,
                    credit_reversal_count INTEGER NOT NULL DEFAULT 0,
                    genuine_missing_count INTEGER NOT NULL DEFAULT 0,
                    stage1_matched INTEGER DEFAULT 0,
                    stage1_statement_total INTEGER DEFAULT 0,
                    stage1_genuine_missing INTEGER DEFAULT 0,
                    stage2_matched INTEGER DEFAULT 0,
                    stage2_statement_total INTEGER DEFAULT 0,
                    stage2_genuine_missing INTEGER DEFAULT 0,
                    cars_plus_unbilled INTEGER DEFAULT 0,
                    nonrev_row_count INTEGER DEFAULT 0,
                    PRIMARY KEY (batch_id, branch)
                );
                """
            )
            self._migrate_schema(conn)

    def _migrate_schema(self, conn: sqlite3.Connection) -> None:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS attention_overrides (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id INTEGER NOT NULL,
                branch TEXT NOT NULL,
                item_key TEXT NOT NULL,
                created_at TEXT NOT NULL,
                note TEXT,
                UNIQUE(batch_id, branch, item_key),
                FOREIGN KEY (batch_id) REFERENCES import_batches(id)
            )
            """
        )
        cols = {r[1] for r in conn.execute("PRAGMA table_info(unmatched)").fetchall()}
        if "source" not in cols:
            conn.execute(
                "ALTER TABLE unmatched ADD COLUMN source TEXT DEFAULT 'branch_sheet'"
            )
        if "supplier" not in cols:
            conn.execute("ALTER TABLE unmatched ADD COLUMN supplier TEXT")
        batch_cols = {r[1] for r in conn.execute("PRAGMA table_info(import_batches)").fetchall()}
        if "credits_skipped_branch" not in batch_cols:
            conn.execute(
                "ALTER TABLE import_batches ADD COLUMN credits_skipped_branch INTEGER DEFAULT 0"
            )
        if "credits_skipped_statement" not in batch_cols:
            conn.execute(
                "ALTER TABLE import_batches ADD COLUMN credits_skipped_statement INTEGER DEFAULT 0"
            )
        um_cols = {r[1] for r in conn.execute("PRAGMA table_info(unmatched)").fetchall()}
        if "fuel_type" not in um_cols:
            conn.execute("ALTER TABLE unmatched ADD COLUMN fuel_type TEXT")
        if "is_credit" not in um_cols:
            conn.execute(
                "ALTER TABLE unmatched ADD COLUMN is_credit INTEGER DEFAULT 0"
            )
        if "stage" not in um_cols:
            conn.execute(
                "ALTER TABLE unmatched ADD COLUMN stage TEXT DEFAULT 'stage2'"
            )
        if "is_nonrev" not in um_cols:
            conn.execute(
                "ALTER TABLE unmatched ADD COLUMN is_nonrev INTEGER DEFAULT 0"
            )
        bl_cols = {r[1] for r in conn.execute("PRAGMA table_info(branch_litres)").fetchall()}
        if "is_nonrev" not in bl_cols:
            conn.execute(
                "ALTER TABLE branch_litres ADD COLUMN is_nonrev INTEGER DEFAULT 0"
            )
        bs_cols = {r[1] for r in conn.execute("PRAGMA table_info(branch_summaries)").fetchall()}
        for col in (
            "stage1_matched",
            "stage1_statement_total",
            "stage1_genuine_missing",
            "stage2_matched",
            "stage2_statement_total",
            "stage2_genuine_missing",
            "cars_plus_unbilled",
            "nonrev_row_count",
        ):
            if col not in bs_cols:
                conn.execute(
                    f"ALTER TABLE branch_summaries ADD COLUMN {col} INTEGER DEFAULT 0"
                )

    def update_batch_credits(
        self, batch_id: int, credits_branch: int, credits_statement: int
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE import_batches
                SET credits_skipped_branch = ?, credits_skipped_statement = ?
                WHERE id = ?
                """,
                (credits_branch, credits_statement, batch_id),
            )

    def add_attention_override(
        self, batch_id: int, branch: str, item_key: str, note: str = ""
    ) -> None:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO attention_overrides
                (batch_id, branch, item_key, created_at, note)
                VALUES (?, ?, ?, ?, ?)
                """,
                (batch_id, branch, item_key, now, note),
            )

    def get_attention_override_keys(self, batch_id: int, branch: str) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT item_key FROM attention_overrides
                WHERE batch_id = ? AND branch = ?
                """,
                (batch_id, branch),
            ).fetchall()
        return [r[0] for r in rows]

    def get_batch_credits(self, batch_id: int) -> tuple[int, int]:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT credits_skipped_branch, credits_skipped_statement
                FROM import_batches WHERE id = ?
                """,
                (batch_id,),
            ).fetchone()
        if not row:
            return (0, 0)
        return (row[0] or 0, row[1] or 0)

    def create_batch(self, label: str) -> int:
        now = datetime.now().isoformat(timespec="seconds")
        with self._connect() as conn:
            cur = conn.execute(
                "INSERT INTO import_batches (created_at, label) VALUES (?, ?)",
                (now, label),
            )
            return int(cur.lastrowid)

    def list_batches(self) -> list[ImportBatch]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT id, created_at, label,
                       credits_skipped_branch, credits_skipped_statement
                FROM import_batches ORDER BY id DESC
                """
            ).fetchall()
        return [
            ImportBatch(
                r["id"],
                r["created_at"],
                r["label"],
                r["credits_skipped_branch"] or 0,
                r["credits_skipped_statement"] or 0,
            )
            for r in rows
        ]

    def clear_batch_data(self, batch_id: int) -> None:
        with self._connect() as conn:
            for table in (
                "branch_litres",
                "cars_plus",
                "fuel_statement",
                "unmatched",
                "branch_summaries",
                "attention_overrides",
            ):
                conn.execute(f"DELETE FROM {table} WHERE batch_id = ?", (batch_id,))

    def save_branch_summaries(
        self, batch_id: int, summaries: dict[str, BranchSummary]
    ) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT OR REPLACE INTO branch_summaries
                (batch_id, branch, statement_total, matched_count,
                 statement_unmatched_count, branch_unmatched_count,
                 credit_reversal_count, genuine_missing_count,
                 stage1_matched, stage1_statement_total, stage1_genuine_missing,
                 stage2_matched, stage2_statement_total, stage2_genuine_missing,
                 cars_plus_unbilled, nonrev_row_count)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        batch_id,
                        s.branch,
                        s.stage2.statement_total,
                        s.stage2.matched_count,
                        s.stage2.statement_unmatched_count,
                        s.stage2.branch_unmatched_count,
                        s.stage2.credit_reversal_count,
                        s.stage2.genuine_missing_count,
                        s.stage1.matched_count,
                        s.stage1.statement_total,
                        s.stage1.genuine_missing_count,
                        s.stage2.matched_count,
                        s.stage2.statement_total,
                        s.stage2.genuine_missing_count,
                        s.cars_plus_unbilled,
                        s.nonrev_row_count,
                    )
                    for s in summaries.values()
                ],
            )

    def get_branch_summary(self, batch_id: int, branch: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT statement_total, matched_count, statement_unmatched_count,
                       branch_unmatched_count, credit_reversal_count, genuine_missing_count,
                       stage1_matched, stage1_statement_total, stage1_genuine_missing,
                       stage2_matched, stage2_statement_total, stage2_genuine_missing,
                       cars_plus_unbilled, nonrev_row_count
                FROM branch_summaries WHERE batch_id = ? AND branch = ?
                """,
                (batch_id, branch),
            ).fetchone()
        if not row:
            return None
        return {
            "statement_total": row[0],
            "matched_count": row[1],
            "statement_unmatched_count": row[2],
            "branch_unmatched_count": row[3],
            "credit_reversal_count": row[4],
            "genuine_missing_count": row[5],
            "stage1": {
                "matched_count": row[6],
                "statement_total": row[7],
                "genuine_missing_count": row[8],
            },
            "stage2": {
                "matched_count": row[9],
                "statement_total": row[10],
                "genuine_missing_count": row[11],
            },
            "cars_plus_unbilled": row[12],
            "nonrev_row_count": row[13],
        }

    def save_branch_litres(self, batch_id: int, rows: list[BranchLitresRow]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO branch_litres
                (batch_id, branch, vehicle_label, ra_number, transaction_date,
                 litres, time, amount, is_nonrev)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        batch_id,
                        r.branch,
                        r.vehicle_label,
                        r.ra_number,
                        r.transaction_date.isoformat(),
                        r.litres,
                        r.time,
                        r.amount,
                        1 if r.is_nonrev else 0,
                    )
                    for r in rows
                ],
            )

    def save_cars_plus(self, batch_id: int, rows: list[CarsPlusRow]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO cars_plus
                (batch_id, branch, ra_loc_out, ra_loc_in, ra_number,
                 transaction_date, time, fuel_charge, fuel_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        batch_id,
                        r.branch,
                        r.ra_loc_out,
                        r.ra_loc_in,
                        r.ra_number,
                        r.transaction_date.isoformat(),
                        r.time,
                        r.fuel_charge,
                        r.fuel_type,
                    )
                    for r in rows
                ],
            )

    def save_fuel_statement(self, batch_id: int, rows: list[FuelStatementRow]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO fuel_statement
                (batch_id, branch, transaction_date, time, supplier, litres,
                 product, total_incl_gst, card_or_invoice, vehicle_name, ra_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        batch_id,
                        r.branch,
                        r.transaction_date.isoformat(),
                        r.time,
                        r.supplier,
                        r.litres,
                        r.product,
                        r.total_incl_gst,
                        r.card_or_invoice,
                        r.vehicle_name,
                        r.ra_number,
                    )
                    for r in rows
                ],
            )

    def save_unmatched(self, batch_id: int, rows: list[UnmatchedLitres]) -> None:
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO unmatched
                (batch_id, branch, ra_number, vehicle_label, transaction_date,
                 litres, time, reason, source, supplier, fuel_type, is_credit,
                 stage, is_nonrev)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        batch_id,
                        r.branch,
                        r.ra_number,
                        r.vehicle_label,
                        r.transaction_date.isoformat(),
                        r.litres,
                        r.time,
                        r.reason,
                        r.source,
                        r.supplier,
                        r.fuel_type,
                        1 if r.is_credit else 0,
                        r.stage,
                        1 if r.is_nonrev else 0,
                    )
                    for r in rows
                ],
            )

    def get_branches(self, batch_id: int) -> list[str]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT DISTINCT branch FROM branch_litres WHERE batch_id = ?
                UNION
                SELECT DISTINCT branch FROM cars_plus WHERE batch_id = ?
                UNION
                SELECT DISTINCT branch FROM fuel_statement WHERE batch_id = ?
                ORDER BY branch
                """,
                (batch_id, batch_id, batch_id),
            ).fetchall()
        return [r[0] for r in rows if r[0]]

    def get_branch_report(self, batch_id: int, branch: str) -> dict[str, Any]:
        with self._connect() as conn:
            litres = conn.execute(
                """
                SELECT vehicle_label, ra_number, transaction_date, litres, time
                FROM branch_litres WHERE batch_id = ? AND branch = ?
                ORDER BY transaction_date, ra_number
                """,
                (batch_id, branch),
            ).fetchall()
            billed = conn.execute(
                """
                SELECT ra_number, ra_loc_out, ra_loc_in, transaction_date, time,
                       fuel_charge, fuel_type
                FROM cars_plus WHERE batch_id = ?
                ORDER BY transaction_date, ra_number
                """,
                (batch_id,),
            ).fetchall()
            statement = conn.execute(
                """
                SELECT transaction_date, time, supplier, litres, product,
                       total_incl_gst, vehicle_name, ra_number
                FROM fuel_statement WHERE batch_id = ? AND branch = ?
                ORDER BY transaction_date
                """,
                (batch_id, branch),
            ).fetchall()
            unmatched = conn.execute(
                """
                SELECT ra_number, vehicle_label, transaction_date, litres, time,
                       reason, source, supplier, fuel_type, is_credit, stage, is_nonrev
                FROM unmatched WHERE batch_id = ? AND branch = ?
                ORDER BY stage, transaction_date
                """,
                (batch_id, branch),
            ).fetchall()
            cars_imported_total = conn.execute(
                "SELECT COUNT(*) FROM cars_plus WHERE batch_id = ?",
                (batch_id,),
            ).fetchone()[0]
            cars_branch_rows = conn.execute(
                "SELECT ra_loc_out, ra_loc_in FROM cars_plus WHERE batch_id = ?",
                (batch_id,),
            ).fetchall()

        credits_branch = sum(1 for r in litres if is_credit_litres(r["litres"]))
        credits_statement = sum(
            1
            for r in statement
            if is_credit_litres(
                r["litres"],
                product=r["product"] or "",
                supplier=r["supplier"] or "",
            )
        )

        um_list = [dict(r) for r in unmatched]

        def _filter(stage: str, source: str) -> list[dict]:
            return [
                u
                for u in um_list
                if u.get("stage") == stage and u.get("source") == source
            ]

        stmt_s1 = _filter("stage1", "fuel_statement")
        stmt_s2 = _filter("stage2", "fuel_statement")
        branch_s2 = _filter("stage2", "branch_sheet")
        cars_um = _filter("cars_plus", "cars_plus")

        summary = self.get_branch_summary(batch_id, branch) or {}

        cars_at_branch_loc = sum(
            1
            for r in cars_branch_rows
            if cars_row_at_branch_location(
                r["ra_loc_out"] or "", branch, r["ra_loc_in"] or ""
            )
        )

        billed_at_branch = [
            dict(r)
            for r in billed
            if cars_row_at_branch_location(
                r["ra_loc_out"] or "", branch, r["ra_loc_in"] or ""
            )
        ]

        override_keys = self.get_attention_override_keys(batch_id, branch)

        return {
            "branch": branch,
            "batch_id": batch_id,
            "litres": [dict(r) for r in litres],
            "billed": billed_at_branch,
            "statement": [dict(r) for r in statement],
            "unmatched": um_list,
            "unmatched_statement_stage1": stmt_s1,
            "unmatched_statement_stage2": stmt_s2,
            "unmatched_statement": stmt_s2,
            "unmatched_branch": branch_s2,
            "unmatched_cars_plus": cars_um,
            "attention_override_keys": override_keys,
            "credits_skipped_branch": credits_branch,
            "credits_skipped_statement": credits_statement,
            "nonrev_skipped_branch": summary.get("nonrev_row_count", 0),
            "cars_plus_imported_total": cars_imported_total,
            "cars_plus_at_branch_loc": cars_at_branch_loc,
            "summary": summary,
        }
