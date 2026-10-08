import pytest
import weakref
import gc
import tkinter as tk

pytest.importorskip('_tkinter')
from tkinterdnd2 import TkinterDnD
from smi2ass_gui import Smi2AssApp
from smi2ass_gui_support import SmiConversionSummary


def watcher_class():
    import smi2ass_gui_theme as theme
    assert hasattr(theme, 'ThemeWatcher'), 'Theme changes must be watched and stopped on teardown.'
    return theme.ThemeWatcher


def test_watcher_delivers_initial_theme_and_applies_only_changes(monkeypatch):
    watcher_type = watcher_class()
    mode = ['light']
    monkeypatch.setattr('smi2ass_gui_theme.detect_system_theme', lambda root: mode[0])
    root = TkinterDnD.Tk()
    root.update_idletasks()
    changes = []
    watcher = watcher_type(root, changes.append)
    try:
        watcher.start()
        assert changes == ['light']
        watcher.refresh()
        assert changes == ['light']
        mode[0] = 'dark'
        watcher.refresh()
        assert changes == ['light', 'dark']
        watcher.start()
        assert len(root.tk.call('after', 'info')) == 1
    finally:
        watcher.stop()
        root.destroy()


def test_watcher_stops_without_pending_callbacks(monkeypatch):
    watcher_type = watcher_class()
    monkeypatch.setattr('smi2ass_gui_theme.detect_system_theme', lambda root: 'light')
    root = TkinterDnD.Tk()
    root.update_idletasks()
    changes = []
    watcher = watcher_type(root, changes.append)
    watcher.start()
    watcher.stop()
    watcher.stop()
    assert not root.tk.call('after', 'info')
    root.event_generate('<<DarkAqua>>')
    root.update()
    assert changes == ['light']
    root.destroy()


def test_theme_change_preserves_busy_state_and_overwrite():
    app = Smi2AssApp()
    try:
        assert hasattr(app, '_apply_theme'), 'The existing widgets need palette updates.'
        app.busy = True
        app.overwrite_existing.set(True)
        app.overwrite_checkbox.configure(state='disabled')
        app._set_drop_state('converting', count=12)
        app.root.update()
        surface = app.drop_zone
        binding = surface.tk.call('bind', surface._w, '<<Drop>>')
        app._apply_theme('dark')
        app.root.update()
        assert app.drop_zone is surface
        assert app.drop_zone.cget('background') == '#181b20' or app.drop_zone.cget('background') == '#181B20'
        assert app.busy
        assert app.overwrite_existing.get()
        assert app.overwrite_checkbox.instate(['disabled'])
        assert app.state_values['count'] == 12
        assert surface.tk.call('bind', surface._w, '<<Drop>>') == binding
        app.events.put(('done', SmiConversionSummary(12, 10, 2, 0), 0))
        app._poll_worker()
        app.root.update()
        assert not app.busy
        assert app.overwrite_checkbox.instate(['!disabled'])
        assert app.state_values['outputs'] == 10
        assert app.theme_mode == 'dark'
    finally:
        app.root.destroy()


def test_disposal_cancels_theme_and_render_callbacks():
    app = Smi2AssApp()
    try:
        assert hasattr(app, 'theme_watcher')
        app._dispose()
        assert not app.root.tk.call('after', 'info')
    finally:
        if not app._disposed:
            app.root.destroy()


@pytest.mark.parametrize('external', [False, True])
def test_disposal_releases_tk_resources_before_worker_collection(external):
    app = Smi2AssApp()
    resources = [weakref.ref(resource) for resource in (
        app.overwrite_existing, app.title_font, app.detail_font,
    )]
    try:
        if external:
            app.root.destroy()
        else:
            app._dispose()
        # A later conversion worker must never inherit Tk resource finalization.
        assert all(reference() is None for reference in resources)
    finally:
        if not app._disposed:
            app._dispose()


def test_background_conversion_does_not_retain_destroyed_app(monkeypatch):
    calls = []
    class PendingWorker:
        def __init__(self, **options):
            calls.append(options)

        def start(self):
            pass

    monkeypatch.setattr('smi2ass_gui.threading.Thread', PendingWorker)
    app = Smi2AssApp()
    reference = weakref.ref(app)
    app._start_conversion(['pending.smi'])
    app.root.destroy()
    del app
    gc.collect()
    assert calls
    assert reference() is None


def test_actual_mac_appearance_updates_palette_without_rebuilding_controls():
    app = Smi2AssApp()
    supported = app.root.tk.call('tk', 'windowingsystem') == 'aqua' and '-appearance' in app.root.attributes()
    try:
        if not supported:
            pytest.skip('This Tk does not expose native macOS appearance.')
        for appearance, background in (('dark', '#181B20'), ('light', '#F6F7F9')):
            try:
                app.root.attributes('-appearance', appearance)
            except tk.TclError:
                # Tk 9.0 uses Aqua names; Tk 9.1 uses light/dark names.
                app.root.attributes('-appearance', {'dark': 'darkaqua', 'light': 'aqua'}[appearance])
            app.root.update()
            app.theme_watcher.refresh()
            app.root.update()
            assert app.palette['background'] == background
    finally:
        if supported:
            app.root.attributes('-appearance', 'auto')
        app._dispose()


def test_external_destroy_has_no_deleted_callback_errors():
    app = Smi2AssApp()
    interpreter = app.root.tk
    previous = interpreter.call('info', 'commands', 'bgerror')
    if previous:
        interpreter.call('rename', 'bgerror', 'gui_test_original_bgerror')
    interpreter.call('set', 'testErrors', '')
    interpreter.call('proc', 'bgerror', 'message', 'lappend ::testErrors $message')
    try:
        app.root.destroy()
        interpreter.call('update')
        assert not interpreter.call('set', 'testErrors')
    finally:
        interpreter.call('rename', 'bgerror', '')
        if previous:
            interpreter.call('rename', 'gui_test_original_bgerror', 'bgerror')
        interpreter.call('unset', 'testErrors')
        if not app._disposed:
            app._dispose()


@pytest.mark.parametrize(('mode', 'expected'), [('dark', '#A7B0BC'), ('high_contrast', '#FFFFFF')])
def test_disabled_selected_overwrite_keeps_visible_checkmark(mode, expected, monkeypatch):
    import smi2ass_gui_theme as theme
    def unavailable(index):
        raise OSError('No native high-contrast colors on this test host')
    if mode == 'high_contrast':
        monkeypatch.setattr(theme, '_windows_system_color', unavailable)
    app = Smi2AssApp()
    try:
        app._apply_theme(mode)
        foreground = app.style.lookup('Converter.TCheckbutton', 'indicatorforeground', ('disabled', 'selected'))
        assert foreground == expected
    finally:
        app._dispose()
