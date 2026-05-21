# Fuel Reconcile — Windows (one file)

## What the client gets

**One program:** `FuelReconcile.exe` (inside `FuelReconcile-Client.zip`)

No `_internal` folder. No extra DLLs to copy.

## How to run

1. **Extract** the ZIP (if you received a zip).
2. Put **`FuelReconcile.exe`** on Desktop or Documents.
3. **Do not** run it from inside WinRAR/7-Zip (causes `python311.dll` errors).
4. Double-click **`FuelReconcile.exe`**.
5. First start can take **20–40 seconds** — wait for the window.

## If Windows blocks it

SmartScreen: **More info** → **Run anyway**

## If `python311.dll` / module not found

- Save/extract the `.exe` first, then run from Desktop.
- Install [Visual C++ Redistributable x64](https://aka.ms/v1/vc/Redist.x64)

## Data saved on this PC

`%LOCALAPPDATA%\FuelReconcile\fuel_app.db`

## For the developer (build)

```bat
build\windows\build.bat
build\windows\package-for-client.bat
```

Send `dist\FuelReconcile-Client.zip` or the `.exe` alone (after telling client to extract if zipped).

The `.exe` is large (~150–350 MB) because it includes Python and Qt — that is normal.
