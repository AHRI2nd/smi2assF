"""Verify the Windows installer with native paths and command-line options."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from scripts.run_with_timeout import run_with_timeout


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _print_diagnostics(log_dir: Path) -> None:
    for log_path in sorted(log_dir.glob('*.log')):
        print(f'[build] Diagnostics: {log_path}', flush=True)
        lines = log_path.read_text(encoding='utf-8-sig', errors='replace').splitlines()
        print('\n'.join(lines[-80:]), flush=True)


def smoke_test_installer(
    installer_path: Path,
    install_dir: Path,
    log_dir: Path,
    *,
    runner=run_with_timeout,
) -> int:
    installer_path = installer_path.resolve()
    install_dir = install_dir.resolve()
    log_dir = log_dir.resolve()
    if log_dir.is_relative_to(install_dir):
        raise ValueError('Installer diagnostics must be outside the installation directory')
    if install_dir.exists():
        shutil.rmtree(install_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    for filename in ('install.log', 'uninstall.log'):
        (log_dir / filename).unlink(missing_ok=True)

    print(f'[build] Installer diagnostics directory: {log_dir}', flush=True)
    result = 1
    try:
        # Construct slash-prefixed Inno options after crossing the Git Bash boundary.
        result = runner([
            str(installer_path), '/SP-', '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
            f'/LOG={log_dir / "install.log"}', f'/DIR={install_dir}',
        ], 120, 'installer install')
        if result:
            return result

        result = 1
        app_path = install_dir / 'smi2assF.exe'
        uninstall_path = install_dir / 'unins000.exe'
        for required_path in (app_path, uninstall_path):
            if not required_path.is_file() or required_path.stat().st_size == 0:
                raise RuntimeError(f'Installer did not create the expected executable: {required_path}')

        result = runner([str(app_path), '--smoke-test'], 60, 'installed app smoke')
        if result:
            return result
        result = runner([
            str(uninstall_path), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
            f'/LOG={log_dir / "uninstall.log"}',
        ], 60, 'uninstall')
        if result:
            return result

        # The uninstaller can finish deleting its own executable after its launcher exits.
        cleanup_deadline = time.monotonic() + 10
        while install_dir.exists() and time.monotonic() < cleanup_deadline:
            time.sleep(0.1)
        if install_dir.exists():
            result = 1
            remaining = ', '.join(str(path.relative_to(install_dir)) for path in install_dir.rglob('*'))
            raise RuntimeError(f'Windows uninstall left the installation directory: {remaining}')
        print('[build] DONE Windows installer lifecycle: install, app smoke, uninstall', flush=True)
        return 0
    finally:
        if result:
            _print_diagnostics(log_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('installer', type=Path)
    parsed = parser.parse_args()
    try:
        return smoke_test_installer(
            parsed.installer,
            PROJECT_ROOT / 'build' / 'installer-smoke',
            PROJECT_ROOT / 'build' / 'installer-smoke-logs',
        )
    except (OSError, RuntimeError, ValueError) as error:
        print(f'[build] FAILED Windows installer lifecycle: {error}', file=sys.stderr, flush=True)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
