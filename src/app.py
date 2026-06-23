# SPDX-License-Identifier: MIT

"""Application entry point — Adw.Application subclass."""

import sys

from gi.repository import Gtk, Adw, Gio

from window import VtracerWindow

__all__ = ["VtracerApplication"]


class VtracerApplication(Adw.Application):
    """The VTracer GTK application."""

    def __init__(self, **kwargs):
        super().__init__(
            application_id="com.github.z0uk.vtracer-gtk",
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            **kwargs,
        )

        # Actions
        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *a: self.quit())
        self.add_action(quit_action)

        about_action = Gio.SimpleAction.new("about", None)
        about_action.connect("activate", self._on_about)
        self.add_action(about_action)

        self._window = None

    def do_activate(self):
        if self._window is not None:
            self._window.present()
            return

        win = VtracerWindow(application=self)
        win.present()
        self._window = win

    def _on_about(self, *_args):
        about = Adw.AboutDialog(
            application_name="VTracer GTK",
            version="0.1.0",
            developer_name="Z0uk",
            license_type=Gtk.License.MIT,
            comments="Convert raster images to vector SVG graphics",
            website="https://github.com/z0uk/vtracer-gtk",
            issue_url="https://github.com/z0uk/vtracer-gtk/issues",
        )
        about.present(self._window)


def main():
    """Entry point called by the wrapper script."""
    app = VtracerApplication()
    return app.run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())
