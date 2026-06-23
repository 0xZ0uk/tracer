# SPDX-License-Identifier: MIT

"""Settings panel — all vtracer parameters as libadwaita preference widgets."""

from gi.repository import Gtk, Adw, GLib, GObject

__all__ = ["SettingsPanel"]

# ── helpers ──────────────────────────────────────────────────────────

def _combo_model(*items):
    """Create a Gtk.StringList from positional strings."""
    store = Gtk.StringList.new()
    for item in items:
        store.append(item)
    return store


# ── Settings Panel ────────────────────────────────────────────────────

class SettingsPanel(Adw.PreferencesPage):
    """A preferences page exposing all vtracer parameters as editable controls.

    Emits a ``params-changed`` signal whenever any value is modified.
    Call ``get_values()`` to read the current state.
    """

    __gsignals__ = {
        "params-changed": (
            GObject.SignalFlags.RUN_FIRST,
            None,
            (),  # no arguments — call get_values() to read
        ),
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self._preset_row = None
        self._param_widgets = {}  # param_name -> Adw.SpinRow | Adw.ComboRow

        self._build_mode_group()
        self._build_parameter_group()
        self._build_post_group()
        self._set_preset("custom")

    # ── public API ──────────────────────────────────────────────────

    def get_values(self) -> dict:
        """Read current widget values into a dict suitable for ``Converter.set_params``."""
        vals = {}
        for name, widget in self._param_widgets.items():
            if isinstance(widget, Adw.ComboRow):
                text = widget.get_selected_item()
                vals[name] = text.get_string() if text else None
            elif isinstance(widget, Adw.SpinRow):
                vals[name] = widget.get_value()
            elif isinstance(widget, Adw.SwitchRow):
                vals[name] = widget.get_active()
        # The preset row selects a preset rather than a direct param
        preset_name = self._read_preset()
        if preset_name:
            vals["_preset"] = preset_name
        return vals

    def set_values(self, **kwargs):
        """Programmatically set widget values. Silently ignores unknown keys."""
        for name, value in kwargs.items():
            w = self._param_widgets.get(name)
            if w is None:
                continue
            if isinstance(w, Adw.ComboRow):
                self._set_combo_value(w, str(value))
            elif isinstance(w, Adw.SpinRow):
                w.set_value(value)
            elif isinstance(w, Adw.SwitchRow):
                w.set_active(bool(value))
            elif name == "_preset":
                self._set_preset(value)

    # ── preset management ───────────────────────────────────────────

    def _read_preset(self) -> str | None:
        if self._preset_row is None:
            return None
        item = self._preset_row.get_selected_item()
        return item.get_string().lower() if item else "custom"

    def _set_preset(self, name: str):
        if self._preset_row is None:
            return
        self._set_combo_value(self._preset_row, name)

    def _on_preset_changed(self, row, _pspec):
        preset = row.get_selected_item()
        if preset is None:
            return
        name = preset.get_string().lower()
        self.emit("params-changed")

    # ── build UI ────────────────────────────────────────────────────

    def _build_mode_group(self):
        group = Adw.PreferencesGroup()
        group.set_title("Mode")
        group.set_description("Vectorization mode and algorithm settings")
        self.add(group)

        # Preset selector
        self._preset_row = Adw.ComboRow()
        self._preset_row.set_title("Preset")
        self._preset_row.set_subtitle("Quick configuration presets")
        self._preset_row.set_model(_combo_model("Custom", "BW", "Poster", "Photo"))
        self._preset_row.connect("notify::selected-item", self._on_preset_changed)
        group.add(self._preset_row)
        self._param_widgets["_preset"] = self._preset_row

        # Color mode
        cm = Adw.ComboRow()
        cm.set_title("Color Mode")
        cm.set_subtitle("'Color' for full color, 'BW' for binary black & white")
        cm.set_model(_combo_model("color", "bw"))
        cm.connect("notify::selected-item", lambda *a: self.emit("params-changed"))
        group.add(cm)
        self._param_widgets["colormode"] = cm

        # Curve fitting mode
        fit = Adw.ComboRow()
        fit.set_title("Fitting Mode")
        fit.set_subtitle("Pixel → Polygon → Spline (quality increases)")
        fit.set_model(_combo_model("pixel", "polygon", "spline"))
        fit.connect("notify::selected-item", lambda *a: self.emit("params-changed"))
        group.add(fit)
        self._param_widgets["mode"] = fit

        # Hierarchical
        hier = Adw.ComboRow()
        hier.set_title("Hierarchical")
        hier.set_subtitle("'Stacked' for overlapping shapes, 'Cutout' for non-overlapping")
        hier.set_model(_combo_model("stacked", "cutout"))
        hier.connect("notify::selected-item", lambda *a: self.emit("params-changed"))
        group.add(hier)
        self._param_widgets["hierarchical"] = hier

    def _build_parameter_group(self):
        group = Adw.PreferencesGroup()
        group.set_title("Parameters")
        group.set_description("Fine-tune the vectorization quality")
        self.add(group)

        # Color precision
        self._add_spin(group, "color_precision", "Color Precision",
                        "Significant bits per RGB channel (1-8). Lower = fewer colors.",
                        6, 1, 8, 1)

        # Corner threshold
        self._add_spin(group, "corner_threshold", "Corner Threshold",
                        "Minimum angle (°) to detect a corner. Higher = fewer corners.",
                        60, 0, 180, 1)

        # Filter speckle
        self._add_spin(group, "filter_speckle", "Filter Speckle",
                        "Discard patches smaller than this many pixels.",
                        4, 0, 200, 1)

        # Layer difference (gradient step)
        self._add_spin(group, "layer_difference", "Gradient Step",
                        "Color difference between gradient layers (1-255). Lower = more colors.",
                        16, 1, 255, 1)

        # Length threshold (segment length)
        self._add_spin(group, "length_threshold", "Segment Length",
                        "Max segment length for subdivision. Smaller = smoother curves.",
                        3.5, 0.0, 50.0, 0.1, digits=1)

        # Splice threshold
        self._add_spin(group, "splice_threshold", "Splice Threshold",
                        "Minimum angle (°) to splice a spline.",
                        45, 0, 180, 1)

        # Path precision
        self._add_spin(group, "path_precision", "Path Precision",
                        "Decimal places in SVG path coordinates. Higher = larger files.",
                        8, 0, 12, 1)

    def _add_spin(self, group, name, title, subtitle, default, min_v, max_v, step,
                  digits=0):
        row = Adw.SpinRow.new_with_range(min_v, max_v, step)
        row.set_title(title)
        row.set_subtitle(subtitle)
        row.set_digits(digits)
        row.set_value(default)
        row.connect("changed", lambda *a: self.emit("params-changed"))
        row.connect("notify::value", lambda *a: self.emit("params-changed"))
        group.add(row)
        self._param_widgets[name] = row

    # ── post-processing group ───────────────────────────────────────

    def _build_post_group(self):
        group = Adw.PreferencesGroup()
        group.set_title("Post-processing")
        group.set_description("Optional cleanup after conversion")
        self.add(group)

        opt = Adw.SwitchRow()
        opt.set_title("Optimize SVG")
        opt.set_subtitle("Run scour optimizer to reduce file size")
        opt.set_active(True)
        opt.connect("notify::active", lambda *a: self.emit("params-changed"))
        group.add(opt)
        self._param_widgets["_optimize"] = opt

    # ── helpers ─────────────────────────────────────────────────────

    def _set_combo_value(self, row: Adw.ComboRow, target: str):
        """Select the model entry whose string equals *target* (case-insensitive)."""
        model = row.get_model()
        if model is None:
            return
        n = model.get_n_items()
        for i in range(n):
            item = model.get_item(i)
            if item and item.get_string().lower() == target.lower():
                row.set_selected(i)
                return
        # fallback: select first
        if n > 0:
            row.set_selected(0)
