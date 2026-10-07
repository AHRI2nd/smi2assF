import time

import pytest


pytest.importorskip('_tkinter', reason='The local Python build has no Tcl/Tk support.')

from smi2ass_gui import Smi2AssApp, main


def test_gui_starts_and_registers_its_drag_target():
    app = Smi2AssApp()
    try:
        app.root.update_idletasks()
        assert app.root.winfo_exists()
        assert app.drop_zone.winfo_exists()
        assert app.drop_zone.master.winfo_children() == [
            app.drop_zone, app.overwrite_checkbox,
        ]
    finally:
        app.root.destroy()


def test_smoke_test_mode_starts_and_closes_the_window():
    assert main(['--smoke-test']) == 0


def test_adding_dropped_paths_starts_conversion_automatically(tmp_path):
    source = tmp_path / 'episode.smi'
    source.write_text(
        '<SYNC Start=0><P Class=KRCC>First cue\n'
        '<SYNC Start=1000><P Class=KRCC>&nbsp;',
        encoding='utf-8',
    )
    app = Smi2AssApp()
    try:
        assert app.add_paths([source]) == 1
        assert app.busy
        deadline = time.monotonic() + 3
        while app.busy and time.monotonic() < deadline:
            app.root.update()
            time.sleep(0.01)
        assert not app.busy
        assert (tmp_path / 'episode.kor.ass').is_file()
    finally:
        app.root.destroy()
