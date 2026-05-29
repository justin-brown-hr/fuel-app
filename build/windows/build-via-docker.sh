#!/usr/bin/env bash
# Build FuelReconcile.exe on Linux/macOS using Wine-in-Docker (no Windows PC required).
# Requires: Docker (docker.io or Docker Desktop).
set -euo pipefail
cd "$(dirname "$0")/../.."
ROOT="$(pwd)"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found."
  echo "Install Docker, or build on Windows:  build\\windows\\build.bat"
  echo "Or push to GitHub and download artifact from Actions: Build Windows app"
  exit 1
fi

echo "=== Fuel Reconcile — Windows .exe via Docker ==="
echo "Project: $ROOT"

# Image runs Wine + PyInstaller; mounts repo at /src
docker pull batonogov/pyinstaller-windows:latest

docker run --rm \
  -v "$ROOT:/src" \
  -w /src \
  batonogov/pyinstaller-windows:latest \
  bash -lc "pip install -q -r requirements.txt -r requirements-build.txt && pyinstaller fuel_reconcile.spec --noconfirm --clean"

EXE="$ROOT/dist/FuelReconcile.exe"
if [[ ! -f "$EXE" ]]; then
  echo "ERROR: $EXE not found after build."
  exit 1
fi

ls -lh "$EXE"
echo ""
echo "Built: $EXE"
echo "Package: run build/windows/package-for-client.sh (or zip manually)"
