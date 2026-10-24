#!/usr/bin/env bash
set -euo pipefail

OS_NAME="$(uname -s)"
ARCH="$(uname -m)"

case "$OS_NAME" in
  Linux*)
    case "$ARCH" in
      aarch64|arm64) echo linux-aarch64 ;;
      x86_64|amd64) echo linux-x86_64 ;;
      *) echo "Unsupported Linux architecture: $ARCH" >&2; exit 1 ;;
    esac
    ;;
  Darwin*)
    case "$ARCH" in
      arm64|aarch64) echo osx-arm64 ;;
      x86_64|amd64)
        echo "Intel Mac builds are not supported." >&2
        exit 1
        ;;
      *) echo "Unsupported macOS architecture: $ARCH" >&2; exit 1 ;;
    esac
    ;;
  MINGW*|MSYS*|CYGWIN*)
    WINDOWS_ARCH="${PROCESSOR_ARCHITEW6432:-${PROCESSOR_ARCHITECTURE:-$ARCH}}"
    case "$WINDOWS_ARCH" in
      arm64|ARM64|aarch64|AARCH64) echo windows-arm64 ;;
      x86_64|X86_64|amd64|AMD64) echo windows-x86_64 ;;
      *) echo "Unsupported Windows architecture: $WINDOWS_ARCH" >&2; exit 1 ;;
    esac
    ;;
  *) echo "Unsupported build platform: $OS_NAME ($ARCH)" >&2; exit 1 ;;
esac
