# SPDX-License-Identifier: MIT

"""Main window — the primary UI layout for tracer."""

from pathlib import Path

from gi.repository import Gtk, Adw, GLib, Gdk, Gio, GObject

from converter import Converter
from settings_panel import SettingsPanel
from image_preview import PreviewArea
from batch import BatchDialog

__all__ = ["VtracerWindow"]


class VtracerWindow(Adw.ApplicationWindow):
    """The application's main window."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.set_default_size(900, 650)
        self.set_title("VTracer GTK")

        self._converter = Converter()
        self._current_image_path = None
        self._last_svg_path = None

        self._build_ui()
        self._setup_drag_drop()
        self._connect_settings()

    # ── UI construction ──────────────────────────────────────────────

    def _build_ui(self):
        # Toast overlay at the root
        self._toast_overlay = Adw.ToastOverlay.new()
        self.set_content(self._toast_overlay)

        # Main box
        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self._toast_overlay.set_child(main_box)

        # Header bar
        header = Adw.HeaderBar()
        main_box.append(header)

        # App menu button (gear)
        menu = Gtk.MenuButton()
        menu.set_icon_name("open-menu-symbolic")
        menu.set_tooltip_text("Menu")
        menu_model = Gio.Menu.new()
        menu_model.append("About", "win.about")
        menu_model.append("_Quit", "app.quit")
        popover = Gtk.PopoverMenu()
        popover.set_menu_model(menu_model)
        menu.set_popover(popover)
        header.pack_end(menu)

        # Open button
        open_btn = Gtk.Button(label="Open Image")
        open_btn.add_css_class("flat")
        open_btn.set_icon_name("document-open-symbolic")
        open_btn.connect("clicked", self._on_open_clicked)
        header.pack_start(open_btn)

        # Batch button
        batch_btn = Gtk.Button(label="Batch")
        batch_btn.add_css_class("flat")
        batch_btn.set_icon_name("folder-symbolic")
        batch_btn.connect("clicked", self._on_batch_clicked)
        header.pack_start(batch_btn)

        # Content — split pane
        self._content_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self._content_box.set_vexpand(True)
        self._content_box.set_hexpand(True)
        main_box.append(self._content_box)

        # Left: preview
        self._preview = PreviewArea()
        self._preview.set_vexpand(True)
        self._preview.set_hexpand(True)
        self._content_box.append(self._preview)

        # Separator
        sep = Gtk.Separator(orientation=Gtk.Orientation.VERTICAL)
        self._content_box.append(sep)

        # Right: settings in a scrolled window
        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_min_content_width(320)
        scroll.set_max_content_width(360)
        self._settings = SettingsPanel()
        scroll.set_child(self._settings)
        self._content_box.append(scroll)

        # Status bar at bottom
        status_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        status_bar.set_margin_start(8)
        status_bar.set_margin_end(8)
        status_bar.set_margin_top(4)
        status_bar.set_margin_bottom(4)
        main_box.append(status_bar)

        self._status_label = Gtk.Label(label="Drop an image or click Open to start")
        self._status_label.set_hexpand(True)
        self._status_label.set_xalign(0.0)
        self._status_label.add_css_class("dim-label")
        status_bar.append(self._status_label)

        self._convert_btn = Gtk.Button(label="Convert → SVG")
        self._convert_btn.add_css_class("suggested-action")
        self._convert_btn.set_sensitive(False)
        self._convert_btn.connect("clicked", self._on_convert_clicked)
        status_bar.append(self._convert_btn)

    # ── drag & drop ─────────────────────────────────────────────────

    def _setup_drag_drop(self):
        drop_target = Gtk.DropTarget.new(Gdk.FileList, Gdk.DragAction.COPY)
        drop_target.connect("accept", self._on_drop_accept)
        drop_target.connect("drop", self._on_drop)
        self.add_controller(drop_target)

    @staticmethod
    def _on_drop_accept(_target, _dropper) -> bool:
        return True

    def _on_drop(self, _target, value, _x, _y) -> bool:
        file_list = value
        if file_list is None:
            return False
        files = file_list.get_files()
        if not files:
            return False
        path = files[0].get_path()
        if path and Converter.is_supported_image(path):
            self._load_image(path)
            return True
        self._show_toast("Unsupported file type")
        return False

    # ── settings ↔ converter sync ──────────────────────────────────

    def _connect_settings(self):
        self._settings.connect("params-changed", self._on_params_changed)
        # Apply preset on change: update converter params
        self._on_params_changed()

    def _on_params_changed(self, *_args):
        values = self._settings.get_values()
        # Handle preset selection
        preset = values.pop("_preset", None)
        if preset and preset != "custom":
            self._converter.apply_preset(preset)
            # Read back the preset values into the UI
            current = self._converter.get_params()
            self._settings.set_values(**current)
            self._settings.set_values(_preset=preset)
        else:
            self._converter.set_params(**values)

    # ── actions ─────────────────────────────────────────────────────

    def _on_open_clicked(self, _btn):
        dialog = Gtk.FileDialog.new()
        dialog.set_title("Select Image")

        # Build filter list
        filter_images = Gtk.FileFilter()
        filter_images.set_name("Images")
        for ext in Converter.supported_input_extensions():
            filter_images.add_pattern(f"*{ext}")

        filter_all = Gtk.FileFilter()
        filter_all.set_name("All Images")
        filter_all.add_mime_type("image/png")
        filter_all.add_mime_type("image/jpeg")
        filter_all.add_mime_type("image/webp")
        filter_all.add_mime_type("image/tiff")
        filter_all.add_mime_type("image/bmp")

        filter_list = Gio.ListStore.new(Gtk.FileFilter)
        filter_list.append(filter_images)
        filter_list.append(filter_all)

        dialog.set_filters(filter_list)
        dialog.set_default_filter(filter_images)

        dialog.open(callback=self._on_open_finished)

    def _on_open_finished(self, dialog, result):
        try:
            file = dialog.open_finish(result)
            if file:
                self._load_image(file.get_path())
        except GLib.GError:
            pass

    def _load_image(self, path: str):
        self._current_image_path = path
        self._preview.set_original_image(path)
        self._convert_btn.set_sensitive(True)
        self._status_label.set_text(f"Loaded: {Path(path).name}")
        self._last_svg_path = None

    def _on_convert_clicked(self, _btn):
        if not self._current_image_path:
            return

        output_path = Converter.suggest_output_path(
            self._current_image_path,
            output_dir=str(Path(self._current_image_path).parent),
        )
        # Make it unique-ish if same name exists
        output_path = self._unique_path(output_path)

        self._convert_btn.set_sensitive(False)
        self._convert_btn.set_label("Converting…")
        self._status_label.set_text("Converting…")

        # Read current values from settings
        values = self._settings.get_values()
        values.pop("_preset", None)

        self._converter.convert_async(
            self._current_image_path,
            output_path,
            on_done=self._on_conversion_done,
            **values,
        )

    def _on_conversion_done(self, result):
        self._convert_btn.set_sensitive(True)
        self._convert_btn.set_label("Convert → SVG")

        if result.success:
            self._last_svg_path = result.output_path
            self._preview.set_result_svg(result.output_path)
            self._status_label.set_text(
                f"Converted: {Path(result.output_path).name}"
            )
            self._show_toast("SVG saved successfully")
        else:
            self._status_label.set_text(f"Error: {result.error}")
            self._show_error_toast(result.error)

    def _on_batch_clicked(self, _btn):
        dialog = BatchDialog(self._converter, parent_window=self)
        dialog.present(self)

    # ── helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _unique_path(path: str) -> str:
        """If the path exists, append a counter before the extension."""
        p = Path(path)
        if not p.exists():
            return path
        counter = 1
        while True:
            new = p.with_stem(f"{p.stem}_{counter}")
            if not new.exists():
                return str(new)
            counter += 1

    def _show_toast(self, msg: str):
        toast = Adw.Toast.new(msg)
        self._toast_overlay.add_toast(toast)

    def _show_error_toast(self, msg: str):
        toast = Adw.Toast.new(f"Error: {msg}")
        toast.set_priority(Adw.ToastPriority.HIGH)
        self._toast_overlay.add_toast(toast)
