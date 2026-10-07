#!/usr/bin/env python3

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ICON_FILES = {
    'osx-arm64': 'smi2ass.icns',
    'windows-x86_64': 'smi2ass.ico',
}


def get_build_icon_path(platform):
    """Return the absolute platform icon path used by PyInstaller."""
    try:
        icon_name = ICON_FILES[platform]
    except KeyError as error:
        raise ValueError('Unsupported GUI build target: %s' % platform) from error
    return (PROJECT_ROOT / 'assets' / icon_name).resolve()


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Usage: build_icon_path.py <osx-arm64|windows-x86_64>')
    print(get_build_icon_path(sys.argv[1]))
