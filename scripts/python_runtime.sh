#!/usr/bin/env bash
# Shared interpreter selection for dependency preparation and packaging.
select_python_version() {
  local classifier="$1"
  local default_version=3.14
  if [[ "$classifier" == windows-* ]]; then
    default_version=3.14
  fi
  REQUESTED_PYTHON_VERSION="${BUILD_PYTHON_VERSION:-$default_version}"
  if [[ "$REQUESTED_PYTHON_VERSION" != 3.13 && "$REQUESTED_PYTHON_VERSION" != 3.14 ]]; then
    echo "BUILD_PYTHON_VERSION must be 3.13 or 3.14." >&2
    return 1
  fi
  PYTHON_MINOR="${REQUESTED_PYTHON_VERSION#3.}"
  VENV_DIR="build/venv-py3$PYTHON_MINOR"
}

verify_python_version() {
  local executable="$1"
  local actual
  actual="$("$executable" -c 'import sys; print("%d.%d" % sys.version_info[:2])')" || return 1
  # Native Windows stdout can retain CR after Bash removes the final LF.
  actual="${actual%$'\r'}"
  if [[ "$actual" != "$REQUESTED_PYTHON_VERSION" ]]; then
    echo "Requested Python $REQUESTED_PYTHON_VERSION, found $actual at $executable." >&2
    return 1
  fi
}

select_venv_python() {
  VENV_PYTHON=""
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    VENV_PYTHON="$VENV_DIR/bin/python"
  elif [[ -x "$VENV_DIR/Scripts/python.exe" ]]; then
    VENV_PYTHON="$VENV_DIR/Scripts/python.exe"
  else
    echo "Python $REQUESTED_PYTHON_VERSION build environment not found. Run install.sh with the same BUILD_PYTHON_VERSION." >&2
    return 1
  fi
  verify_python_version "$VENV_PYTHON"
}
