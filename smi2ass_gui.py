#!/usr/bin/env python3

import queue
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

from smi2ass import convert_smi_file
from smi2ass_gui_support import detect_ui_language, localized_text, scan_smi_files


class Smi2AssApp:
    def __init__(self, root=None):
        self.root = root or TkinterDnD.Tk()
        self.language = detect_ui_language()
        self.root.title(self._text('window_title'))
        self.root.minsize(720, 520)
        self.root.protocol('WM_DELETE_WINDOW', self._close)

        self.files = []
        self.row_ids = {}
        self.events = queue.Queue()
        self.busy = False
        self.overwrite_existing = tk.BooleanVar(master=self.root, value=False)

        self._build_ui()
        self.root.drop_target_register(DND_FILES)
        self.root.dnd_bind('<<Drop>>', self._on_drop)

    def _text(self, key, **values):
        return localized_text(key, self.language, **values)

    def _build_ui(self):
        frame = ttk.Frame(self.root, padding=16)
        frame.pack(fill='both', expand=True)

        ttk.Label(
            frame,
            text=self._text('heading'),
            font=('TkDefaultFont', 18, 'bold'),
        ).pack(anchor='w')
        ttk.Label(
            frame,
            text=self._text('intro'),
        ).pack(anchor='w', pady=(4, 12))

        self.drop_zone = ttk.Label(
            frame,
            text=self._text('drop_hint'),
            anchor='center',
            padding=22,
            relief='groove',
        )
        self.drop_zone.pack(fill='x', pady=(0, 12))
        self.drop_zone.drop_target_register(DND_FILES)
        self.drop_zone.dnd_bind('<<Drop>>', self._on_drop)

        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=(0, 8))
        self.add_files_button = ttk.Button(actions, text=self._text('file_button'), command=self._choose_files)
        self.add_files_button.pack(side='left')
        self.add_folder_button = ttk.Button(actions, text=self._text('folder_button'), command=self._choose_folder)
        self.add_folder_button.pack(side='left', padx=(8, 0))
        self.remove_button = ttk.Button(actions, text=self._text('remove_button'), command=self._remove_selected)
        self.remove_button.pack(side='left', padx=(8, 0))
        self.clear_button = ttk.Button(actions, text=self._text('clear_button'), command=self._clear)
        self.clear_button.pack(side='left', padx=(8, 0))

        columns = ('name', 'path', 'status')
        self.file_list = ttk.Treeview(frame, columns=columns, show='headings', height=9)
        self.file_list.heading('name', text=self._text('file_column'))
        self.file_list.heading('path', text=self._text('path_column'))
        self.file_list.heading('status', text=self._text('status_column'))
        self.file_list.column('name', width=190, stretch=False)
        self.file_list.column('path', width=360, stretch=True)
        self.file_list.column('status', width=160, stretch=False)
        self.file_list.pack(fill='both', expand=True)

        options = ttk.Frame(frame)
        options.pack(fill='x', pady=(8, 4))
        self.overwrite_checkbox = ttk.Checkbutton(
            options,
            text=self._text('overwrite'),
            variable=self.overwrite_existing,
        )
        self.overwrite_checkbox.pack(side='left')
        self.convert_button = ttk.Button(
            options,
            text=self._text('start'),
            command=self._start_conversion,
            state='disabled',
        )
        self.convert_button.pack(side='right')

        self.progress = ttk.Progressbar(frame, mode='determinate')
        self.progress.pack(fill='x', pady=(6, 4))
        self.status_label = ttk.Label(frame, text=self._text('status_add_hint'))
        self.status_label.pack(anchor='w')

        ttk.Label(frame, text=self._text('history')).pack(anchor='w', pady=(10, 3))
        self.log = tk.Text(frame, height=7, wrap='word', state='disabled')
        self.log.pack(fill='x')

    def add_paths(self, paths):
        if self.busy:
            self.status_label.configure(text=self._text('status_busy_add'))
            return 0

        scan_result = scan_smi_files(paths)
        found = scan_result.files
        added = 0
        for path in found:
            if path in self.row_ids:
                continue
            item_id = 'file-%d' % len(self.files)
            self.files.append(path)
            self.row_ids[path] = item_id
            self.file_list.insert(
                '', 'end', iid=item_id,
                values=(path.name, str(path.parent), self._text('status_pending')),
            )
            added += 1

        if added:
            self.status_label.configure(text=self._text('status_added', count=added))
            self.convert_button.configure(state='normal')
        elif not found and not scan_result.errors:
            self.status_label.configure(text=self._text('status_no_files'))
        elif not added and self.files and not scan_result.errors:
            self.status_label.configure(text=self._text('status_duplicate'))
        for path, error in scan_result.errors:
            self._append_log(self._text('log_folder_error', path=path, error=error))
        if scan_result.errors:
            self.status_label.configure(text=self._text(
                'status_scan_errors', added=added, errors=len(scan_result.errors),
            ))
        return added

    def _on_drop(self, event):
        self.add_paths(self.root.tk.splitlist(event.data))
        return 'break'

    def _choose_files(self):
        paths = filedialog.askopenfilenames(
            parent=self.root,
            title=self._text('dialog_select_files'),
            filetypes=(
                (self._text('smi_filter'), '*.smi *.SMI'),
                (self._text('all_files'), '*'),
            ),
        )
        if paths:
            self.add_paths(paths)

    def _choose_folder(self):
        path = filedialog.askdirectory(parent=self.root, title=self._text('dialog_select_folder'))
        if path:
            self.add_paths([path])

    def _remove_selected(self):
        selected = set(self.file_list.selection())
        if not selected:
            return
        self.files = [path for path in self.files if self.row_ids[path] not in selected]
        for item_id in selected:
            self.file_list.delete(item_id)
        self.row_ids = {path: self.row_ids[path] for path in self.files}
        self.convert_button.configure(state='normal' if self.files else 'disabled')
        self.status_label.configure(text=self._text('status_remaining', count=len(self.files)))

    def _clear(self):
        if self.busy:
            return
        self.files.clear()
        self.row_ids.clear()
        for item_id in self.file_list.get_children():
            self.file_list.delete(item_id)
        self.convert_button.configure(state='disabled')
        self.progress.configure(value=0)
        self.status_label.configure(text=self._text('status_add_hint'))

    def _append_log(self, message):
        self.log.configure(state='normal')
        self.log.insert('end', message + '\n')
        self.log.see('end')
        self.log.configure(state='disabled')

    def _start_conversion(self):
        if self.busy or not self.files:
            return
        self.busy = True
        self._completed = 0
        self._failed = 0
        self._skipped_existing = 0
        self._repaired_diagnostics = 0
        self._skipped_cues = 0
        self._total = len(self.files)
        self.progress.configure(maximum=self._total, value=0)
        self.convert_button.configure(state='disabled')
        self.overwrite_checkbox.configure(state='disabled')
        self._set_controls_enabled(False)
        self.status_label.configure(text=self._text('status_converting', completed=0, total=self._total))
        self._append_log(self._text(
            'log_conversion_start',
            overwrite=self._text('yes' if self.overwrite_existing.get() else 'no'),
        ))

        worker = threading.Thread(
            target=self._convert_worker,
            args=(tuple(self.files), self.overwrite_existing.get()),
            daemon=True,
        )
        worker.start()
        self.root.after(75, self._poll_worker)

    def _set_controls_enabled(self, enabled):
        state = 'normal' if enabled else 'disabled'
        for button in (
            self.add_files_button,
            self.add_folder_button,
            self.remove_button,
            self.clear_button,
        ):
            button.configure(state=state)

    def _convert_worker(self, files, overwrite):
        for path in files:
            try:
                result = convert_smi_file(path, overwrite=overwrite)
            except Exception as error:
                self.events.put(('error', path, error))
            else:
                self.events.put(('result', path, result))
        self.events.put(('done',))

    def _poll_worker(self):
        while True:
            try:
                event = self.events.get_nowait()
            except queue.Empty:
                break

            if event[0] == 'result':
                self._show_result(event[1], event[2])
            elif event[0] == 'error':
                path, error = event[1], event[2]
                self._failed += 1
                self._completed += 1
                self.progress.configure(value=self._completed)
                self.file_list.set(self.row_ids[path], 'status', self._text('status_error'))
                self._append_log(self._text('log_error', path=path, error=error))
            elif event[0] == 'done':
                self.busy = False
                self._set_controls_enabled(True)
                self.overwrite_checkbox.configure(state='normal')
                self.convert_button.configure(state='normal' if self.files else 'disabled')
                self.status_label.configure(
                    text=self._text(
                        'status_done', completed=self._completed, total=self._total,
                        repaired=self._repaired_diagnostics, skipped=self._skipped_cues,
                        existing=self._skipped_existing, failed=self._failed,
                    )
                )

        if self.busy:
            self.root.after(75, self._poll_worker)

    def _show_result(self, path, result):
        self._completed += 1
        self._repaired_diagnostics += sum(
            item.severity == 'repair' for item in result.diagnostics
        )
        self._skipped_cues += sum(
            item.severity == 'skip' for item in result.diagnostics
        )
        self.progress.configure(value=self._completed)
        self.status_label.configure(
            text=self._text('status_converting', completed=self._completed, total=self._total)
        )
        if result.skipped_existing:
            self._skipped_existing += len(result.skipped_existing)
            if result.outputs:
                self.file_list.set(self.row_ids[path], 'status', self._text('status_partial_existing'))
            else:
                self.file_list.set(self.row_ids[path], 'status', self._text('status_existing'))
            for output in result.skipped_existing:
                self._append_log(self._text('log_existing_kept', path=output))
        elif any(item.severity == 'skip' for item in result.diagnostics):
            self.file_list.set(self.row_ids[path], 'status', self._text('status_skipped_cues'))
        else:
            self.file_list.set(self.row_ids[path], 'status', self._text('status_complete'))

        for output in result.outputs:
            self._append_log(self._text('log_output', source=path, output=output))
        for diagnostic in result.diagnostics:
            self._append_log(self._text(
                'log_diagnostic', path=path, line=diagnostic.line,
                severity=diagnostic.severity, message=diagnostic.message,
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
