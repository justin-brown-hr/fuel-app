# Fuel Reconcile — User Guide

## What this app does

Import your monthly files and check that **litres on branch fuel sheets match litres on fuel card statements**. Cars+ billing is shown for reference. Export a PDF per branch for follow-up.

## Files to import

| File | Description |
|------|-------------|
| Fuel statement | Farmlands or Mobil PDF (monthly card statement with litres) |
| Branch litres | Excel workbook with one sheet per branch (e.g. Taupo, Kerikeri) |
| Cars+ statement | Excel export from Cars+ (optional for cross-reference) |

**Fuel statement is required** for reconciliation.

## Steps

1. Open **Fuel Reconcile**.
2. Drag all three files onto the drop zone (or **Browse files**).
3. Click **Import & reconcile**.
4. Select a **branch** from the dropdown to review unmatched litres.
5. Click **Export PDF** to save a branch report.

## Understanding results

- **Unmatched litres** — A row on the branch sheet has no matching litres on the fuel statement (same branch, date, and amount), or the other way around.
- **Credits skipped** — Negative litres or credit/rebate/payment lines are ignored and do not need to match. The status bar shows how many were excluded (branch sheet vs statement).
- **Branch sheet / Statement / Cars+** — Row counts for the selected branch.

## Tips

- Use clear file names (e.g. `branch litres.xlsx`, `Farmlands Statement April.PDF`) so the app assigns files correctly.
- Re-importing creates a new batch in **Import history**; older batches remain available.

## Support

Matching rules and PDF layout can be adjusted in the source code. Contact your developer for new branches or statement formats.
