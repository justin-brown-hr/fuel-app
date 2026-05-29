@echo off
setlocal EnableExtensions EnableDelayedExpansion

:: Double-click: keep window open so errors are visible
if /I not "%~1"=="_run" (
    cmd /k "%~f0" _run
    exit /b %ERRORLEVEL%
)

cd /d "%~dp0\..\.."
set "LOG=%~dp0build.log"

echo === Fuel Reconcile - Windows build (single .exe) ===
echo Project: %CD%
echo Log: %LOG%
echo.

call :main >> "%LOG%" 2>&1
set "ERR=!ERRORLEVEL!"

type "%LOG%"
echo.

if !ERR! neq 0 goto :failed
goto :done

:main
if not exist "app\run.py" (
    echo ERROR: app\run.py not found.
    echo Run from the fuel_app folder ^(must contain app\ and fuel_reconcile.spec^).
    exit /b 1
)

set "PY="
where python >nul 2>&1 && set "PY=python"
if not defined PY where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    echo ERROR: Python not found.
    echo Install from https://www.python.org/ and tick "Add python.exe to PATH".
    echo Then open a NEW Command Prompt and try again.
    exit /b 1
)

echo Using: %PY%
%PY% --version
if errorlevel 1 exit /b 1

if not exist ".venv\Scripts\python.exe" (
    echo Creating virtual environment...
    %PY% -m venv .venv
    if errorlevel 1 exit /b 1
)

set "VPY=%CD%\.venv\Scripts\python.exe"
if not exist "%VPY%" (
    echo ERROR: Missing %VPY%
    exit /b 1
)

echo Installing dependencies...
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
"%VPY%" -m pip install -r requirements.txt -r requirements-build.txt
if errorlevel 1 exit /b 1

echo Running PyInstaller ^(5-15 minutes^)...
"%VPY%" -m PyInstaller fuel_reconcile.spec --noconfirm --clean
if errorlevel 1 exit /b 1

set "EXE=%CD%\dist\FuelReconcile.exe"
if not exist "%EXE%" (
    echo ERROR: %EXE% was not created.
    exit /b 1
)

for %%A in ("%EXE%") do echo Built: %%~fA  ^(%%~zA bytes^)
exit /b 0

:failed
echo ========================================
echo  BUILD FAILED
echo  Log: %LOG%
echo ========================================
echo.
echo Try:  build\windows\BUILD_ON_WINDOWS.txt
echo.
pause
exit /b 1

:done
echo === Build complete ===
echo   %CD%\dist\FuelReconcile.exe
echo.
echo Optional: build\windows\package-for-client.bat
echo.
pause
exit /b 0
