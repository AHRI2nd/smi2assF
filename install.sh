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
  echo "Python 3.14 was not found: $PYTHON_BIN" >&2
  exit 1
fi

if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(sys.version_info[:2] != (3, 14))'; then
  echo "Python 3.14 is required to build smi2ass." >&2
  exit 1
fi

mkdir -p build
"$PYTHON_BIN" -m venv build/venv-py314

if [[ -x build/venv-py314/bin/python ]]; then
  VENV_PYTHON=build/venv-py314/bin/python
else
  VENV_PYTHON=build/venv-py314/Scripts/python.exe
fi

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements-dev.txt

echo "Prepared Python 3.14 build environment at build/venv-py314"
