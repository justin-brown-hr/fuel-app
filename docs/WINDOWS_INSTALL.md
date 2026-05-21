# Fuel Reconcile — Windows install (for client)

## What you receive

A folder named **FuelReconcile** containing:

- **FuelReconcile.exe** — double-click to open the app
- Other files — required by the app; **keep them in the same folder**
- **README.txt** — short usage guide

Do not move only the `.exe` file; the whole folder must stay together.

## First run

1. Unzip the folder (e.g. to `Desktop\FuelReconcile`).
2. Double-click **FuelReconcile.exe**.
3. If Windows SmartScreen appears: click **More info** → **Run anyway** (the app is not signed with a commercial certificate).

## Monthly workflow

1. Open **Fuel Reconcile**.
2. Drag your three files onto the window:
   - Farmlands (or Mobil) fuel statement **PDF**
   - **Branch litres** Excel workbook
   - **Cars+** statement Excel (optional but recommended)
3. Click **Import & reconcile**.
4. Choose the **branch** (e.g. Whangarei).
5. Review the action items in the table.
6. Click **Export PDF** and save the report.

## Where data is stored

Import history is saved on this PC at:

`%LOCALAPPDATA%\FuelReconcile\fuel_app.db`

(Usually: `C:\Users\<YourName>\AppData\Local\FuelReconcile\`)

Re-importing creates a new batch; older imports remain in the dropdown.

## Files needed each month

| File | Example name |
|------|----------------|
| Fuel statement | `Farmlands Statement April.PDF` |
| Branch litres | `branch litres.xlsx` |
| Cars+ | `cars+ statement.xlsx` |

## Support

Contact your developer to add branches, fix statement formats, or rebuild the app.
