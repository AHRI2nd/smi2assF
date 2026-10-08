"""Keep GUI tests on one native Tk runtime with independent test windows."""

from contextlib import nullcontext

import pytest


GUI_MODULES = {'test_gui_startup.py', 'test_gui_layout.py', 'test_gui_theme_lifecycle.py'}


@pytest.fixture(scope='session')
def gui_runtime(request):
    pytest.importorskip('_tkinter')
    from tkinterdnd2 import TkinterDnD
    capture = request.config.pluginmanager.getplugin('capturemanager')
    # Native Tk startup precedes test capture; Windows tests still use capture=sys.
    with capture.global_and_fixture_disabled() if capture else nullcontext():
        root = TkinterDnD.Tk()
        root.update_idletasks()
        root.withdraw()
        root.update_idletasks()
    yield root
    root.update_idletasks()
    root.destroy()


@pytest.fixture(autouse=True)
def isolated_gui_window(request, monkeypatch):
    if request.path.name not in GUI_MODULES:
        return
    root = request.getfixturevalue('gui_runtime')
    import tkinter as tk
    from tkinterdnd2 import TkinterDnD
    # Toplevels share Tcl/Tk safely; each app still owns and destroys its window.
    monkeypatch.setattr(TkinterDnD, 'Tk', lambda *args, **kwargs: tk.Toplevel(root))
