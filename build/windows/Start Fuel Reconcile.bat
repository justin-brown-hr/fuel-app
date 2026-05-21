@echo off
setlocal EnableExtensions
cd /d "%~dp0"

title Fuel Reconcile

if not exist "%~dp0FuelReconcile.exe" (
    echo.
    echo  ERROR: FuelReconcile.exe not found in this folder.
    echo  Extract the full ZIP to a folder such as Desktop\FuelReconcile
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0_internal\" (
    echo.
    echo  ERROR: The _internal folder is missing.
    echo.
    echo  You must extract the ENTIRE FuelReconcile folder from the ZIP.
    echo  Do not run the .exe from inside WinRAR or from email preview.
    echo.
    echo  See START_HERE.txt for instructions.
    echo.
    pause
    exit /b 1
)

if not exist "%~dp0_internal\python311.dll" (
    if not exist "%~dp0_internal\python3*.dll" (
        echo.
        echo  ERROR: Python support files are missing from _internal.
        echo  Extract the full ZIP again or re-download the package.
        echo.
        pause
        exit /b 1
    )
)

start "" "%~dp0FuelReconcile.exe"
