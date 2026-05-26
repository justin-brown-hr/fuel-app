# Fuel Reconcile — User Guide

## What this app does

Import your monthly files and compare **fuel card litres** to **branch tab litres**. The report lists **only items that need attention** (missing card lines, tab-only rows, Cars+ not charged at your branch location).

## Files to import

| File | Description |
|------|-------------|
| Fuel statement(s) | Farmlands and/or Mobil PDFs (monthly card statements with litres). Import all statement PDFs for the month, e.g. Farmlands plus `Mobile - Taupo.pdf`. |
| Branch litres | Excel workbook with one sheet per branch (e.g. Taupo, Kerikeri, Whangarei) |
| Cars+ statement | Excel export from Cars+ (recommended for billing check) |

At least one **fuel statement** and **branch litres** are required for reconciliation.

## Steps

1. Open **Fuel Reconcile** (`FuelReconcile.exe` on Windows).
2. Drag all monthly files onto the drop zone (or **Browse files**): all fuel statements, branch litres, and Cars+.
3. Click **Import & reconcile**.
4. Select a **branch** from the dropdown.
5. Review the action-items table (Type, Date, Litres, RA, Action).
6. Click **Export PDF** to save the branch report.

## Understanding the PDF

1. **Fuel card not on branch tab** — On Farmlands/Mobil but not on the branch spreadsheet (incl. NONREV check).
2. **Branch tab without card** — On the spreadsheet but no matching card line.
3. **Cars+ billing** — Operational fill not charged on Cars+ at confirmed client locations only.

Summary at the top shows how many card lines matched; tables list follow-ups only.

## Credits

Negative litres / credit reversals on the statement are noted in the summary but are not listed as action items.

## Tips

- Use clear file names (e.g. `branch litres.xlsx`, `Farmlands Statement April.PDF`).
- Re-importing creates a new batch in **Import history**; older batches stay in the dropdown.
- On Windows, data is saved under `%LOCALAPPDATA%\FuelReconcile\`.

## Support

Contact your developer for new branches, statement formats, or app updates.
