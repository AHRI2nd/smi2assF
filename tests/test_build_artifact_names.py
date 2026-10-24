from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / 'build.sh'
WINDOWS_INSTALLER_SCRIPT = PROJECT_ROOT / 'scripts' / 'windows-installer.iss'


def test_build_script_uses_project_name_for_platform_artifacts():
    build_script = BUILD_SCRIPT.read_text(encoding='utf-8')

    assert 'PRODUCT_NAME="smi2assF"' in build_script
    assert '--name "$PRODUCT_NAME"' in build_script
    assert 'build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.exe' in build_script
    assert 'build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.app' in build_script
    assert 'build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.dmg' in build_script
    assert '"$DMG_STAGE/$PRODUCT_NAME.app"' in build_script
    assert 'rm -rf build/gui-dist/smi2ass.*' in build_script


def test_windows_installer_installs_project_named_app_per_user():
    installer_script = WINDOWS_INSTALLER_SCRIPT.read_text(encoding='utf-8')
    build_script = BUILD_SCRIPT.read_text(encoding='utf-8')

    assert '#define InstallerName "smi2assF.windows-x86_64"' in installer_script
    assert '#define AppId "D037DE16-5DD8-4E87-8C9D-5A4D19B6E2A1"' in installer_script
    assert '#define InstallerName "smi2assF.windows-arm64"' in installer_script
    assert '#define AllowedArchitecture "arm64"' in installer_script
    assert '#define InstallArchitecture "arm64"' in installer_script
    assert '#define InstallDirectory "smi2assF-arm64"' in installer_script
    assert '#define ShortcutGroup "smi2assF ARM64"' in installer_script
    assert 'AppVerName={#AppName}' in installer_script
    assert 'DefaultDirName={localappdata}\\Programs\\{#InstallDirectory}' in installer_script
    assert 'PrivilegesRequired=lowest' in installer_script
    assert '#define AppExeName "smi2assF.exe"' in installer_script
    assert 'DestName: "{#AppExeName}"' in installer_script
    assert '[Icons]' in installer_script
    assert 'Uninstallable=yes' in installer_script
    assert 'scripts/windows_installer_build.py "$OS_CLASSIFIER"' in build_script
    assert 'rm -f "$INSTALLER_PATH" "$INSTALLER_PATH.sha256"' in build_script
    assert '-m scripts.windows_installer_smoke "$INSTALLER_PATH"' in build_script


def test_windows_installer_build_keeps_inno_switch_inside_native_python():
    from scripts.windows_installer_build import build_installer

    commands = []

    def runner(command, timeout, label):
        commands.append((command, timeout, label))
        return 0

    assert build_installer('windows-arm64', runner) == 0
    assert commands == [(
        ['ISCC.exe', '/DWindowsArchitecture=arm64', 'scripts/windows-installer.iss'],
        120,
        'installer compile',
    )]


def test_windows_release_uses_verified_python_314():
    release_workflow = (PROJECT_ROOT / '.github' / 'workflows' / 'release.yml').read_text(
        encoding='utf-8',
    )
    install_script = (PROJECT_ROOT / 'install.sh').read_text(encoding='utf-8')
    build_script = (PROJECT_ROOT / 'build.sh').read_text(encoding='utf-8')

    assert "python-version: '3.14.8'" in release_workflow
    assert 'platform: windows-arm64' in release_workflow
    assert 'python-architecture: arm64' in release_workflow
    assert 'smi2assF.windows-arm64.exe' in release_workflow
    assert 'PYTHON: python' in release_workflow
    assert 'select_python_version' in install_script
    assert 'select_venv_python' in build_script
    assert 'default_version=3.14' in (PROJECT_ROOT / 'scripts/python_runtime.sh').read_text()


def test_windows_installer_smoke_is_silent_diagnostic_and_bounded():
    installer_script = WINDOWS_INSTALLER_SCRIPT.read_text(encoding='utf-8')
    build_script = BUILD_SCRIPT.read_text(encoding='utf-8')
    release_workflow = (PROJECT_ROOT / '.github' / 'workflows' / 'release.yml').read_text(
        encoding='utf-8',
    )

    assert 'DisableStartupPrompt=yes' in installer_script
    assert 'scripts/windows_installer_build.py "$OS_CLASSIFIER"' in build_script
    assert '-m scripts.windows_installer_smoke "$INSTALLER_PATH"' in build_script
    assert '/VERYSILENT' not in build_script
    assert '/LOG=' not in build_script
    assert 'timeout-minutes:' in release_workflow
