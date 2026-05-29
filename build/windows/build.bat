@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

echo === Fuel Reconcile - Windows build (single .exe) ===
echo Project: %CD%

if not exist "app\run.py" (
    echo ERROR: app\run.py not found. Open this repo folder (fuel_app), not app\ only.
    exit /b 1
)

where python >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Install Python 3.10+ from https://www.python.org/
    echo        Tick "Add python.exe to PATH" during setup.
    exit /b 1
)

python --version
if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    python -m venv .venv
)
call .venv\Scripts\activate.bat

echo Installing dependencies...
python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt

echo Running PyInstaller (one-file .exe, may take several minutes)...
pyinstaller fuel_reconcile.spec --noconfirm --clean
if errorlevel 1 exit /b 1

set EXE=%CD%\dist\FuelReconcile.exe
if not exist "%EXE%" (
    echo ERROR: Build failed - dist\FuelReconcile.exe not found.
    exit /b 1
)

for %%A in ("%EXE%") do echo Built: %%~fA  (%%~zA bytes)

echo.
echo === Build complete ===
echo Client needs ONLY:  dist\FuelReconcile.exe
echo.
echo Next:  build\windows\package-for-client.bat  (makes zip for email)
echo.
echo Tell client: extract zip, put exe on Desktop, double-click.
echo First launch is slow (~30 sec). Data: %%LOCALAPPDATA%%\FuelReconcile\
echo.
pause
