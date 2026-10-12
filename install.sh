#!/usr/bin/env bash
set -euo pipefail

OS_CLASSIFIER="$(./os_classifier.sh)"
source scripts/python_runtime.sh
select_python_version "$OS_CLASSIFIER"
if [[ -n "${PYTHON:-}" ]]; then
  PYTHON_BIN="$PYTHON"
elif command -v "python$REQUESTED_PYTHON_VERSION" >/dev/null 2>&1; then
  PYTHON_BIN="python$REQUESTED_PYTHON_VERSION"
elif [[ "$OS_CLASSIFIER" == windows-* ]]; then
  PYTHON_BIN=python
else
  PYTHON_BIN=python3
fi
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "Python was not found: $PYTHON_BIN" >&2
  exit 1
fi
verify_python_version "$PYTHON_BIN"
mkdir -p build
"$PYTHON_BIN" -m venv "$VENV_DIR"

select_venv_python

"$VENV_PYTHON" -m pip install --upgrade pip
"$VENV_PYTHON" -m pip install -r requirements-dev.txt
"$VENV_PYTHON" scripts/prepare_tkdnd.py

echo "Prepared Python $REQUESTED_PYTHON_VERSION build environment at $VENV_DIR"
