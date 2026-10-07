#!/usr/bin/env bash
set -euo pipefail

PRODUCT_NAME="smi2assF"
OS_CLASSIFIER="$(./os_classifier.sh)"

VENV_PYTHON=""
if [[ "$OS_CLASSIFIER" == windows-* ]]; then
  VENV_CANDIDATES=(build/venv-py313 build/venv-py314)
else
  VENV_CANDIDATES=(build/venv-py314 build/venv-py313)
fi
for VENV_DIR in "${VENV_CANDIDATES[@]}"; do
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    VENV_PYTHON="$VENV_DIR/bin/python"
    break
  elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
    break
  fi
done
if [[ -z "$VENV_PYTHON" ]]; then
  echo "Build environment not found. Run install.sh first." >&2
  exit 1
fi

"$VENV_PYTHON" -c 'import sys; raise SystemExit(sys.version_info.major != 3 or sys.version_info.minor not in (13, 14))'
"$VENV_PYTHON" -c 'import tkinter; import tkinterdnd2'
"$VENV_PYTHON" -m pytest -q

export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/build/pyinstaller-config}"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

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
  PAYLOAD_PATH="build/gui-stage/$PRODUCT_NAME.exe"
  "$VENV_PYTHON" scripts/run_with_timeout.py --timeout-seconds 60 --label "payload smoke" -- \
    "$PAYLOAD_PATH" --smoke-test
  if ! command -v ISCC.exe >/dev/null 2>&1; then
    echo "Inno Setup compiler ISCC.exe is required to build the Windows installer." >&2
    exit 1
  fi
  INSTALLER_PATH="build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.exe"
  rm -f "$INSTALLER_PATH" "$INSTALLER_PATH.sha256"
  "$VENV_PYTHON" scripts/run_with_timeout.py --timeout-seconds 120 --label "installer compile" -- \
    ISCC.exe scripts/windows-installer.iss
  test -s "$INSTALLER_PATH"

  INSTALL_SMOKE_DIR="$PWD/build/installer-smoke"
  INSTALL_SMOKE_DIR_WIN="$(cygpath -w "$INSTALL_SMOKE_DIR")"
  rm -rf "$INSTALL_SMOKE_DIR"
  mkdir -p "$INSTALL_SMOKE_DIR"
  echo "[build] Installer install diagnostics: $INSTALL_SMOKE_DIR/install.log"
  "$VENV_PYTHON" scripts/run_with_timeout.py --timeout-seconds 120 --label "installer install" -- \
    "$INSTALLER_PATH" /SP- /VERYSILENT /SUPPRESSMSGBOXES /NORESTART \
    "/LOG=$INSTALL_SMOKE_DIR/install.log" "/DIR=$INSTALL_SMOKE_DIR_WIN"
  test -s "$INSTALL_SMOKE_DIR/$PRODUCT_NAME.exe"
  "$VENV_PYTHON" scripts/run_with_timeout.py --timeout-seconds 60 --label "installed app smoke" -- \
    "$INSTALL_SMOKE_DIR/$PRODUCT_NAME.exe" --smoke-test
  "$VENV_PYTHON" scripts/run_with_timeout.py --timeout-seconds 60 --label "uninstall" -- \
    "$INSTALL_SMOKE_DIR/unins000.exe" /VERYSILENT /SUPPRESSMSGBOXES /NORESTART
  if [[ -e "$INSTALL_SMOKE_DIR" ]]; then
    echo "Windows installer smoke test left files after uninstall." >&2
    exit 1
  fi
  CHECKSUM_TARGET="$INSTALLER_PATH"
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
