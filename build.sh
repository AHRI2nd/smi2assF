#!/usr/bin/env bash
set -euo pipefail

if [[ -x build/venv-py314/bin/python ]]; then
  VENV_PYTHON=build/venv-py314/bin/python
elif [[ -x build/venv-py314/Scripts/python.exe ]]; then
  VENV_PYTHON=build/venv-py314/Scripts/python.exe
else
  echo "Build environment not found. Run install.sh first." >&2
  exit 1
fi

"$VENV_PYTHON" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 14))'
"$VENV_PYTHON" -c 'import tkinter; import tkinterdnd2'
"$VENV_PYTHON" -m pytest -q

export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/build/pyinstaller-config}"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

OS_CLASSIFIER="$(./os_classifier.sh)"
PYINSTALLER_ARGS=(
  --noconfirm
  --clean
  --windowed
  --name smi2ass
  --collect-all tkinterdnd2
  --distpath build/gui-stage
  --workpath build/gui-work
  --specpath build/gui-spec
  smi2ass_gui.py
)

if [[ "$OS_CLASSIFIER" == windows-* ]]; then
  PYINSTALLER_ARGS+=(--icon assets/smi2ass.ico)
  "$VENV_PYTHON" -m PyInstaller --onefile "${PYINSTALLER_ARGS[@]}"
  mkdir -p build/gui-dist
  SMI2ASS_BIN="build/gui-dist/smi2ass.$OS_CLASSIFIER.exe"
  mv -f build/gui-stage/smi2ass.exe "$SMI2ASS_BIN"
  "$SMI2ASS_BIN" --smoke-test
  CHECKSUM_TARGET="$SMI2ASS_BIN"
elif [[ "$OS_CLASSIFIER" == osx-* ]]; then
  PYINSTALLER_ARGS+=(--icon assets/smi2ass.icns)
  "$VENV_PYTHON" -m PyInstaller --onedir --argv-emulation \
    --osx-bundle-identifier com.ahri2nd.smi2ass \
    "${PYINSTALLER_ARGS[@]}"
  mkdir -p build/gui-dist
  APP_PATH="build/gui-dist/smi2ass.$OS_CLASSIFIER.app"
  rm -rf "$APP_PATH"
  mv -f build/gui-stage/smi2ass.app "$APP_PATH"
  APP_EXECUTABLE="$APP_PATH/Contents/MacOS/smi2ass"
  "$APP_EXECUTABLE" --smoke-test
  DMG_PATH="build/gui-dist/smi2ass.$OS_CLASSIFIER.dmg"
  DMG_STAGE="build/gui-dmg-stage"
  rm -rf "$DMG_STAGE"
  mkdir -p "$DMG_STAGE"
  ditto "$APP_PATH" "$DMG_STAGE/smi2ass.app"
  hdiutil create \
    -volname smi2ass \
    -srcfolder "$DMG_STAGE" \
    -ov \
    -format UDZO \
    "$DMG_PATH"
  CHECKSUM_TARGET="$DMG_PATH"
else
  echo "Unsupported GUI build target: $OS_CLASSIFIER" >&2
  exit 1
fi

if command -v sha256sum >/dev/null 2>&1; then
  SHA256="$(sha256sum "$CHECKSUM_TARGET" | awk '{print $1}')"
else
  SHA256="$(shasum -a 256 "$CHECKSUM_TARGET" | awk '{print $1}')"
fi
printf '%s  %s\n' "$SHA256" "$(basename "$CHECKSUM_TARGET")" \
  > "$CHECKSUM_TARGET.sha256"
echo "SHA256: $SHA256 ($CHECKSUM_TARGET.sha256)"
echo "GUI build smoke test passed: $CHECKSUM_TARGET"
