# Fuel Reconcile — Windows build (PowerShell)
$ErrorActionPreference = "Stop"
Set-Location (Join-Path $PSScriptRoot "..\..")

Write-Host "=== Fuel Reconcile - Windows build ===" -ForegroundColor Cyan
Write-Host "Project: $(Get-Location)"

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

$dist = Join-Path (Get-Location) "dist\FuelReconcile"
$exe = Join-Path $dist "FuelReconcile.exe"
if (-not (Test-Path $exe)) {
    throw "Build failed: $exe not found"
}

Copy-Item "docs\USER_GUIDE.md" (Join-Path $dist "README.txt") -Force -ErrorAction SilentlyContinue
Copy-Item "docs\WINDOWS_INSTALL.md" (Join-Path $dist "INSTALL.txt") -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "=== Build complete ===" -ForegroundColor Green
Write-Host "Run:  $exe"
Write-Host "Zip folder: $dist"
Write-Host "Data folder: $env:LOCALAPPDATA\FuelReconcile"
