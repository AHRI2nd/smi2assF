#!/usr/bin/env bash
set -euo pipefail

PRODUCT_NAME="smi2assF"
OS_CLASSIFIER="$(./os_classifier.sh)"
MACOS_RELEASE_SIGNING="${MACOS_RELEASE_SIGNING:-0}"
if [[ "$OS_CLASSIFIER" == osx-* && "${GITHUB_ACTIONS:-false}" == true && "$MACOS_RELEASE_SIGNING" != 1 ]]; then
  echo "A GitHub macOS package build requires MACOS_RELEASE_SIGNING=1." >&2
  exit 1
fi
if [[ "$OS_CLASSIFIER" == osx-* && "$MACOS_RELEASE_SIGNING" == 1 ]]; then
  for SETTING in MACOS_CODESIGN_IDENTITY MACOS_EXPECTED_TEAM_ID MACOS_SIGNING_KEYCHAIN MACOS_NOTARY_PROFILE; do
    if [[ -z "${!SETTING:-}" ]]; then
      echo "Missing macOS release signing setting: $SETTING" >&2
      exit 1
    fi
  done
fi

source scripts/python_runtime.sh
select_python_version "$OS_CLASSIFIER"
select_venv_python
if [[ "$OS_CLASSIFIER" == osx-* ]]; then
  "$VENV_PYTHON" scripts/report_runtime.py -ApplePersistenceIgnoreState YES -NSQuitAlwaysKeepsWindows NO
  # Cocoa arguments affect this test process only; preserve user preferences.
  "$VENV_PYTHON" -c 'import pytest; raise SystemExit(pytest.main(["-q", "-W", "error", "-rs"]))' \
    -ApplePersistenceIgnoreState YES -NSQuitAlwaysKeepsWindows NO
else
  "$VENV_PYTHON" scripts/report_runtime.py
  "$VENV_PYTHON" -m pytest -q -W error -rs
fi

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
  "$VENV_PYTHON" -m scripts.windows_installer_build "$OS_CLASSIFIER"
  test -s "$INSTALLER_PATH"

  "$VENV_PYTHON" -m scripts.windows_installer_smoke "$INSTALLER_PATH"
  CHECKSUM_TARGET="$INSTALLER_PATH"
elif [[ "$OS_CLASSIFIER" == osx-* ]]; then
  DMG_PATH="build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.dmg"
  rm -f "$DMG_PATH" "$DMG_PATH.sha256"
  ICON_PATH="$("$VENV_PYTHON" scripts/build_icon_path.py "$OS_CLASSIFIER")"
  PYINSTALLER_ARGS+=(--icon "$ICON_PATH")
  if [[ "$MACOS_RELEASE_SIGNING" == 1 ]]; then
    PYINSTALLER_ARGS+=(--codesign-identity "$MACOS_CODESIGN_IDENTITY")
  fi
  "$VENV_PYTHON" -m PyInstaller --onedir --argv-emulation \
    --osx-bundle-identifier com.ahri2nd.smi2assf \
    "${PYINSTALLER_ARGS[@]}"
  mkdir -p build/gui-dist
  APP_PATH="build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.app"
  rm -rf "$APP_PATH"
  mv -f "build/gui-stage/$PRODUCT_NAME.app" "$APP_PATH"
  APP_EXECUTABLE="$APP_PATH/Contents/MacOS/$PRODUCT_NAME"
  "$APP_EXECUTABLE" --smoke-test
  if [[ "$MACOS_RELEASE_SIGNING" == 1 ]]; then
    "$VENV_PYTHON" -m scripts.macos_signing app "$APP_PATH"
  fi
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
  if [[ "$MACOS_RELEASE_SIGNING" == 1 ]]; then
    "$VENV_PYTHON" -m scripts.macos_signing dmg "$DMG_PATH"
  fi
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
