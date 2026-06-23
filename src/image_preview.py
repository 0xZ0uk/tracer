# SPDX-License-Identifier: MIT

"""Before/after image preview widgets."""

from pathlib import Path

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib, Gio, cairo

__all__ = ["PreviewArea"]


class PreviewArea(Gtk.Box):
    """Side-by-side (or single) preview of original vs vectorized result.

    Uses Gtk.Picture for raster images. Falls back to a label-based state
    when no image is loaded or the SVG can't be rendered via librsvg.
    """

    SVG_PREVIEW_SIZE = 600

    def __init__(self, **kwargs):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8, **kwargs)
        self.set_homogeneous(True)
        self.set_vexpand(True)
        self.set_hexpand(True)

        # Before box
        self._before_box = self._make_panel("Original", "before")
        self.append(self._before_box)

        # After box
        self._after_box = self._make_panel("Vectorized", "after")
        self.append(self._after_box)

        # Store the current images
        self._original_path = None
        self._svg_path = None
        self._last_error = None

    def _make_panel(self, label_text: str, name: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.set_vexpand(True)
        box.set_hexpand(True)

        label = Gtk.Label(label=label_text)
        label.set_xalign(0.0)
        label.add_css_class("heading")
        box.append(label)

        frame = Gtk.Frame()
        frame.set_vexpand(True)
        frame.set_hexpand(True)
        frame.add_css_class("border")
        box.append(frame)

        # Placeholder / picture inside frame
        placeholder = Gtk.Label(label="Drop an image here\nto convert")
        placeholder.set_vexpand(True)
        placeholder.set_valign(Gtk.Align.CENTER)
        placeholder.set_halign(Gtk.Align.CENTER)
        placeholder.add_css_class("dim-label")
        frame.set_child(placeholder)

        # Tag this frame with a name so we can find it later
        frame.set_name(f"{name}-frame")
        setattr(box, "_frame", frame)
        setattr(box, "_placeholder", placeholder)

        size_info = Gtk.Label(label="")
        size_info.add_css_class("caption")
        size_info.set_xalign(0.0)
        box.append(size_info)

        return box

    # ── public API ──────────────────────────────────────────────────

    def set_original_image(self, filepath: str | None):
        """Set the original (before) image."""
        self._original_path = filepath
        if filepath and self._file_exists(filepath):
            self._set_image_on_frame("before", filepath)
        else:
            self._clear_frame("before")
        self._update_size_info()

    def set_result_svg(self, filepath: str | None):
        """Set the result (after) SVG."""
        self._svg_path = filepath
        if filepath and self._file_exists(filepath):
            # We still show SVG as an image — Gtk.Picture with GdkPixbuf
            # fails for SVG. Use the file path display.
            self._set_svg_on_frame("after", filepath)
        else:
            self._clear_frame("after")
        self._update_size_info()

    def clear_all(self):
        """Reset both panels to empty state."""
        self._original_path = None
        self._svg_path = None
        self._clear_frame("before")
        self._clear_frame("after")
        self._update_size_info()

    # ── internals ───────────────────────────────────────────────────

    def _file_exists(self, path: str | None) -> bool:
        if not path:
            return False
        try:
            return GLib.file_test(path, GLib.FileTest.IS_REGULAR)
        except Exception:
            return False

    def _set_image_on_frame(self, side: str, filepath: str):
        """Load a raster image into one of the frames."""
        frame = self._find_frame(side)
        if frame is None:
            return

        try:
            pixbuf = GdkPixbuf.Pixbuf.new_from_file(filepath)
            pic = Gtk.Picture.new_for_pixbuf(pixbuf)
            pic.set_can_shrink(True)
            pic.set_vexpand(True)
            pic.set_hexpand(True)
            pic.set_keep_aspect_ratio(True)
            frame.set_child(pic)
        except GLib.GError as e:
            self._show_error_on_frame(side, f"Could not load image:\n{e.message}")

    def _set_svg_on_frame(self, side: str, filepath: str):
        """Try to render SVG preview. Falls back to showing the file info."""
        frame = self._find_frame(side)
        if frame is None:
            return

        # Try librsvg to render SVG -> Cairo surface -> GdkPixbuf
        try:
            import gi
            gi.require_version('Rsvg', '2.0')
            from gi.repository import Rsvg
            handle = Rsvg.Handle.new_from_file(filepath)
            dims = handle.get_dimensions()
            if dims.width > 0 and dims.height > 0:
                surf = cairo.ImageSurface(
                    cairo.Format.ARGB32,
                    min(dims.width, self.SVG_PREVIEW_SIZE),
                    min(dims.height, self.SVG_PREVIEW_SIZE),
                )
                cr = cairo.Context(surf)
                scale_x = self.SVG_PREVIEW_SIZE / dims.width if dims.width > self.SVG_PREVIEW_SIZE else 1.0
                scale_y = self.SVG_PREVIEW_SIZE / dims.height if dims.height > self.SVG_PREVIEW_SIZE else 1.0
                scale = min(scale_x, scale_y)
                cr.scale(scale, scale)
                handle.render_cairo(cr)

                # Convert cairo surface to GdkPixbuf and display
                pixbuf = Gdk.pixbuf_get_from_surface(surf, 0, 0, surf.get_width(), surf.get_height())
                pic = Gtk.Picture.new_for_pixbuf(pixbuf) if pixbuf else None
                if pic:
                    pic.set_can_shrink(True)
                    pic.set_vexpand(True)
                    pic.set_hexpand(True)
                    pic.set_keep_aspect_ratio(True)
                    frame.set_child(pic)
                    return
        except (ImportError, GLib.GError, Exception):
            pass

        # Fallback: show filename + size info
        fsize = Path(filepath).stat().st_size if Path(filepath).exists() else 0
        label = Gtk.Label(label=f"SVG saved ✓\n{Path(filepath).name}\n({self._fmt_size(fsize)})")
        label.set_vexpand(True)
        label.set_valign(Gtk.Align.CENTER)
        label.set_halign(Gtk.Align.CENTER)
        label.set_justify(Gtk.Justification.CENTER)
        label.add_css_class("dim-label")
        frame.set_child(label)

    def _show_error_on_frame(self, side: str, message: str):
        frame = self._find_frame(side)
        if frame is None:
            return
        label = Gtk.Label(label=message)
        label.set_vexpand(True)
        label.set_valign(Gtk.Align.CENTER)
        label.set_halign(Gtk.Align.CENTER)
        label.add_css_class("error")
        frame.set_child(label)

    def _clear_frame(self, side: str):
        frame = self._find_frame(side)
        if frame is None:
            return
        placeholder = Gtk.Label(label="Drop an image here\nto convert")
        placeholder.set_vexpand(True)
        placeholder.set_valign(Gtk.Align.CENTER)
        placeholder.set_halign(Gtk.Align.CENTER)
        placeholder.add_css_class("dim-label")
        frame.set_child(placeholder)

    def _find_frame(self, side: str) -> Gtk.Frame | None:
        """Find the frame widget tagged with *side* ('before' or 'after')."""
        for child in self:
            if hasattr(child, "_frame"):
                frame = child._frame
                if frame.get_name() == f"{side}-frame":
                    return frame
        return None

    def _update_size_info(self):
        """Update the size/caption labels below each panel."""
        for child in self:
            info_labels = [c for c in child if isinstance(c, Gtk.Label) and c.get_css_classes().count("caption")]
            if not info_labels:
                continue
            info = info_labels[-1]
            side = "before" if "before" in (child._frame.get_name() if hasattr(child, "_frame") else "") else "after"
            if side == "before" and self._original_path and Path(self._original_path).exists():
                p = Path(self._original_path)
                info.set_text(f"{p.name}  ·  {self._fmt_size(p.stat().st_size)}")
            elif side == "after" and self._svg_path and Path(self._svg_path).exists():
                p = Path(self._svg_path)
                info.set_text(f"{p.name}  ·  {self._fmt_size(p.stat().st_size)}")
            else:
                info.set_text("")

    @staticmethod
    def _fmt_size(size_bytes: int) -> str:
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 ** 2:
            return f"{size_bytes / 1024:.0f} KB"
        else:
            return f"{size_bytes / 1024 ** 2:.1f} MB"



