# SPDX-License-Identifier: MIT

"""Batch conversion dialog — select a folder and process all supported images."""

from pathlib import Path
from gi.repository import Gtk, Adw, GLib, GObject

__all__ = ["BatchDialog"]


class BatchDialog(Adw.Dialog):
    """Dialog for batch-converting all images in a folder."""

    def __init__(self, converter, parent_window=None, toast_overlay=None, **kwargs):
        super().__init__(**kwargs)
        self.set_title("Batch Convert")
        self.set_content_width(600)
        self.set_content_height(500)

        self._converter = converter
        self._parent = parent_window
        self._toast_overlay = toast_overlay
        self._input_dir = None
        self._output_dir = None
        self._file_list = []
        self._processed = 0
        self._total = 0
        self._running = False

        self._build_ui()

    # ── build ───────────────────────────────────────────────────────

    def _build_ui(self):
        page = Adw.PreferencesPage.new()
        self.set_content(page)
        self.set_can_close(True)

        group = Adw.PreferencesGroup()
        group.set_title("Batch Conversion")
        group.set_description("Process all supported images in a folder")
        page.add(group)

        # Input folder
        self._input_row = Adw.ActionRow()
        self._input_row.set_title("Input Folder")
        self._input_row.set_subtitle("Choose a folder containing images…")
        btn = Gtk.Button(label="Browse…")
        btn.add_css_class("flat")
        btn.connect("clicked", self._on_pick_input)
        self._input_row.add_suffix(btn)
        group.add(self._input_row)

        # Output folder
        self._output_row = Adw.ActionRow()
        self._output_row.set_title("Output Folder")
        self._output_row.set_subtitle("Choose where to save SVGs…")
        btn2 = Gtk.Button(label="Browse…")
        btn2.add_css_class("flat")
        btn2.connect("clicked", self._on_pick_output)
        self._output_row.add_suffix(btn2)
        group.add(self._output_row)

        # File list (scrolled)
        frame = Gtk.Frame()
        frame.set_vexpand(True)
        frame.set_margin_top(12)
        frame.set_margin_bottom(12)
        self._list_view = Gtk.ColumnView.new()
        selection = Gtk.NoSelection.new(Gtk.StringList.new())
        self._list_view.set_model(selection)

        col = Gtk.ColumnViewColumn.new("Images")
        factory = Gtk.SignalListItemFactory()
        factory.connect("setup", self._on_factory_setup)
        col.set_factory(factory)
        self._list_view.append_column(col)

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_hexpand(True)
        scroll.set_child(self._list_view)
        frame.set_child(scroll)
        group.add(frame)

        self._file_count_label = Gtk.Label(label="No images found")
        self._file_count_label.add_css_class("dim-label")
        self._file_count_label.set_xalign(0.0)
        group.add(self._file_count_label)

        # Progress bar
        self._progress_bar = Gtk.ProgressBar()
        self._progress_bar.set_margin_top(8)
        self._progress_bar.set_margin_bottom(8)
        self._progress_bar.set_visible(False)
        group.add(self._progress_bar)

        self._status_label = Gtk.Label(label="")
        self._status_label.add_css_class("dim-label")
        self._status_label.set_xalign(0.0)
        group.add(self._status_label)

        # Buttons
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self._cancel_btn = Gtk.Button(label="Cancel")
        self._cancel_btn.connect("clicked", lambda *a: self.close())
        btn_box.append(self._cancel_btn)

        self._convert_btn = Gtk.Button(label="Convert All")
        self._convert_btn.add_css_class("suggested-action")
        self._convert_btn.connect("clicked", self._on_convert)
        btn_box.append(self._convert_btn)
        group.add(btn_box)

        self._convert_btn.set_sensitive(False)

    # ── factory callbacks ───────────────────────────────────────────

    @staticmethod
    def _on_factory_setup(_factory, list_item):
        label = Gtk.Label()
        label.set_xalign(0.0)
        label.set_ellipsize(3)  # PANGO_ELLIPSIZE_END
        label.set_margin_start(8)
        list_item.set_child(label)

        list_item.connect("bind", lambda li: _bind_label(li, label))

        def _bind_label(li, lbl):
            obj = li.get_item()
            if obj:
                lbl.set_text(obj.get_string())

    # ── folder selection ────────────────────────────────────────────

    def _on_pick_input(self, _btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Input Folder")
        dialog.select_folder(callback=self._on_input_folder_selected)

    def _on_input_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self._input_dir = folder.get_path()
                self._input_row.set_subtitle(self._input_dir)
                self._scan_folder()
        except GLib.GError:
            pass

    def _on_pick_output(self, _btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Output Folder")
        dialog.select_folder(callback=self._on_output_folder_selected)

    def _on_output_folder_selected(self, dialog, result):
        try:
            folder = dialog.select_folder_finish(result)
            if folder:
                self._output_dir = folder.get_path()
                self._output_row.set_subtitle(self._output_dir)
                self._update_convert_button()
        except GLib.GError:
            pass

    # ── scanning ────────────────────────────────────────────────────

    def _scan_folder(self):
        from converter import Converter

        if not self._input_dir:
            return

        self._file_list = []
        supported = set(Converter.supported_input_extensions())
        for f in sorted(Path(self._input_dir).iterdir()):
            if f.is_file() and f.suffix.lower() in supported:
                self._file_list.append(str(f))

        # Update list model
        store = Gtk.StringList.new(self._file_list)
        self._list_view.set_model(Gtk.NoSelection.new(store))

        self._file_count_label.set_text(
            f"{len(self._file_list)} image{'s' if len(self._file_list) != 1 else ''} found"
        )
        self._update_convert_button()

    def _update_convert_button(self):
        ready = len(self._file_list) > 0 and bool(self._output_dir)
        self._convert_btn.set_sensitive(ready and not self._running)

    # ── conversion ──────────────────────────────────────────────────

    def _on_convert(self, _btn):
        if self._running or not self._output_dir:
            return

        self._running = True
        self._processed = 0
        self._total = len(self._file_list)
        self._convert_btn.set_sensitive(False)
        self._cancel_btn.set_sensitive(False)
        self._progress_bar.set_visible(True)
        self._progress_bar.set_fraction(0.0)
        self._status_label.set_text(f"0 / {self._total} converted")

        self._process_next()

    def _process_next(self):
        if self._processed >= self._total:
            self._on_batch_done()
            return

        input_path = self._file_list[self._processed]
        output_path = str(Path(self._output_dir) / f"{Path(input_path).stem}.svg")

        def on_done(result):
            self._processed += 1
            fraction = self._processed / self._total
            self._progress_bar.set_fraction(fraction)
            self._status_label.set_text(
                f"{self._processed} / {self._total} converted"
                + (" — last: OK" if result.success else f" — last: {result.error}")
            )
            # Update file list to show status
            GLib.idle_add(self._process_next, priority=GLib.PRIORITY_DEFAULT)

        self._converter.convert_async(input_path, output_path, on_done=on_done)

    def _on_batch_done(self):
        self._running = False
        self._convert_btn.set_sensitive(False)
        self._cancel_btn.set_sensitive(True)
        self._status_label.set_text(f"Done — {self._processed} / {self._total} converted")

        toast = Adw.Toast.new(f"Batch complete — {self._processed} SVG files created")
        if self._toast_overlay is not None:
            self._toast_overlay.add_toast(toast)
