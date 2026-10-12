"""Log the actual loaded GUI runtime and packaging dependencies."""
from importlib.metadata import version
import platform
from tkinterdnd2 import TkinterDnD


def main():
    print('Python: %s (%s)' % (platform.python_version(), platform.machine()), flush=True)
    for package in ('beautifulsoup4', 'chardet', 'tkinterdnd2', 'pyinstaller', 'pytest'):
        print('%s: %s' % (package, version(package)), flush=True)
    root = TkinterDnD.Tk()
    try:
        # Complete Cocoa initialization before destroying this standalone interpreter.
        root.update_idletasks()
        print('Tcl: %s; Tk: %s; TkDND: %s' % (
            root.tk.call('info', 'patchlevel'), root.tk.call('package', 'provide', 'Tk'),
            root.tk.call('package', 'require', 'tkdnd')), flush=True)
    finally:
        root.destroy()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
