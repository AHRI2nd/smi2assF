from types import SimpleNamespace
import time

import pytest

pytest.importorskip('_tkinter')
import tkinter as tk
from smi2ass_gui import Smi2AssApp


@pytest.mark.parametrize('mode', ['light', 'dark'])
@pytest.mark.parametrize('language', ['ko', 'en'])
@pytest.mark.parametrize('size', ['400x280', '320x260'])
@pytest.mark.parametrize('state', ['idle', 'converting', 'done', 'failed', 'partial', 'empty'])
def test_gui_layout_keeps_all_content_visible(monkeypatch, mode, language, size, state):
    monkeypatch.setattr('smi2ass_gui.detect_ui_language', lambda: language)
    app = Smi2AssApp()
    try:
        assert isinstance(app.drop_zone, tk.Canvas), 'The drop surface must render separate title and detail content.'
        app._apply_theme(mode)
        app.root.geometry(size)
        app._set_drop_state(state, count=99999, total=99999, outputs=88888,
                            existing=77777, failed=66666, scan_errors=55555)
        app.root.update()
        bounds = app.drop_zone.bbox('content')
        assert bounds is not None
        left, top, right, bottom = bounds
        assert left >= 12 and top >= 12
        assert right <= app.drop_zone.winfo_width() - 12
        assert bottom <= app.drop_zone.winfo_height() - 12
        option = app.overwrite_checkbox
        assert option.winfo_height() >= option.winfo_reqheight()
        assert option.winfo_y() + option.winfo_height() <= option.master.winfo_height()
    finally:
        app.root.destroy()


def test_drop_leave_restores_previous_result():
    app = Smi2AssApp()
    try:
        assert isinstance(app.drop_zone, tk.Canvas)
        app._set_drop_state('done', total=12, outputs=10, existing=2, failed=0, scan_errors=0)
        app.root.update()
        before = app.drop_zone.itemcget('title', 'text')
        assert app._on_drop_enter(SimpleNamespace()) == 'copy'
        app.root.update()
        assert app.drop_zone.itemcget('title', 'text') != before
        app._on_drop_leave(SimpleNamespace())
        app.root.update()
        assert app.drop_zone.itemcget('title', 'text') == before
    finally:
        app.root.destroy()


def test_drop_on_canvas_content_converts_once(tmp_path):
    source = tmp_path / '자막 file.smi'
    source.write_text('<SYNC Start=0><P Class=KRCC>First\n<SYNC Start=1000><P Class=KRCC>&nbsp;')
    app = Smi2AssApp()
    try:
        assert isinstance(app.drop_zone, tk.Canvas)
        app._on_drop(SimpleNamespace(data=app.root.tk.call('list', str(source)), widget=app.drop_zone))
        deadline = time.monotonic() + 4
        while app.busy and time.monotonic() < deadline:
            app.root.update()
            time.sleep(0.01)
        assert not app.busy
        assert (tmp_path / '자막 file.kor.ass').is_file()
        assert app.state_values['total'] == 1
        assert app.state_values['outputs'] == 1
    finally:
        app.root.destroy()


def test_gui_layout_expands_minimum_for_large_font():
    app = Smi2AssApp()
    try:
        assert isinstance(app.drop_zone, tk.Canvas)
        app.title_font.configure(size=26)
        app.detail_font.configure(size=22)
        app._update_minimum_size()
        width, height = app.root.minsize()
        assert height > 260
        app.root.geometry(f'{width}x{height}')
        app._set_drop_state('done', total=99999, outputs=88888, existing=77777, failed=0, scan_errors=0)
        app.root.update()
        assert app.drop_zone.bbox('content')[3] < app.drop_zone.winfo_height()
    finally:
        app.root.destroy()
