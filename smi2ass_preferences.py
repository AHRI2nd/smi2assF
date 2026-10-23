import json
import os
from pathlib import Path
import sys
import tempfile


DEFAULT_PREFERENCES = {
    'overwrite_existing': False,
    'include_language_suffix': True,
}


def preferences_path(*, platform_name=None, environ=None, home=None):
    platform_name = sys.platform if platform_name is None else platform_name
    environ = os.environ if environ is None else environ
    home = Path.home() if home is None else Path(home)

    if platform_name == 'darwin':
        config_home = home / 'Library' / 'Application Support'
    elif platform_name == 'win32':
        config_home = Path(environ.get('APPDATA') or home / 'AppData' / 'Roaming')
    else:
        config_home = Path(environ.get('XDG_CONFIG_HOME') or home / '.config')
    return config_home / 'smi2assF' / 'preferences.json'


def load_preferences(path=None):
    defaults = DEFAULT_PREFERENCES.copy()
    path = preferences_path() if path is None else Path(path)
    try:
        stored = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return defaults
    if not isinstance(stored, dict):
        return defaults

    for key in defaults:
        value = stored.get(key)
        if type(value) is bool:
            defaults[key] = value
    return defaults


def save_preferences(preferences, path=None):
    path = preferences_path() if path is None else Path(path)
    values = DEFAULT_PREFERENCES.copy()
    for key in values:
        value = preferences.get(key)
        if type(value) is bool:
            values[key] = value

    temporary = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode='w', encoding='utf-8', dir=path.parent,
            prefix='.preferences-', delete=False,
        ) as stream:
            temporary = Path(stream.name)
            json.dump(values, stream, indent=2)
            stream.write('\n')
        os.replace(temporary, path)
        return True
    except OSError:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        return False
