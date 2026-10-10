"""Verify the Windows installer with native paths and command-line options."""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

from scripts.run_with_timeout import run_with_timeout


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def existing_installation() -> bool:
    """Refuse production installer smoke when its AppId is already registered."""
    if sys.platform != 'win32':
        return False
    import winreg
    # Read the compiler input so the guard follows changes to the actual AppId.
    setup = (PROJECT_ROOT / 'scripts' / 'windows-installer.iss').read_text(encoding='utf-8')
    app_id = next(line.split('=', 1)[1].strip() for line in setup.splitlines()
                  if line.startswith('AppId='))
    app_id = app_id.replace('{{', '{', 1)
    key = rf'Software\Microsoft\Windows\CurrentVersion\Uninstall\{app_id}_is1'
    for root in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(root, key, 0, winreg.KEY_READ | view):
                    return True
            except FileNotFoundError:
                continue
    return False


def _validate_install_directory(install_dir: Path, workspace_root: Path) -> Path:
    expected = workspace_root.absolute() / 'installer-smoke'
    absolute = install_dir.absolute()
    if absolute != expected or absolute.resolve() != absolute:
        raise ValueError('Installation must use an unlinked verification directory')
    # Junctions are resolved by Path.resolve; include nested links before cleanup.
    if absolute.exists():
        for child in absolute.rglob('*'):
            if child.is_symlink() or (hasattr(child, 'is_junction') and child.is_junction()):
                raise ValueError('Linked entries are not allowed in the verification directory')
    return absolute


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
    workspace_root=PROJECT_ROOT / 'build',
    installation_checker=None,
) -> int:
    installer_path = installer_path.resolve()
    raw_install_dir = install_dir
    install_dir = install_dir.resolve()
    log_dir = log_dir.resolve()
    if log_dir.is_relative_to(install_dir):
        raise ValueError('Installer diagnostics must be outside the installation directory')
    install_dir = _validate_install_directory(raw_install_dir, Path(workspace_root))
    checker = installation_checker or existing_installation
    if checker():
        raise RuntimeError('Existing smi2assF installation detected; use a clean Windows user or VM for verification')
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
