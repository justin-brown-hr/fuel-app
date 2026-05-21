@echo off
setlocal EnableExtensions
cd /d "%~dp0\..\.."

set EXE=%CD%\dist\FuelReconcile.exe
if not exist "%EXE%" (
    echo Run build.bat first.
    exit /b 1
)

set STAGE=%CD%\dist\client_package
if exist "%STAGE%" rmdir /s /q "%STAGE%"
mkdir "%STAGE%"

copy /Y "%EXE%" "%STAGE%\FuelReconcile.exe" >nul
copy /Y "build\windows\START_HERE.txt" "%STAGE%\START_HERE.txt" >nul
copy /Y "docs\WINDOWS_INSTALL.md" "%STAGE%\INSTALL.txt" >nul

set ZIP=%CD%\dist\FuelReconcile-Client.zip
if exist "%ZIP%" del "%ZIP%"

powershell -NoProfile -Command "Compress-Archive -Path '%STAGE%\*' -DestinationPath '%ZIP%' -Force"
if errorlevel 1 (
    echo ZIP failed. Send dist\FuelReconcile.exe directly.
    exit /b 1
)

rmdir /s /q "%STAGE%"

echo.
echo === Client package ready ===
echo   %ZIP%
echo   Contains: FuelReconcile.exe + START_HERE.txt
echo.
echo Client: Extract zip -^> run FuelReconcile.exe (not from inside WinRAR)
echo.
pause
