@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

echo === Fuel Reconcile - Windows build ===
echo Project: %CD%

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

echo Running PyInstaller...
pyinstaller fuel_reconcile.spec --noconfirm --clean
if errorlevel 1 exit /b 1

set DIST=%CD%\dist\FuelReconcile
if not exist "%DIST%\FuelReconcile.exe" (
    echo ERROR: Build failed - FuelReconcile.exe not found.
    exit /b 1
)

copy /Y "docs\USER_GUIDE.md" "%DIST%\README.txt" >nul 2>&1
copy /Y "docs\WINDOWS_INSTALL.md" "%DIST%\INSTALL.txt" >nul 2>&1
echo.
echo === Build complete ===
echo Run:  "%DIST%\FuelReconcile.exe"
echo Zip the whole folder "dist\FuelReconcile" and send to the client.
echo Database is stored in: %%LOCALAPPDATA%%\FuelReconcile\fuel_app.db
echo.
pause
