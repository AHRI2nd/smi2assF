import ctypes
import sys
from types import SimpleNamespace

import pytest


@pytest.mark.parametrize('names', [('ko-KR', 'en-US'), ('en-US', 'ko-KR')])
def test_windows_native_language_buffer_preserves_preference_order(monkeypatch, names):
    from smi2ass_os_language import windows_ui_languages
    payload = '\0'.join(names) + '\0\0'
    def preferred(flags, count, buffer, size):
        assert flags == 8
        ctypes.cast(count, ctypes.POINTER(ctypes.c_uint32))[0] = len(names)
        if buffer is None:
            ctypes.cast(size, ctypes.POINTER(ctypes.c_uint32))[0] = len(payload)
        else:
            for index, char in enumerate(payload):
                buffer[index] = char
        return 1
    dll = SimpleNamespace(GetUserPreferredUILanguages=preferred)
    monkeypatch.setattr(ctypes, 'WinDLL', lambda *args, **kwargs: dll, raising=False)
    assert windows_ui_languages() == names


def test_windows_query_failure_uses_actual_ui_language_fallback(monkeypatch):
    from smi2ass_os_language import windows_ui_languages
    def preferred(*args):
        return 0
    def default():
        return 0x0412
    dll = SimpleNamespace(GetUserPreferredUILanguages=preferred, GetUserDefaultUILanguage=default)
    monkeypatch.setattr(ctypes, 'WinDLL', lambda *args, **kwargs: dll, raising=False)
    assert windows_ui_languages() == ('ko',)


@pytest.mark.skipif(sys.platform != 'darwin', reason='Requires macOS user preferences')
def test_macos_native_languages_match_os_preferences():
    import re
    import subprocess
    from smi2ass_os_language import macos_ui_languages
    result = subprocess.run(['/usr/bin/defaults', 'read', '-g', 'AppleLanguages'],
                            capture_output=True, text=True, check=True, timeout=10)
    expected = tuple(re.findall(r'"([^"]+)"', result.stdout))
    assert expected
    assert macos_ui_languages() == expected
