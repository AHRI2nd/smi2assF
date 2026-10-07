from pathlib import Path

from scripts.build_icon_path import get_build_icon_path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_windows_build_icon_path_is_absolute_from_project_root():
    icon_path = get_build_icon_path('windows-x86_64')

    assert icon_path == (
        PROJECT_ROOT / 'assets' / 'smi2ass.ico'
    ).resolve()
    assert icon_path.is_absolute()
    assert icon_path.is_file()


def test_macos_build_icon_path_is_absolute_from_project_root():
    icon_path = get_build_icon_path('osx-arm64')

    assert icon_path == (
        PROJECT_ROOT / 'assets' / 'smi2ass.icns'
    ).resolve()
    assert icon_path.is_absolute()
    assert icon_path.is_file()
