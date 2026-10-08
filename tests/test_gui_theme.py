import importlib.util
from types import SimpleNamespace

import pytest


def theme_module():
    assert importlib.util.find_spec('smi2ass_gui_theme') is not None, 'OS appearance handling is not implemented.'
    import smi2ass_gui_theme
    return smi2ass_gui_theme


class ThemeRoot:
    def __init__(self, system='aqua', rgb=(65535, 65535, 65535)):
        self.system = system
        self.rgb = rgb
        self.tk = SimpleNamespace(call=lambda *args: self.system if args == ('tk', 'windowingsystem') else '')

    def winfo_rgb(self, name):
        return self.rgb

    def attributes(self, *args):
        raise RuntimeError('Unsupported attribute')


@pytest.mark.parametrize(('rgb', 'expected'), [((65535, 65535, 65535), 'light'), ((7710, 7710, 7710), 'dark')])
def test_mac_theme_detection_uses_actual_window_colors(rgb, expected):
    assert theme_module().detect_system_theme(ThemeRoot(rgb=rgb)) == expected


@pytest.mark.parametrize(('light', 'expected'), [(True, 'light'), (False, 'dark')])
def test_theme_detection_uses_app_preference(monkeypatch, light, expected):
    theme = theme_module()
    monkeypatch.setattr(theme, '_windows_high_contrast', lambda: False)
    monkeypatch.setattr(theme, '_windows_app_is_light', lambda: light)
    assert theme.detect_system_theme(ThemeRoot('win32')) == expected


def test_theme_detection_falls_back_when_preference_missing(monkeypatch):
    theme = theme_module()
    monkeypatch.setattr(theme, '_windows_high_contrast', lambda: False)
    def missing_preference():
        raise FileNotFoundError('Preference missing')
    monkeypatch.setattr(theme, '_windows_app_is_light', missing_preference)
    assert theme.detect_system_theme(ThemeRoot('win32')) == 'light'
    assert theme.detect_system_theme(ThemeRoot('x11')) == 'light'


def test_high_contrast_overrides_dark(monkeypatch):
    theme = theme_module()
    monkeypatch.setattr(theme, '_windows_high_contrast', lambda: True)
    monkeypatch.setattr(theme, '_windows_app_is_light', lambda: False)
    monkeypatch.setattr(theme, '_windows_system_color', lambda index: {5: '#000000', 8: '#ffffff', 13: '#ffff00', 17: '#aaaaaa'}[index])
    root = ThemeRoot('win32')
    assert theme.detect_system_theme(root) == 'high_contrast'
    palette = theme.get_palette(root, 'high_contrast')
    assert palette.background == '#000000'
    assert palette.text == '#ffffff'
    assert palette.accent == '#ffff00'


def test_mac_appearance_is_capability_guarded():
    theme_module().configure_native_appearance(ThemeRoot(), 'dark')


def test_theme_detection_failure_does_not_abort_startup():
    root = ThemeRoot()
    def broken_color(name):
        raise ValueError('Unsupported system color')
    root.winfo_rgb = broken_color
    assert theme_module().detect_system_theme(root) == 'light'


def contrast(first, second):
    def luminance(color):
        values = [int(color[i:i+2], 16)/255 for i in (1, 3, 5)]
        linear = [v/12.92 if v <= 0.04045 else ((v+0.055)/1.055)**2.4 for v in values]
        return sum(v*w for v, w in zip(linear, (0.2126, 0.7152, 0.0722)))
    a, b = sorted((luminance(first), luminance(second)))
    return (b+0.05)/(a+0.05)


@pytest.mark.parametrize('mode', ['light', 'dark'])
def test_palette_text_and_focus_contrast(mode):
    palette = theme_module().get_palette(ThemeRoot(), mode)
    assert contrast(palette.text, palette.surface) >= 4.5
    assert contrast(palette.muted, palette.surface) >= 4.5
    assert contrast(palette.text, palette.background) >= 4.5
    assert contrast(palette.accent, palette.surface) >= 3


def test_windows_registry_reads_app_mode_instead_of_system_mode(monkeypatch):
    import sys
    from contextlib import nullcontext
    theme = theme_module()
    key = object()
    def open_key(hive, location):
        assert hive == 'current-user'
        assert location == r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize'
        return nullcontext(key)
    def query_value(actual_key, name):
        assert actual_key is key
        assert name == 'AppsUseLightTheme'
        return 0, 4
    monkeypatch.setitem(sys.modules, 'winreg', SimpleNamespace(
        HKEY_CURRENT_USER='current-user', OpenKey=open_key, QueryValueEx=query_value,
    ))
    assert theme._windows_app_is_light() is False


def test_windows_native_appearance_keeps_64_bit_window_handle(monkeypatch):
    theme = theme_module()
    handle = 0x123456789ABC
    calls = []
    class Function:
        def __init__(self, callback):
            self.callback = callback
        def __call__(self, *args):
            return self.callback(*args)
    def get_ancestor(window, flags):
        assert window == handle
        assert flags == 2
        return handle
    def set_attribute(window, attribute, pointer, size):
        calls.append((window, attribute, pointer._obj.value))
        return 0
    user32 = SimpleNamespace(GetAncestor=Function(get_ancestor))
    dwmapi = SimpleNamespace(DwmSetWindowAttribute=Function(set_attribute))
    monkeypatch.setattr(theme.ctypes, 'WinDLL', lambda name: {'user32': user32, 'dwmapi': dwmapi}[name], raising=False)
    monkeypatch.setattr(theme, 'sys', SimpleNamespace(getwindowsversion=lambda: SimpleNamespace(build=22000)))
    root = ThemeRoot('win32')
    root.winfo_id = lambda: handle
    theme.configure_native_appearance(root, 'dark')
    assert calls == [(handle, 20, 1)]
    assert user32.GetAncestor.argtypes[0] == theme.wintypes.HWND


def test_windows_native_api_failure_does_not_abort_startup(monkeypatch):
    theme = theme_module()
    monkeypatch.setattr(theme, 'sys', SimpleNamespace(getwindowsversion=lambda: SimpleNamespace(build=22000)))
    def unavailable(name):
        raise OSError('DWM unavailable')
    monkeypatch.setattr(theme.ctypes, 'WinDLL', unavailable, raising=False)
    theme.configure_native_appearance(ThemeRoot('win32'), 'dark')


def test_selected_mark_stays_visible_on_green_highlight(monkeypatch):
    theme = theme_module()
    assert hasattr(theme, 'selection_text_color'), 'Selected checkmarks need an accessible contrast calculation.'
    monkeypatch.setattr(theme, '_windows_system_color', lambda index: {5: '#000000', 8: '#FFFFFF', 13: '#00FF00', 14: '#000000'}[index])
    color = theme.selection_text_color(ThemeRoot('win32'), 'high_contrast')
    assert color == '#000000'
    assert contrast(color, '#00FF00') >= 3
