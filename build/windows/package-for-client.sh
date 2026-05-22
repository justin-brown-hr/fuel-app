#!/usr/bin/env bash
# Create dist/FuelReconcile-Client.zip after build (Linux/macOS).
set -euo pipefail
cd "$(dirname "$0")/../.."
EXE="dist/FuelReconcile.exe"
if [[ ! -f "$EXE" ]]; then
  echo "Run build first: build/windows/build-via-docker.sh or build.bat on Windows"
  exit 1
fi
STAGE="dist/client_package"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp "$EXE" "$STAGE/"
cp build/windows/START_HERE.txt "$STAGE/"
cp docs/WINDOWS_INSTALL.md "$STAGE/INSTALL.txt"
ZIP="dist/FuelReconcile-Client.zip"
rm -f "$ZIP"
(cd "$STAGE" && zip -r "../FuelReconcile-Client.zip" .)
rm -rf "$STAGE"
ls -lh "$ZIP"
echo "Client package: $ZIP"
