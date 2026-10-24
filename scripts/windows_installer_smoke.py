"""Verify the Windows installer with native paths and command-line options."""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import getpass
import os
import tempfile
import shutil
import sys
import time
from pathlib import Path

from scripts.run_with_timeout import run_with_timeout


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WINDOWS_INSTALLER_APP_IDS = {
    'windows-x86_64': '{D037DE16-5DD8-4E87-8C9D-5A4D19B6E2A1}',
    'windows-arm64': '{AF94EC15-0A57-4072-B235-340D690F2C58}',
}


def existing_installation(target='windows-x86_64') -> bool:
    """Refuse production installer smoke when its AppId is already registered."""
    if sys.platform != 'win32':
        return False
    import winreg
    try:
        app_id = WINDOWS_INSTALLER_APP_IDS[target]
    except KeyError as error:
        raise ValueError('Unsupported Windows installer target: %s' % target) from error
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


@contextmanager
def _verification_lock():
    """Refuse overlapping production-AppId smoke runs across workspaces."""
    if sys.platform == 'win32':
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.CreateMutexW.argtypes = (ctypes.c_void_p, wintypes.BOOL, wintypes.LPCWSTR)
        kernel.CreateMutexW.restype = wintypes.HANDLE
        kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel.ReleaseMutex.argtypes = (wintypes.HANDLE,)
        name = 'Global\\smi2assFInstallerSmoke-' + getpass.getuser().casefold()
        handle = kernel.CreateMutexW(None, True, name)
        error = ctypes.get_last_error()
        if not handle:
            raise OSError(error, 'Could not acquire installer verification mutex')
        if error == 183:
            kernel.CloseHandle(handle)
            raise RuntimeError('Installer verification already in progress')
        try:
            yield
        finally:
            kernel.ReleaseMutex(handle)
            kernel.CloseHandle(handle)
    else:
        import fcntl
        path = Path(tempfile.gettempdir()) / ('smi2assF-installer-smoke-%d.lock' % os.getuid())
        fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        with os.fdopen(fd, 'a+b') as stream:
            if os.fstat(stream.fileno()).st_uid != os.getuid():
                raise RuntimeError('Installer verification lock has an unexpected owner')
            try:
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as error:
                raise RuntimeError('Installer verification already in progress') from error
            try:
                yield
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)


def smoke_test_installer(installer_path, install_dir, log_dir, *, runner=run_with_timeout,
                         workspace_root=PROJECT_ROOT / 'build', installation_checker=None):
    with _verification_lock():
        return _smoke_test_installer(installer_path, install_dir, log_dir, runner=runner,
                                     workspace_root=workspace_root, installation_checker=installation_checker)


def _smoke_test_installer(
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
    target = 'windows-arm64' if installer_path.name.endswith('windows-arm64.exe') else 'windows-x86_64'
    checker = installation_checker or (lambda: existing_installation(target))
    if checker():
        raise RuntimeError('Existing smi2assF installation detected; use a clean Windows user or VM for verification')
    if install_dir.exists():
        shutil.rmtree(install_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    for filename in ('install.log', 'uninstall.log'):
        (log_dir / filename).unlink(missing_ok=True)

    print(f'[build] Installer diagnostics directory: {log_dir}', flush=True)
    result = 1
    installation_started = False
    uninstall_attempted = False
    uninstall_path = install_dir / 'unins000.exe'
    try:
        # Construct slash-prefixed Inno options after crossing the Git Bash boundary.
        installation_started = True
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
        uninstall_attempted = True
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
        if installation_started and not uninstall_attempted and uninstall_path.is_file():
            try:
                _validate_install_directory(install_dir, Path(workspace_root))
                cleanup_result = runner([
                    str(uninstall_path), '/VERYSILENT', '/SUPPRESSMSGBOXES', '/NORESTART',
                    f'/LOG={log_dir / "uninstall.log"}',
                ], 60, 'uninstall')
                deadline = time.monotonic() + 10
                while not cleanup_result and install_dir.exists() and time.monotonic() < deadline:
                    time.sleep(0.1)
                if cleanup_result or install_dir.exists():
                    print(f'[build] FAILED installer cleanup (exit code: {cleanup_result}); primary failure: {result}', flush=True)
            except Exception as error:
                print(f'[build] FAILED installer cleanup: {error}; primary failure: {result}', flush=True)
        elif installation_started and not uninstall_attempted and install_dir.exists():
            print('[build] FAILED installer cleanup: owned uninstaller is unavailable', flush=True)
        if result:
            try:
                _print_diagnostics(log_dir)
            except OSError as error:
                print(f'[build] Could not read installer diagnostics: {error}', flush=True)


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
