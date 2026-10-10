#!/usr/bin/env python3

from dataclasses import asdict
import queue
import sys
import threading
import tkinter as tk
from tkinter import font, messagebox, ttk

from tkinterdnd2 import COPY, DND_FILES, REFUSE_DROP, TkinterDnD

from smi2ass_gui_support import (
    convert_smi_files,
    detect_ui_language,
    localized_text,
    scan_smi_files,
)

from smi2ass_gui_theme import (
    LIGHT,
    ThemeWatcher,
    configure_native_appearance,
    detect_system_theme,
    get_palette,
    selection_text_color,
)


class Smi2AssApp:
    def __init__(self, root=None):
        self.root = root or TkinterDnD.Tk()
        self.language = detect_ui_language()
        self.root.title(self._text('window_title'))
        self.root.geometry('400x280')
        self.root.minsize(320, 260)
        self.root.protocol('WM_DELETE_WINDOW', self._close)

        self.events = queue.Queue()
        self.busy = False
        self.overwrite_existing = tk.BooleanVar(master=self.root, value=False)
        self.drop_state = 'idle'
        self.state_values = {}
        self.dragging = False
        self._redraw_id = None
        self._disposed = False
        self._poll_id = None
        self.palette = asdict(LIGHT)
        configure_native_appearance(self.root, detect_system_theme(self.root))
        self._build_ui()
        for target in (self.root, self.drop_zone, self.overwrite_checkbox):
            target.drop_target_register(DND_FILES)
            target.dnd_bind('<<Drop>>', self._on_drop)
            target.dnd_bind('<<DropEnter>>', self._on_drop_enter)
            target.dnd_bind('<<DropLeave>>', self._on_drop_leave)
        self.root.update_idletasks()
        self.theme_watcher = ThemeWatcher(self.root, self._apply_theme)
        self.theme_watcher.start()
        # Watcher teardown runs before this handler can delete its Tcl bindings.
        self.root.bind('<Destroy>', self._on_destroy, add='+')

    def _text(self, key, **values):
        return localized_text(key, self.language, **values)

    def _build_ui(self):
        self.frame = tk.Frame(self.root, padx=16, pady=16, bg=self.palette['background'])
        self.frame.pack(fill='both', expand=True)
        default_font = font.nametofont('TkDefaultFont', root=self.root)
        self.title_font = default_font.copy()
        self.title_font.configure(size=max(14, default_font.actual('size')), weight='normal')
        self.detail_font = default_font.copy()
        self.detail_font.configure(size=max(11, default_font.actual('size') - 2))
        self.style = ttk.Style(self.root)
        self.style.configure('Converter.TCheckbutton', background=self.palette['background'],
                             foreground=self.palette['text'])
        self.drop_zone = tk.Canvas(self.frame, highlightthickness=0, borderwidth=0,
                                   bg=self.palette['background'], takefocus=False)
        self.frame.columnconfigure(0, weight=1)
        self.frame.rowconfigure(0, weight=1)
        self.drop_zone.grid(row=0, column=0, sticky='nsew')
        self.drop_zone.bind('<Configure>', self._queue_redraw)
        self.overwrite_checkbox = ttk.Checkbutton(
            self.frame, text=self._text('overwrite'), variable=self.overwrite_existing,
            style='Converter.TCheckbutton',
        )
        self.overwrite_checkbox.grid(row=1, column=0, sticky='w', pady=(12, 0))
        self._update_minimum_size()
        self._queue_redraw()

    def _update_minimum_size(self):
        # Reserve three result lines and two title lines even at larger font sizes.
        content_height = (28 + 18 + 2 * self.title_font.metrics('linespace')
                          + 3 * self.detail_font.metrics('linespace') + 24)
        height = content_height + self.overwrite_checkbox.winfo_reqheight() + 44
        # Normal typography fits the compact window; larger accessibility fonts grow it.
        normal_height = (28 + 18 + self.title_font.metrics('linespace')
                         + 3 * self.detail_font.metrics('linespace') + 24
                         + self.overwrite_checkbox.winfo_reqheight() + 44)
        reserve = height if self.title_font.actual('size') > 18 else normal_height
        result_width = max(self.detail_font.measure(line) for line in self._text(
            'result_summary', total=99999, outputs=99999, existing=99999, failed=99999, scan_errors=99999,
        ).splitlines())
        self.root.minsize(max(320, result_width + 72, self.overwrite_checkbox.winfo_reqwidth() + 32),
                          max(260, reserve))

    def _apply_theme(self, mode):
        self.theme_mode = mode
        self.palette = asdict(get_palette(self.root, mode))
        colors = self.palette
        self.root.configure(background=colors['background'])
        self.frame.configure(background=colors['background'])
        self.drop_zone.configure(background=colors['background'])
        if self.root.tk.call('tk', 'windowingsystem') == 'win32':
            if self.style.theme_use() != 'clam':
                self.style.theme_use('clam')
            configure_native_appearance(self.root, mode)
        self.style.configure('Converter.TCheckbutton', background=colors['background'],
                             foreground=colors['text'], focuscolor=colors['accent'],
                             indicatorbackground=colors['surface'], bordercolor=colors['border'])
        mark = selection_text_color(self.root, mode)
        self.style.map('Converter.TCheckbutton',
                       background=[('active', colors['background'])],
                       foreground=[('disabled', colors['muted'])],
                       indicatorbackground=[('disabled', colors['background']), ('selected', colors['accent'])],
                       indicatorforeground=[('disabled', colors['muted']), ('selected', mark)])
        self._queue_redraw()

    def _queue_redraw(self, event=None):
        if self._redraw_id is None and not self._disposed:
            self._redraw_id = self.root.after_idle(self._render_drop_state)

    def _set_drop_state(self, state, **values):
        self.drop_state = state
        self.state_values = values
        self._queue_redraw()

    def _state_copy(self):
        if self.dragging and not self.busy:
            return self._text('drop_ready'), self._text('drop_detail')
        state = self.drop_state
        if state == 'idle':
            return self._text('drop_hint'), self._text('drop_detail')
        if state == 'converting':
            return self._text('status_converting_title'), self._text('status_converting_detail', **self.state_values)
        if state in ('done', 'failed', 'partial'):
            title = {'done': 'status_done_title', 'failed': 'status_failed_title',
                     'partial': 'status_partial_title'}[state]
            return self._text(title), self._text('result_summary', **self.state_values)
        if state == 'scan_error':
            return self._text('status_scan_title'), self._text('status_scan_errors', **self.state_values)
        if state == 'busy_add':
            return self._text('status_converting_title'), self._text('status_busy_add')
        return self._text('status_empty_title'), self._text('drop_again')

    def _render_drop_state(self):
        self._redraw_id = None
        canvas = self.drop_zone
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if self._disposed or width < 30 or height < 30:
            return
        canvas.delete('all')
        colors = self.palette
        edge = colors['accent'] if self.dragging and not self.busy else colors['border']
        # Duplicate the points along straight edges to keep the rounded shape flat.
        r, x, y, w, h = 12, 1, 1, width - 1, height - 1
        canvas.create_polygon(
            x+r, y, x+r, y, w-r, y, w-r, y, w, y, w, y+r, w, y+r,
            w, h-r, w, h-r, w, h, w-r, h, w-r, h, x+r, h, x+r, h,
            x, h, x, h-r, x, h-r, x, y+r, x, y+r, x, y,
            smooth=True, splinesteps=24, fill=colors['surface'], outline=edge,
            width=2 if self.dragging and not self.busy else 1,
        )
        title, detail = self._state_copy()
        text_width = max(40, width - 40)
        title_id = canvas.create_text(width/2, 0, text=title, font=self.title_font,
                                      fill=colors['text'], width=text_width,
                                      anchor='n', justify='center', tags=('content', 'title'))
        detail_id = canvas.create_text(width/2, 0, text=detail, font=self.detail_font,
                                       fill=colors['muted'], width=text_width,
                                       anchor='n', justify='center', tags=('content', 'detail'))
        title_box, detail_box = canvas.bbox(title_id), canvas.bbox(detail_id)
        title_height, detail_height = title_box[3]-title_box[1], detail_box[3]-detail_box[1]
        group_height = 28 + 12 + title_height + 6 + detail_height
        top = max(12, (height-group_height)/2)
        self._draw_file_icon(width/2 - 11, top, colors['accent'])
        canvas.coords(title_id, width/2, top+40)
        canvas.coords(detail_id, width/2, top+40+title_height+6)

    def _draw_file_icon(self, x, y, color):
        canvas = self.drop_zone
        options = dict(fill=color, width=1.5, capstyle='round', joinstyle='round', tags=('content', 'icon'))
        canvas.create_line(x+1, y+28, x+1, y+1, x+15, y+1, x+23, y+9,
                           x+23, y+28, x+1, y+28, **options)
        canvas.create_line(x+15, y+1, x+15, y+9, x+23, y+9, **options)
        for end, offset in ((17, 15), (12, 20), (17, 25)):
            canvas.create_line(x+6, y+offset, x+end, y+offset, **options)

    def _on_drop_enter(self, event):
        if self.busy:
            return REFUSE_DROP
        self.dragging = True
        self._queue_redraw()
        return COPY

    def _on_drop_leave(self, event):
        self.dragging = False
        self._queue_redraw()
        return COPY

    def add_paths(self, paths):
        if self.busy:
            self._set_drop_state('busy_add')
            return 0
        scan_result = scan_smi_files(paths)
        found = scan_result.files
        if not found:
            if scan_result.errors:
                self._set_drop_state('scan_error', count=len(scan_result.errors))
            else:
                self._set_drop_state('empty')
            return 0
        self._start_conversion(found, scan_errors=len(scan_result.errors))
        return len(found)

    def _on_drop(self, event):
        self.dragging = False
        if self.busy:
            return REFUSE_DROP
        self.add_paths(self.root.tk.splitlist(event.data))
        return COPY

    def _start_conversion(self, files, scan_errors=0):
        if self.busy or not files:
            return
        self.busy = True
        overwrite = self.overwrite_existing.get()
        self.overwrite_checkbox.configure(state='disabled')
        self._set_drop_state('converting', count=len(files))
        threading.Thread(target=self._convert_worker, args=(self.events, tuple(files), overwrite, scan_errors),
                         daemon=True).start()
        self._poll_id = self.root.after(75, self._poll_worker)

    @staticmethod
    def _convert_worker(events, files, overwrite, scan_errors):
        # The worker owns conversion data only, never a Tk window or interpreter.
        summary = convert_smi_files(files, overwrite=overwrite)
        events.put(('done', summary, scan_errors))

    def _poll_worker(self):
        self._poll_id = None
        if self._disposed:
            return
        try:
            event = self.events.get_nowait()
        except queue.Empty:
            if self.busy:
                self._poll_id = self.root.after(75, self._poll_worker)
            return
        if event[0] == 'done':
            summary, scan_errors = event[1], event[2]
            self.busy = False
            self.overwrite_checkbox.configure(state='normal')
            state = 'done'
            if summary.failed or scan_errors:
                state = 'partial' if summary.outputs or summary.existing else 'failed'
            self._set_drop_state(state,
                                 total=summary.total, outputs=summary.outputs,
                                 existing=summary.existing, failed=summary.failed, scan_errors=scan_errors)

    def _on_destroy(self, event):
        if event.widget is self.root:
            self._dispose(destroy=False)

    def _dispose(self, destroy=True):
        if self._disposed:
            return
        self._disposed = True
        if hasattr(self, 'theme_watcher'):
            self.theme_watcher.stop()
        for identity in (self._redraw_id, self._poll_id):
            if identity is not None:
                self.root.after_cancel(identity)
        self._redraw_id = self._poll_id = None
        # Finalize Tcl variables and fonts on the UI thread, before worker GC.
        self.overwrite_existing = None
        self.title_font = self.detail_font = None
        if destroy:
            self.root.destroy()

    def _close(self):
        if self.busy:
            messagebox.showinfo(self._text('dialog_busy_title'), self._text('dialog_busy_message'), parent=self.root)
            return
        self._dispose()


def main(argv=None):
    initial_paths = sys.argv[1:] if argv is None else argv
    if initial_paths == ['--smoke-test']:
        app = Smi2AssApp()
        try:
            app.root.update_idletasks()
        finally:
            app._dispose()
        return 0
    app = Smi2AssApp()
    if initial_paths:
        app.add_paths(initial_paths)
    app.root.mainloop()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
