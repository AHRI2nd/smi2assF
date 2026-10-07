#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif command -v python3.14 >/dev/null 2>&1; then
  PYTHON_BIN=python3.14
else
  PYTHON_BIN=python3
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python was not found: $PYTHON_BIN" >&2
  exit 1
fi

PYTHON_MINOR="$("$PYTHON_BIN" -c 'import sys; print(sys.version_info.minor)')"
if [[ "$PYTHON_MINOR" != 13 && "$PYTHON_MINOR" != 14 ]] || \
  ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info.major != 3)'; then
  echo "Python 3.13 or 3.14 is required to build smi2ass." >&2
  exit 1
fi

mkdir -p build
VENV_DIR="build/venv-py3$PYTHON_MINOR"
"$PYTHON_BIN" -m venv "$VENV_DIR"

if [[ -x "$VENV_DIR/bin/python" ]]; then
  VENV_PYTHON="$VENV_DIR/bin/python"
else
  VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
fi

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements-dev.txt
"$VENV_PYTHON" scripts/prepare_tkdnd.py

echo "Prepared Python 3.$PYTHON_MINOR build environment at $VENV_DIR"
