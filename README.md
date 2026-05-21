# Fuel Reconcile

Windows desktop app (Python) to reconcile fuel usage across three monthly files:

1. **Fuel statement** — Farmlands or Mobil PDF (or Excel)
2. **Branch litres** — Excel workbook with one sheet per branch
3. **Cars+ statement** — Excel export (reference; billing in dollars)

The app matches **litres on branch fuel sheets against litres on fuel statements**. Rows that do not match are flagged. **Credit fuel litres** (negative amounts or credit-related lines) are excluded and do not need to match.

## Requirements

- Python 3.10+
- Windows 10/11 for the packaged `.exe` (development can run on Linux/macOS with a display)

## Setup

```bash
cd fuel_app
pip install -r requirements.txt
```

## Run (development)

**GUI:**

```bash
python3 run.py
```

**Linux — if Qt fails with `libxcb-cursor.so.0`:**

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0
```

Then run `python3 run.py` again (needs a display, e.g. `DISPLAY=:0`).

**CLI (no GUI)** — useful on servers or when Qt libraries are missing:

```bash
python3 run.py --cli \
  --fuel "docs/Farmlands Statement April.PDF" \
  --branch "docs/branch litres.xlsx" \
  --cars "docs/cars+ statement.xlsx" \
  --branch-name Whangarei \
  --list-branches \
  --export /tmp/whangarei_report.pdf
```

Or with sample files from `docs/`:

1. Drop `Farmlands Statement April.PDF`, `branch litres.xlsx`, and `cars+ statement.xlsx`
2. Click **Import & reconcile**
3. Choose a branch and review unmatched litres
4. Click **Export PDF**

## Build Windows executable

On a Windows machine with Python installed:

```bash
pip install pyinstaller
pyinstaller --windowed --name FuelReconcile run.py
```

The executable will be under `dist/FuelReconcile/`. Test on a PC without Python installed.

## Project layout

```
src/
  importers/     # Parse Excel & PDF inputs
  matching/      # Reconcile litres (sheet vs statement)
  db/            # SQLite persistence
  reports/       # PDF export
  services/      # Import orchestration
  ui/            # PySide6 desktop UI
data/            # SQLite database (created at runtime)
docs/            # Client sample files
```

## Matching logic

- Compare **branch litres sheet** ↔ **fuel statement** per branch, primarily by **litres** (dates may differ between sources).
- When duplicate litre amounts exist, the closest date is preferred.
- **Credits** (negative litres on the statement) appear in the report as “Credit/reversal entry” and are excluded from the matched count.
- Per-branch summary (like `docs/refer_value.md`):
  - Total statement fill-ups
  - Matched count
  - Genuine missing vs credit reversals
- **Cars+** is stored for reference in PDF export only.

## Notes for production

- PDF export layout can be adjusted to match Mobil/Farmlands stationery in `src/reports/pdf_export.py`.
- Add more branch sheets or location codes in `src/config.py` as needed.
