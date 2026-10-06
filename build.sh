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
"$VENV_PYTHON" -m pytest -q

export PYINSTALLER_CONFIG_DIR="${PYINSTALLER_CONFIG_DIR:-$PWD/build/pyinstaller-config}"
mkdir -p "$PYINSTALLER_CONFIG_DIR"

"$VENV_PYTHON" -m PyInstaller \
  --noconfirm \
  --console \
  --onefile \
  --name smi2ass \
  --distpath build/dist \
  --workpath build/work \
  --specpath build \
  smi2ass.py

OS_CLASSIFIER="$(./os_classifier.sh)"
if [[ -f build/dist/smi2ass.exe ]]; then
  SMI2ASS_BIN="build/dist/smi2ass.$OS_CLASSIFIER.exe"
  mv -f build/dist/smi2ass.exe "$SMI2ASS_BIN"
else
  SMI2ASS_BIN="build/dist/smi2ass.$OS_CLASSIFIER"
  mv -f build/dist/smi2ass "$SMI2ASS_BIN"
fi

if command -v sha256sum >/dev/null 2>&1; then
  SHA256="$(sha256sum "$SMI2ASS_BIN" | awk '{print $1}')"
else
  SHA256="$(shasum -a 256 "$SMI2ASS_BIN" | awk '{print $1}')"
fi
printf '%s\n' "$SHA256" > "$SMI2ASS_BIN.sha256"
echo "SHA256: $SHA256 ($SMI2ASS_BIN.sha256)"

mkdir -p build/smoke
cp tests/fixtures/minimal.smi build/smoke/input.smi
"$SMI2ASS_BIN" build/smoke/input.smi
grep -Fq 'Build smoke test' build/smoke/input.kor.ass
echo "Executable smoke test passed: $SMI2ASS_BIN"
