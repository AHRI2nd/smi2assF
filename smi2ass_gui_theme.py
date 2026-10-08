"""Follow native app appearance while keeping conversion state independent."""

from dataclasses import dataclass
import ctypes
from ctypes import wintypes
import sys
import tkinter as tk
from typing import Literal


ThemeMode = Literal['light', 'dark', 'high_contrast']


@dataclass(frozen=True)
class ThemePalette:
    background: str
    surface: str
    text: str
    muted: str
    border: str
    accent: str


LIGHT = ThemePalette('#F6F7F9', '#FFFFFF', '#20252B', '#68717D', '#D8DDE5', '#2F6FEB')
DARK = ThemePalette('#181B20', '#22262D', '#EEF1F5', '#A7B0BC', '#3A414C', '#6FA8FF')


def _windows_high_contrast():
    class HighContrast(ctypes.Structure):
        _fields_ = [('cbSize', wintypes.UINT), ('dwFlags', wintypes.DWORD),
                    ('lpszDefaultScheme', wintypes.LPWSTR)]
    settings = HighContrast()
    settings.cbSize = ctypes.sizeof(settings)
    user32 = ctypes.WinDLL('user32', use_last_error=True)
    query = user32.SystemParametersInfoW
    query.argtypes = [wintypes.UINT, wintypes.UINT, wintypes.LPVOID, wintypes.UINT]
    query.restype = wintypes.BOOL
    return bool(query(0x0042, settings.cbSize, ctypes.byref(settings), 0) and settings.dwFlags & 1)


def _windows_app_is_light():
    import winreg
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                        r'Software\Microsoft\Windows\CurrentVersion\Themes\Personalize') as key:
        return bool(winreg.QueryValueEx(key, 'AppsUseLightTheme')[0])


def _windows_system_color(index):
    query = ctypes.WinDLL('user32').GetSysColor
    query.argtypes = [ctypes.c_int]
    query.restype = wintypes.DWORD
    color = query(index)
    return f'#{color & 255:02x}{(color >> 8) & 255:02x}{(color >> 16) & 255:02x}'


def detect_system_theme(root) -> ThemeMode:
    try:
        system = root.tk.call('tk', 'windowingsystem')
        if system == 'aqua':
            red, green, blue = root.winfo_rgb('systemWindowBackgroundColor')
            brightness = (0.2126*red + 0.7152*green + 0.0722*blue)/65535
            return 'dark' if brightness < 0.5 else 'light'
        if system == 'win32':
            if _windows_high_contrast():
                return 'high_contrast'
            return 'light' if _windows_app_is_light() else 'dark'
    except (tk.TclError, OSError, AttributeError, ValueError, ImportError):
        pass
    return 'light'


def get_palette(root, mode: ThemeMode) -> ThemePalette:
    if mode == 'high_contrast':
        try:
            surface, text = _windows_system_color(5), _windows_system_color(8)
            return ThemePalette(surface, surface, text, text, text, _windows_system_color(13))
        except (OSError, AttributeError):
            # Preserve contrast even when the system color API is unavailable.
            return ThemePalette('#000000', '#000000', '#FFFFFF', '#FFFFFF', '#FFFFFF', '#FFFF00')
    return DARK if mode == 'dark' else LIGHT


def selection_text_color(root, mode: ThemeMode) -> str:
    if mode == 'high_contrast':
        try:
            return _windows_system_color(14)
        except (OSError, AttributeError):
            pass
    accent = get_palette(root, mode).accent
    components = [int(accent[index:index+2], 16)/255 for index in (1, 3, 5)]
    linear = [value/12.92 if value <= 0.04045 else ((value+0.055)/1.055)**2.4 for value in components]
    luminance = sum(value*weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    # Compare the black and white contrast ratios rather than raw RGB brightness.
    return '#000000' if (luminance+0.05)/0.05 >= 1.05/(luminance+0.05) else '#FFFFFF'


def configure_native_appearance(root, mode: ThemeMode) -> None:
    try:
        system = root.tk.call('tk', 'windowingsystem')
        if system == 'aqua':
            attributes = root.attributes()
            if '-appearance' in attributes:
                root.attributes('-appearance', 'auto')
            elif root.tk.call('info', 'commands', 'tk::unsupported::MacWindowStyle'):
                root.tk.call('tk::unsupported::MacWindowStyle', 'appearance', root._w, 'auto')
        elif system == 'win32' and sys.getwindowsversion().build >= 22000:
            # HWND arguments must stay pointer-sized on 64-bit Windows.
            user32 = ctypes.WinDLL('user32')
            ancestor = user32.GetAncestor
            ancestor.argtypes = [wintypes.HWND, wintypes.UINT]
            ancestor.restype = wintypes.HWND
            handle = ancestor(root.winfo_id(), 2)
            if handle:
                apply = ctypes.WinDLL('dwmapi').DwmSetWindowAttribute
                apply.argtypes = [wintypes.HWND, wintypes.DWORD, wintypes.LPCVOID, wintypes.DWORD]
                apply.restype = ctypes.c_long
                dark = wintypes.BOOL(mode == 'dark')
                apply(handle, 20, ctypes.byref(dark), ctypes.sizeof(dark))
    except (tk.TclError, OSError, AttributeError, TypeError, RuntimeError):
        # Native decorations are optional; unsupported APIs cannot prevent startup.
        pass


class ThemeWatcher:
    """Use native appearance events and one bounded fallback polling timer."""

    def __init__(self, root, on_change):
        self.root = root
        self.on_change = on_change
        self.active = False
        self._timer_id = None
        self._bindings = []
        self._last = None

    def start(self):
        if self.active:
            return
        self.active = True
        self.refresh()
        for event in ('<<LightAqua>>', '<<DarkAqua>>', '<FocusIn>'):
            identity = self.root.bind(event, self.refresh, add='+')
            self._bindings.append((event, identity))
        identity = self.root.bind('<Destroy>', self._on_destroy, add='+')
        self._bindings.append(('<Destroy>', identity))
        self._timer_id = self.root.after(2000, self._poll)

    def refresh(self, event=None):
        if not self.active:
            return
        mode = detect_system_theme(self.root)
        # A high-contrast palette may change without its mode changing.
        current = (mode, get_palette(self.root, mode))
        if current != self._last:
            self._last = current
            self.on_change(mode)

    def _poll(self):
        self._timer_id = None
        if self.active:
            self.refresh()
            self._timer_id = self.root.after(2000, self._poll)

    def _on_destroy(self, event):
        if event.widget is self.root:
            self.stop()

    def stop(self):
        self.active = False
        if self._timer_id is not None:
            try:
                self.root.after_cancel(self._timer_id)
            except tk.TclError:
                pass
            self._timer_id = None
        for event, identity in self._bindings:
            try:
                self.root.unbind(event, identity)
            except tk.TclError:
                pass
        self._bindings.clear()
        self._last = None
