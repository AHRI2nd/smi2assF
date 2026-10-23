import json

from smi2ass_preferences import DEFAULT_PREFERENCES, load_preferences, preferences_path, save_preferences


def test_preferences_round_trip(tmp_path):
    path = tmp_path / 'preferences.json'
    values = {'overwrite_existing': True, 'include_language_suffix': False}

    assert save_preferences(values, path)
    assert load_preferences(path) == values


def test_missing_or_invalid_preferences_use_defaults(tmp_path):
    path = tmp_path / 'preferences.json'

    assert load_preferences(path) == DEFAULT_PREFERENCES
    path.write_text('{invalid json', encoding='utf-8')
    assert load_preferences(path) == DEFAULT_PREFERENCES


def test_preferences_path_uses_platform_user_config_location(tmp_path):
    home = tmp_path / 'home'
    appdata = tmp_path / 'roaming'
    xdg = tmp_path / 'xdg'

    assert preferences_path(platform_name='darwin', environ={}, home=home) == (
        home / 'Library' / 'Application Support' / 'smi2assF' / 'preferences.json'
    )
    assert preferences_path(platform_name='win32', environ={'APPDATA': str(appdata)}, home=home) == (
        appdata / 'smi2assF' / 'preferences.json'
    )
    assert preferences_path(platform_name='linux', environ={'XDG_CONFIG_HOME': str(xdg)}, home=home) == (
        xdg / 'smi2assF' / 'preferences.json'
    )


def test_saved_preferences_ignore_unknown_and_non_boolean_values(tmp_path):
    path = tmp_path / 'preferences.json'
    path.write_text(json.dumps({
        'overwrite_existing': 1,
        'include_language_suffix': False,
        'unrecognized': True,
    }), encoding='utf-8')

    assert load_preferences(path) == {
        'overwrite_existing': False,
        'include_language_suffix': False,
    }
