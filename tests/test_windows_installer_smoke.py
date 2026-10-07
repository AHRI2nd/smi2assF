import shutil

import pytest


def test_installer_lifecycle_keeps_native_options_and_logs_outside_installation(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer

    installer = tmp_path / 'package.exe'
    install_dir = tmp_path / 'install with spaces'
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

    result = smoke_test_installer(installer, install_dir, log_dir, runner=run)

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

    result = smoke_test_installer(tmp_path / 'package.exe', tmp_path / 'installed', log_dir, runner=run)

    assert result == 124
    assert labels == ['installer install']
    assert 'Installer failed before copying files' in capsys.readouterr().out


def test_installer_success_requires_the_installed_executable(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer

    with pytest.raises(RuntimeError, match='smi2assF.exe'):
        smoke_test_installer(
            tmp_path / 'package.exe', tmp_path / 'installed', tmp_path / 'logs',
            runner=lambda command, timeout_seconds, label: 0,
        )


def test_installer_rejects_logs_inside_the_install_directory(tmp_path):
    from scripts.windows_installer_smoke import smoke_test_installer

    with pytest.raises(ValueError, match='outside'):
        smoke_test_installer(tmp_path / 'package.exe', tmp_path / 'installed', tmp_path / 'installed' / 'logs')
