# Fuel Reconcile — User Guide

## What this app does

Import your monthly files and compare **fuel card litres** to **branch tab litres**. The report lists **only items that need attention** (missing card lines, tab-only rows, Cars+ not charged at your branch location).

## Files to import

| File | Description |
|------|-------------|
| Fuel statement | Farmlands or Mobil PDF (monthly card statement with litres) |
| Branch litres | Excel workbook with one sheet per branch (e.g. Taupo, Kerikeri, Whangarei) |
| Cars+ statement | Excel export from Cars+ (recommended for billing check) |

**Fuel statement** and **branch litres** are required for reconciliation.

## Steps

1. Open **Fuel Reconcile** (`FuelReconcile.exe` on Windows).
2. Drag all three files onto the drop zone (or **Browse files**).
3. Click **Import & reconcile**.
4. Select a **branch** from the dropdown.
5. Review the action-items table (Type, Date, Litres, RA, Action).
6. Click **Export PDF** to save the branch report.

## Understanding the PDF

1. **Fuel card not on branch tab** — On Farmlands/Mobil but not on the branch spreadsheet (incl. NONREV check).
2. **Branch tab without card** — On the spreadsheet but no matching card line.
3. **Cars+ not billed at WHN/WNU** (for Whangarei) — Operational fill not charged on Cars+ at that branch’s location codes only (not Auckland, Taupo, etc.).

Summary at the top shows how many card lines matched; tables list follow-ups only.

## Credits

Negative litres / credit reversals on the statement are noted in the summary but are not listed as action items.

## Tips

- Use clear file names (e.g. `branch litres.xlsx`, `Farmlands Statement April.PDF`).
- Re-importing creates a new batch in **Import history**; older batches stay in the dropdown.
- On Windows, data is saved under `%LOCALAPPDATA%\FuelReconcile\`.

## Support

Contact your developer for new branches, statement formats, or app updates.
