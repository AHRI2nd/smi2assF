import pytest


pytest.importorskip('_tkinter', reason='The local Python build has no Tcl/Tk support.')

from smi2ass_gui import Smi2AssApp, main


def test_gui_starts_and_registers_its_drag_target():
    app = Smi2AssApp()
    try:
        app.root.update_idletasks()
        assert app.root.winfo_exists()
        assert app.drop_zone.winfo_exists()
    finally:
        app.root.destroy()


def test_smoke_test_mode_starts_and_closes_the_window():
    assert main(['--smoke-test']) == 0
