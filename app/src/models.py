from dataclasses import dataclass
from datetime import date, datetime
from typing import Optional


@dataclass
class BranchLitresRow:
    branch: str
    vehicle_label: str
    ra_number: str
    transaction_date: date
    litres: float
    time: Optional[str] = None
    amount: Optional[float] = None
    day_of_month: Optional[int] = None
    is_nonrev: bool = False


@dataclass
class CarsPlusRow:
    branch: str
    ra_loc_out: str
    ra_loc_in: str
    ra_number: str
    transaction_date: date
    time: str
    fuel_charge: float
    fuel_type: str


@dataclass
class FuelStatementRow:
    branch: str
    transaction_date: date
    time: Optional[str]
    supplier: str
    litres: float
    product: str
    total_incl_gst: Optional[float]
    card_or_invoice: str
    vehicle_name: Optional[str] = None
    ra_number: Optional[str] = None


@dataclass
class UnmatchedLitres:
    branch: str
    ra_number: str
    vehicle_label: str
    transaction_date: date
    litres: float
    time: Optional[str]
    reason: str
    source: str = "branch_sheet"  # branch_sheet | fuel_statement
    supplier: Optional[str] = None
    fuel_type: Optional[str] = None
    is_credit: bool = False
    stage: str = "stage2"  # stage1 | stage2 | cars_plus
    is_nonrev: bool = False
