#!/usr/bin/env python3

import queue
import sys
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from smi2ass_gui_support import (
    convert_smi_files,
    detect_ui_language,
    localized_text,
    scan_smi_files,
)


class Smi2AssApp:
    def __init__(self, root=None):
        self.root = root or TkinterDnD.Tk()
        self.language = detect_ui_language()
        self.root.title(self._text('window_title'))
        self.root.geometry('520x380')
        self.root.minsize(360, 280)
        self.root.protocol('WM_DELETE_WINDOW', self._close)

        self.events = queue.Queue()
        self.busy = False
        self.overwrite_existing = tk.BooleanVar(master=self.root, value=False)

        self._build_ui()
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self._on_drop)

    def _text(self, key, **values):
        return localized_text(key, self.language, **values)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=20)
        frame.pack(fill='both', expand=True)

        self.drop_zone = ttk.Label(
            frame,
            text=self._text('drop_hint'),
            anchor='center',
            justify='center',
            wraplength=440,
            padding=32,
            relief='groove',
            font=('TkDefaultFont', 16, 'bold'),
        )
        self.drop_zone.pack(fill='both', expand=True)
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self._on_drop)

        self.overwrite_checkbox = ttk.Checkbutton(
            frame,
            text=self._text('overwrite'),
            variable=self.overwrite_existing,
        )
        self.overwrite_checkbox.pack(anchor='center', pady=(16, 0))

    def add_paths(self, paths):
        if self.busy:
            self.drop_zone.configure(text=self._text('status_busy_add'))
            return 0

        scan_result = scan_smi_files(paths)
        found = scan_result.files
        if not found:
            if scan_result.errors:
                self.drop_zone.configure(text=self._text(
                    'status_scan_errors', count=len(scan_result.errors),
                ))
            else:
                self.drop_zone.configure(text=self._text('status_no_files'))
            return 0

        self._start_conversion(found, scan_errors=len(scan_result.errors))
        return len(found)

    def _on_drop(self, event):
        self.add_paths(self.root.tk.splitlist(event.data))
        return 'break'

    def _start_conversion(self, files, scan_errors=0):
        if self.busy or not files:
            return
        self.busy = True
        overwrite = self.overwrite_existing.get()
        self.overwrite_checkbox.configure(state='disabled')
        self.drop_zone.configure(text=self._text('status_converting', count=len(files)))

        worker = threading.Thread(
            target=self._convert_worker,
            args=(tuple(files), overwrite, scan_errors),
            daemon=True,
        )
        worker.start()
        self.root.after(75, self._poll_worker)

    def _convert_worker(self, files, overwrite, scan_errors):
        summary = convert_smi_files(files, overwrite=overwrite)
        self.events.put(('done', summary, scan_errors))

    def _poll_worker(self):
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            if self.busy:
                self.root.after(75, self._poll_worker)
            return

        if event[0] == 'done':
            summary, scan_errors = event[1], event[2]
            self.busy = False
            self.overwrite_checkbox.configure(state='normal')
            self.drop_zone.configure(text=self._text(
                'status_done', total=summary.total, outputs=summary.outputs,
                existing=summary.existing, failed=summary.failed,
                scan_errors=scan_errors,
            ))

    def _close(self):
        if self.busy:
            messagebox.showinfo(
                self._text('dialog_busy_title'), self._text('dialog_busy_message'),
                parent=self.root,
            )
            return
        self.root.destroy()


def main(argv=None):
    initial_paths = sys.argv[1:] if argv is None else argv
    if initial_paths == ['--smoke-test']:
        app = Smi2AssApp()
        try:
            app.root.update_idletasks()
        finally:
            app.root.destroy()
        return 0

    app = Smi2AssApp()
    if initial_paths:
        app.add_paths(initial_paths)
    app.root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
