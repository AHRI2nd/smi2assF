from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUILD_SCRIPT = PROJECT_ROOT / 'build.sh'


def test_build_script_uses_project_name_for_platform_artifacts():
    build_script = BUILD_SCRIPT.read_text(encoding='utf-8')

    assert 'PRODUCT_NAME="smi2assF"' in build_script
    assert '--name "$PRODUCT_NAME"' in build_script
    assert 'build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.exe' in build_script
    assert 'build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.app' in build_script
    assert 'build/gui-dist/$PRODUCT_NAME.$OS_CLASSIFIER.dmg' in build_script
    assert '"$DMG_STAGE/$PRODUCT_NAME.app"' in build_script
    assert 'rm -rf build/gui-dist/smi2ass.*' in build_script
