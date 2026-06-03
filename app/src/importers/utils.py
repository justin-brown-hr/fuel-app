import re
import shutil
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional


def open_data_file(path: Path) -> Path:
    """
    Return a path pandas can read. Copies to temp if the file is locked
    (e.g. OneDrive / Excel open / Permission denied).
    """
    path = Path(path)
    try:
        with path.open("rb"):
            return path
    except OSError:
        dest = Path(tempfile.gettempdir()) / f"fuel_reconcile_{path.name}"
        shutil.copy2(path, dest)
        return dest


def normalize_ra(value) -> str:
    if value is None:
        return ""
    s = str(value).strip().upper()
    if re.fullmatch(r"\d+\.0+", s):
        s = str(int(float(s)))
    s = re.sub(r"[^A-Z0-9]", "", s)
    return s


def parse_excel_date(value, default_year: int = 2026) -> Optional[date]:
    if value is None or (isinstance(value, float) and str(value) == "nan"):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            serial = int(value)
            if serial > 40000:
                return (datetime(1899, 12, 30) + timedelta(days=serial)).date()
        except (ValueError, OverflowError):
            pass
    s = str(value).strip()
    m = re.match(r"^(\d{1,2})/(\d{1,2})$", s)
    if m:
        day, month = int(m.group(1)), int(m.group(2))
        return date(default_year, month, day)
    m = re.match(r"^(\d{1,2})/(\d{1,2})/(\d{2,4})$", s)
    if m:
        day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if year < 100:
            year += 2000
        return date(year, month, day)
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d %b %y", "%d %b %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_time(value) -> Optional[str]:
    if value is None or str(value).strip() in ("", "?", "nan"):
        return None
    if isinstance(value, float) and str(value) == "nan":
        return None
    s = str(value).strip().replace(".0", "")
    if re.fullmatch(r"\d{3,4}", s):
        s = s.zfill(4)
        return f"{s[:2]}:{s[2:]}"
    if re.fullmatch(r"\d{1,2}:\d{2}", s):
        return s
    m = re.search(r"(\d{1,2}):(\d{2})", s)
    if m:
        return f"{int(m.group(1)):02d}:{m.group(2)}"
    return None


def safe_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        f = float(value)
        if f != f:
            return None
        return f
    except (TypeError, ValueError):
        return None
