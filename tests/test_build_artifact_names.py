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

    assert 'OutputBaseFilename=smi2assF.windows-x86_64' in installer_script
    assert 'AppVerName={#AppName}' in installer_script
    assert 'DefaultDirName={localappdata}\\Programs\\{#AppName}' in installer_script
    assert 'PrivilegesRequired=lowest' in installer_script
    assert '#define AppExeName "smi2assF.exe"' in installer_script
    assert 'DestName: "{#AppExeName}"' in installer_script
    assert '[Icons]' in installer_script
    assert 'Uninstallable=yes' in installer_script
    assert 'ISCC.exe scripts/windows-installer.iss' in build_script
    assert 'rm -f "$INSTALLER_PATH" "$INSTALLER_PATH.sha256"' in build_script
    assert 'unins000.exe' in build_script
    assert '"$INSTALL_SMOKE_DIR/$PRODUCT_NAME.exe" --smoke-test' in build_script
