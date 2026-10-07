#!/usr/bin/env bash
set -euo pipefail

PRODUCT_NAME="smi2assF"

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
mkdir -p build/gui-dist
rm -rf build/gui-dist/smi2ass.*
PYINSTALLER_ARGS=(
  --noconfirm
  --clean
  --windowed
  --name "$PRODUCT_NAME"
  --collect-all tkinterdnd2
  --distpath build/gui-stage
  --workpath build/gui-work
  --specpath build/gui-spec
  smi2ass_gui.py
)

if [[ "$OS_CLASSIFIER" == windows-* ]]; then
  ICON_PATH="$("$VENV_PYTHON" scripts/build_icon_path.py "$OS_CLASSIFIER")"
  PYINSTALLER_ARGS+=(--icon "$ICON_PATH")
  "$VENV_PYTHON" -m PyInstaller --onefile "${PYINSTALLER_ARGS[@]}"
  mkdir -p build/gui-dist
  APP_EXECUTABLE="build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.exe"
  mv -f "build/gui-stage/$PRODUCT_NAME.exe" "$APP_EXECUTABLE"
  "$APP_EXECUTABLE" --smoke-test
  CHECKSUM_TARGET="$APP_EXECUTABLE"
elif [[ "$OS_CLASSIFIER" == osx-* ]]; then
  ICON_PATH="$("$VENV_PYTHON" scripts/build_icon_path.py "$OS_CLASSIFIER")"
  PYINSTALLER_ARGS+=(--icon "$ICON_PATH")
  "$VENV_PYTHON" -m PyInstaller --onedir --argv-emulation \
    --osx-bundle-identifier com.ahri2nd.smi2assf \
    "${PYINSTALLER_ARGS[@]}"
  mkdir -p build/gui-dist
  APP_PATH="build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.app"
  rm -rf "$APP_PATH"
  mv -f "build/gui-stage/$PRODUCT_NAME.app" "$APP_PATH"
  APP_EXECUTABLE="$APP_PATH/Contents/MacOS/$PRODUCT_NAME"
  "$APP_EXECUTABLE" --smoke-test
  DMG_PATH="build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.dmg"
  DMG_STAGE="build/gui-dmg-stage"
  rm -rf "$DMG_STAGE"
  mkdir -p "$DMG_STAGE"
  ditto "$APP_PATH" "$DMG_STAGE/$PRODUCT_NAME.app"
  hdiutil create \
    -volname "$PRODUCT_NAME" \
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
