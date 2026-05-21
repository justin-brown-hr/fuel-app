# Fuel Reconcile — Windows build (single .exe)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\..")

Write-Host "=== Fuel Reconcile - Windows build (single .exe) ===" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found. Install Python 3.10+ and add it to PATH."
}

python --version

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}
& .\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt -r requirements-build.txt

pyinstaller fuel_reconcile.spec --noconfirm --clean

$exe = Join-Path (Get-Location) "dist\FuelReconcile.exe"
if (-not (Test-Path $exe)) {
    throw "Build failed: $exe not found"
}

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Client file: $exe"
Write-Host "Size: $([math]::Round((Get-Item $exe).Length / 1MB, 1)) MB"
Write-Host "Package: build\windows\package-for-client.bat"
