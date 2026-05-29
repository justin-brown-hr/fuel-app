# Fuel Reconcile

Windows desktop app (Python) to reconcile fuel usage across monthly files:

1. **Fuel statement(s)** — Farmlands and/or Mobil PDFs (or Excel)
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

**GUI** (from the `app` folder):

```bash
cd app
PYTHONPATH=. python3 run.py
```

**Linux — if Qt fails with `libxcb-cursor.so.0`:**

```bash
sudo apt install libxcb-cursor0 libxkbcommon-x11-0
```

Then run `python3 run.py` again (needs a display, e.g. `DISPLAY=:0`).

**CLI (no GUI)** — useful on servers or when Qt libraries are missing:

```bash
cd app
PYTHONPATH=. python3 run.py --cli \
  --fuel "../docs/Farmlands Statement April.PDF" "../docs/Mobile - Taupo.pdf" \
  --branch "../docs/branch litres.xlsx" \
  --cars "../docs/cars+ statement.xlsx" \
  --branch-name Whangarei \
  --list-branches \
  --export /tmp/whangarei_report.pdf
```

Or with sample files from `docs/`:

1. Drop `Farmlands Statement April.PDF`, `Mobile - Taupo.pdf`, `branch litres.xlsx`, and `cars+ statement.xlsx`
2. Click **Import & reconcile**
3. Choose a branch and review unmatched litres
4. Click **Export PDF**

## Build Windows executable (for client)

**Must be built on Windows** (PyInstaller cannot cross-compile the GUI from Linux).

### Option A — double-click build script

1. Install [Python 3.10+](https://www.python.org/downloads/) and tick **Add python.exe to PATH**.
2. Run `build\windows\build.bat` (creates **one** `dist\FuelReconcile.exe`).
3. Run `build\windows\package-for-client.bat` → sends `FuelReconcile-Client.zip`.

**Client needs only `FuelReconcile.exe`** after extracting the zip (not the old folder with `_internal`). First launch may take ~30 seconds.

### Option B — manual commands

```bat
cd fuel_app
pip install -r requirements.txt -r requirements-build.txt
pyinstaller fuel_reconcile.spec --noconfirm --clean
```

Entry script for the build is `app\run.py` (configured in `fuel_reconcile.spec`).

Output: `dist\FuelReconcile.exe` (single file, ~150–350 MB)

### Client cannot run? (`python311.dll` error)

They ran the `.exe` **from inside RAR/ZIP** without saving it. Fix: **Extract All** → put `FuelReconcile.exe` on Desktop → run again. See `docs/WINDOWS_INSTALL.md`.

### GitHub Actions

Push to `main` or run the **Build Windows app** workflow manually. Download the **FuelReconcile-Windows** artifact (zip of `dist/FuelReconcile`).

### Packaged app data

On Windows, the SQLite database is stored at `%LOCALAPPDATA%\FuelReconcile\fuel_app.db` (not beside the `.exe`), so imports persist across updates.

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

## Matching logic (three checks)

1. **Stage 1** — Branch tab **including NONREV** vs fuel statement (litres). NONREV rows (e.g. 8.89L on 9 Apr) match statement lines that were wrongly flagged before.
2. **Stage 2** — **Operational** branch tab only (NONREV excluded) vs fuel statement — use for “missing on WHN tab” follow-up.
3. **Cars+** — Branch tab **RA numbers** vs Cars+ fuel charges within the date window, using only confirmed client locations on **RA Loc Out or RA Loc In**: Kerikeri, Whangarei, Rotorua, Taupo, Whanganui/Wanganui, and Mount Maunganui/Tauranga (Z Hewletts Rd). National locations such as Auckland/Wellington are ignored.

Dates may differ between sheet and statement; matching is primarily by **litres** within the branch.

## Notes for production

- PDF export layout can be adjusted to match Mobil/Farmlands stationery in `src/reports/pdf_export.py`.
- Add more branch sheets or location codes in `src/config.py` as needed.
