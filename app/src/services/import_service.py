from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Iterable

from src.db.database import Database
from src.importers import import_branch_litres, import_cars_plus, import_fuel_statement
from src.importers.utils import open_data_file
from src.matching import reconcile


@dataclass
class ImportResult:
    batch_id: int
    branch_litres_count: int = 0
    cars_plus_count: int = 0
    fuel_statement_count: int = 0
    unmatched_count: int = 0
    credits_skipped_branch: int = 0
    credits_skipped_statement: int = 0
    nonrev_skipped_branch: int = 0
    branches: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class ImportService:
    def __init__(self, db: Database | None = None):
        self.db = db or Database()

    def process_files(
        self,
        fuel_statement: Path | Iterable[Path] | None,
        branch_litres: Path | None,
        cars_plus: Path | None,
        label: str = "Import",
    ) -> ImportResult:
        batch_id = self.db.create_batch(label)
        self.db.clear_batch_data(batch_id)
        result = ImportResult(batch_id=batch_id)
        branch_rows = []
        cars_rows = []
        statement_rows = []

        try:
            if branch_litres and branch_litres.exists():
                branch_rows = import_branch_litres(open_data_file(branch_litres))
                self.db.save_branch_litres(batch_id, branch_rows)
                result.branch_litres_count = len(branch_rows)
        except Exception as e:
            result.errors.append(f"Branch litres: {e}")

        try:
            if cars_plus and cars_plus.exists():
                cars_rows = import_cars_plus(cars_plus)
                self.db.save_cars_plus(batch_id, cars_rows)
                result.cars_plus_count = len(cars_rows)
        except Exception as e:
            result.errors.append(f"Cars+: {e}")

        fuel_files: list[Path] = []
        if isinstance(fuel_statement, Path):
            fuel_files = [fuel_statement]
        elif fuel_statement:
            fuel_files = list(fuel_statement)

        for fuel_file in fuel_files:
            try:
                if fuel_file and fuel_file.exists():
                    statement_rows.extend(
                        import_fuel_statement(open_data_file(fuel_file))
                    )
            except Exception as e:
                result.errors.append(f"Fuel statement {fuel_file.name}: {e}")
        if statement_rows:
            self.db.save_fuel_statement(batch_id, statement_rows)
            result.fuel_statement_count = len(statement_rows)

        if branch_rows and (statement_rows or cars_rows):
            # If statement is missing (client waiting for it), still run Cars+ checks
            # and populate branch dropdown from imported data.
            recon = reconcile(branch_rows, statement_rows or [], cars_rows or None)
            self.db.save_unmatched(batch_id, recon.unmatched)
            result.unmatched_count = len(recon.unmatched)
            result.credits_skipped_branch = recon.credits_skipped_branch
            result.credits_skipped_statement = recon.credits_skipped_statement
            result.nonrev_skipped_branch = recon.nonrev_skipped_branch
            self.db.update_batch_credits(
                batch_id,
                recon.credits_skipped_branch,
                recon.credits_skipped_statement,
            )
            self.db.save_branch_summaries(batch_id, recon.branch_summaries)
        elif branch_rows and not statement_rows:
            result.errors.append(
                "Fuel statement required to match litres (branch sheet vs statement)."
            )

        result.branches = self.db.get_branches(batch_id)
        return result
