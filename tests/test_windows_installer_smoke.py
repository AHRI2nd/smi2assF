import shutil
import sys
from types import SimpleNamespace

import pytest


def test_installer_lifecycle_keeps_native_options_and_logs_outside_installation(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer

    installer = tmp_path / 'package.exe'
    install_dir = tmp_path / 'installer-smoke'
    log_dir = tmp_path / 'diagnostics with spaces'
    commands = []

    def run(command, timeout_seconds, label):
        commands.append((command, timeout_seconds, label))
        if label == 'installer install':
            assert command[0] == str(installer.resolve())
            assert '/VERYSILENT' in command
            assert '/SUPPRESSMSGBOXES' in command
            assert '/NORESTART' in command
            assert f'/DIR={install_dir.resolve()}' in command
            assert f'/LOG={log_dir.resolve() / "install.log"}' in command
            install_dir.mkdir()
            (install_dir / 'smi2assF.exe').write_bytes(b'app')
            (install_dir / 'unins000.exe').write_bytes(b'uninstaller')
            (log_dir / 'install.log').write_text('Installation succeeded', encoding='utf-8')
        elif label == 'installed app smoke':
            assert command == [str(install_dir.resolve() / 'smi2assF.exe'), '--smoke-test']
        elif label == 'uninstall':
            assert command[0] == str(install_dir.resolve() / 'unins000.exe')
            assert '/VERYSILENT' in command
            assert f'/LOG={log_dir.resolve() / "uninstall.log"}' in command
            shutil.rmtree(install_dir)
            (log_dir / 'uninstall.log').write_text('Uninstall succeeded', encoding='utf-8')
        return 0

    result = smoke_test_installer(installer, install_dir, log_dir, runner=run,
                                  workspace_root=tmp_path, installation_checker=lambda: False)

    assert result == 0
    assert not install_dir.exists()
    assert (log_dir / 'install.log').is_file()
    assert (log_dir / 'uninstall.log').is_file()
    assert [entry[2] for entry in commands] == ['installer install', 'installed app smoke', 'uninstall']
    assert all(0 < entry[1] <= 120 for entry in commands)


def test_installer_timeout_stops_lifecycle_and_prints_diagnostics(tmp_path, capsys):
    from scripts.windows_installer_smoke import smoke_test_installer

    log_dir = tmp_path / 'diagnostics'
    labels = []

    def run(command, timeout_seconds, label):
        labels.append(label)
        (log_dir / 'install.log').write_text('Installer failed before copying files', encoding='utf-8')
        return 124

    result = smoke_test_installer(tmp_path / 'package.exe', tmp_path / 'installer-smoke', log_dir, runner=run,
                                  workspace_root=tmp_path, installation_checker=lambda: False)

    assert result == 124
    assert labels == ['installer install']
    assert 'Installer failed before copying files' in capsys.readouterr().out


def test_installer_success_requires_the_installed_executable(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer

    with pytest.raises(RuntimeError, match='smi2assF.exe'):
        smoke_test_installer(
            tmp_path / 'package.exe', tmp_path / 'installer-smoke', tmp_path / 'logs',
            runner=lambda command, timeout_seconds, label: 0,
            workspace_root=tmp_path, installation_checker=lambda: False,
        )


def test_installer_rejects_logs_inside_the_install_directory(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer

    with pytest.raises(ValueError, match='outside'):
        smoke_test_installer(tmp_path / 'package.exe', tmp_path / 'installed', tmp_path / 'installed' / 'logs')


@pytest.mark.parametrize('blocked', ['existing', 'unreadable'])
def test_installer_guard_preserves_existing_directory_before_any_command(tmp_path, blocked):
    from scripts.windows_installer_smoke import smoke_test_installer
    install_dir = tmp_path / 'installer-smoke'
    install_dir.mkdir()
    sentinel = install_dir / 'keep.txt'
    sentinel.write_text('preserve')
    commands = []

    def check():
        if blocked == 'unreadable':
            raise OSError('Registry access denied')
        return True

    with pytest.raises((RuntimeError, OSError)):
        smoke_test_installer(tmp_path / 'package.exe', install_dir, tmp_path / 'logs',
                             runner=lambda *args: commands.append(args),
                             workspace_root=tmp_path, installation_checker=check)
    assert sentinel.read_text() == 'preserve'
    assert commands == []
    assert not (tmp_path / 'logs').exists()


def test_installer_rejects_arbitrary_cleanup_path(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer
    existing = tmp_path / 'personal-files'
    existing.mkdir()
    sentinel = existing / 'keep.txt'
    sentinel.write_text('preserve')
    with pytest.raises(ValueError, match='verification'):
        smoke_test_installer(tmp_path / 'package.exe', existing, tmp_path / 'logs',
                             workspace_root=tmp_path, installation_checker=lambda: False)
    assert sentinel.read_text() == 'preserve'


def test_installer_rejects_linked_cleanup_directory(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer
    target = tmp_path / 'personal-files'
    target.mkdir()
    sentinel = target / 'keep.txt'
    sentinel.write_text('preserve')
    linked = tmp_path / 'installer-smoke'
    try:
        linked.symlink_to(target, target_is_directory=True)
    except OSError:
        pytest.skip('Creating symlinks requires Windows developer mode or privilege')
    with pytest.raises(ValueError, match='verification'):
        smoke_test_installer(tmp_path / 'package.exe', linked, tmp_path / 'logs',
                             workspace_root=tmp_path, installation_checker=lambda: False)
    assert sentinel.read_text() == 'preserve'


@pytest.mark.parametrize('location', [('user', 32), ('user', 64), ('machine', 32), ('machine', 64), None])
def test_existing_installation_checks_both_registry_roots_and_views(monkeypatch, location):
    from scripts import windows_installer_smoke as smoke
    from contextlib import nullcontext
    checked = []

    def open_key(root, path, reserved, access):
        assert path.endswith(r'{D037DE16-5DD8-4E87-8C9D-5A4D19B6E2A1}_is1')
        checked.append((root, access))
        if (root, access) == location:
            return nullcontext()
        raise FileNotFoundError(path)

    registry = SimpleNamespace(HKEY_CURRENT_USER='user', HKEY_LOCAL_MACHINE='machine',
                               KEY_READ=0, KEY_WOW64_32KEY=32, KEY_WOW64_64KEY=64, OpenKey=open_key)
    monkeypatch.setitem(sys.modules, 'winreg', registry)
    monkeypatch.setattr(smoke.sys, 'platform', 'win32')
    assert smoke.existing_installation() is (location is not None)
    if location is None:
        assert set(checked) == {('user', 32), ('user', 64), ('machine', 32), ('machine', 64)}


def test_arm64_installer_has_its_own_app_registration(monkeypatch):
    from scripts import windows_installer_smoke as smoke
    checked = []

    def open_key(root, path, reserved, access):
        checked.append(path)
        raise FileNotFoundError(path)

    registry = SimpleNamespace(HKEY_CURRENT_USER='user', HKEY_LOCAL_MACHINE='machine',
                               KEY_READ=0, KEY_WOW64_32KEY=32, KEY_WOW64_64KEY=64, OpenKey=open_key)
    monkeypatch.setitem(sys.modules, 'winreg', registry)
    monkeypatch.setattr(smoke.sys, 'platform', 'win32')
    assert smoke.existing_installation('windows-arm64') is False
    assert all(path.endswith(r'{AF94EC15-0A57-4072-B235-340D690F2C58}_is1') for path in checked)


def test_registry_query_failure_is_not_treated_as_absent(monkeypatch):
    from scripts import windows_installer_smoke as smoke
    def open_key(*args):
        raise PermissionError('access denied')
    registry = SimpleNamespace(HKEY_CURRENT_USER=1, HKEY_LOCAL_MACHINE=2, KEY_READ=0,
                               KEY_WOW64_32KEY=32, KEY_WOW64_64KEY=64, OpenKey=open_key)
    monkeypatch.setitem(sys.modules, 'winreg', registry)
    monkeypatch.setattr(smoke.sys, 'platform', 'win32')
    with pytest.raises(PermissionError):
        smoke.existing_installation()


@pytest.mark.parametrize('install_code, app_code, cleanup_code', [(0, 7, 0), (124, 0, 0), (0, 7, 9)])
def test_failed_installation_runs_owned_cleanup_and_preserves_error(tmp_path, capsys, install_code, app_code, cleanup_code):
    from scripts.windows_installer_smoke import smoke_test_installer
    directory = tmp_path / 'installer-smoke'
    labels = []
    def run(command, timeout, label):
        labels.append(label)
        if label == 'installer install':
            directory.mkdir()
            (directory / 'smi2assF.exe').write_bytes(b'app')
            (directory / 'unins000.exe').write_bytes(b'uninstaller')
            return install_code
        if label == 'installed app smoke':
            return app_code
        if label == 'uninstall':
            if not cleanup_code:
                shutil.rmtree(directory)
            return cleanup_code
        raise AssertionError(label)
    result = smoke_test_installer(tmp_path / 'installer.exe', directory, tmp_path / 'logs',
                                  runner=run, workspace_root=tmp_path, installation_checker=lambda: False)
    assert result == (install_code or app_code)
    assert labels[-1] == 'uninstall'
    if cleanup_code:
        assert 'cleanup' in capsys.readouterr().out.lower()
    else:
        assert not directory.exists()


def test_concurrent_installer_smoke_is_refused(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer
    def run(command, timeout, label):
        with pytest.raises(RuntimeError, match='in progress'):
            smoke_test_installer(tmp_path / 'other.exe', tmp_path / 'other' / 'installer-smoke', tmp_path / 'other-logs',
                                 runner=lambda *args: pytest.fail('Concurrent install executed'),
                                 workspace_root=tmp_path / 'other', installation_checker=lambda: False)
        return 124
    assert smoke_test_installer(tmp_path / 'installer.exe', tmp_path / 'installer-smoke', tmp_path / 'logs',
                                runner=run, workspace_root=tmp_path, installation_checker=lambda: False) == 124


@pytest.mark.parametrize('existing', [False, True])
def test_windows_mutex_is_exclusive_and_always_closed(monkeypatch, existing):
    import ctypes
    from scripts import windows_installer_smoke as smoke
    calls = []
    def create(security, owner, name):
        assert owner and name.startswith('Global\\smi2assFInstallerSmoke-')
        return 42
    def release(handle):
        calls.append(('release', handle))
    def close(handle):
        calls.append(('close', handle))
    kernel = SimpleNamespace(CreateMutexW=create, ReleaseMutex=release, CloseHandle=close)
    monkeypatch.setattr(ctypes, 'WinDLL', lambda *args, **kwargs: kernel, raising=False)
    monkeypatch.setattr(ctypes, 'get_last_error', lambda: 183 if existing else 0, raising=False)
    monkeypatch.setattr(smoke.sys, 'platform', 'win32')
    if existing:
        with pytest.raises(RuntimeError, match='in progress'):
            with smoke._verification_lock():
                pytest.fail('Acquired an existing mutex')
        assert calls == [('close', 42)]
    else:
        with pytest.raises(ValueError):
            with smoke._verification_lock():
                raise ValueError('primary error')
        assert calls == [('release', 42), ('close', 42)]
