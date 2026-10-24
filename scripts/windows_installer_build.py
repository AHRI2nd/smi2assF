"""Compile the architecture-specific Windows installer with native arguments."""

from __future__ import annotations

import sys
from collections.abc import Sequence

from scripts.run_with_timeout import run_with_timeout


ARCHITECTURES = {
    'windows-x86_64': 'x64',
    'windows-arm64': 'arm64',
}


def build_installer(classifier: str, runner=run_with_timeout) -> int:
    try:
        architecture = ARCHITECTURES[classifier]
    except KeyError as error:
        raise ValueError('Unsupported Windows installer target: %s' % classifier) from error

    return runner(
        ['ISCC.exe', '/DWindowsArchitecture=' + architecture, 'scripts/windows-installer.iss'],
        120,
        'installer compile',
    )


def main(arguments: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if arguments is None else arguments)
    if len(arguments) != 1:
        print('Usage: windows_installer_build.py <windows-x86_64|windows-arm64>', file=sys.stderr)
        return 2
    try:
        return build_installer(arguments[0])
    except ValueError as error:
        print(error, file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
