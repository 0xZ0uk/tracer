# SPDX-License-Identifier: MIT

"""VTracer integration — wraps the vtracer Python bindings and handles threading."""

import threading
import os
from pathlib import Path

from gi.repository import GLib

__all__ = ["Converter", "ConversionResult"]


class ConversionResult:
    """Result of a single conversion."""

    def __init__(self, success: bool, input_path: str, output_path: str = "", error: str = ""):
        self.success = success
        self.input_path = input_path
        self.output_path = output_path
        self.error = error


class Converter:
    """Wraps vtracer.convert_image_to_svg_py with async callbacks and parameter management."""

    # Valid parameter ranges
    PARAM_RANGES = {
        "color_precision": (1, 8, 1),
        "corner_threshold": (0.0, 180.0, 0.5),
        "filter_speckle": (0, 200, 1),
        "layer_difference": (0, 255, 1),
        "length_threshold": (0.0, 50.0, 0.1),
        "splice_threshold": (0.0, 180.0, 0.5),
        "path_precision": (0, 12, 1),
    }

    VALID_COLORMODES = ["color", "bw"]
    VALID_MODES = ["pixel", "polygon", "spline"]
    VALID_HIERARCHICAL = ["stacked", "cutout"]

    # Params that vtracer expects as int (Adw.SpinRow returns float)
    # Only length_threshold is float per vtracer's pyi stubs
    INT_PARAMS = {"color_precision", "filter_speckle", "layer_difference",
                  "corner_threshold", "max_iterations", "splice_threshold",
                  "path_precision"}

    PRESETS = {
        "custom": {},
        "bw": {
            "colormode": "bw",
            "mode": "polygon",
            "filter_speckle": 4,
            "color_precision": 6,
            "corner_threshold": 60,
            "hierarchical": "cutout",
        },
        "poster": {
            "colormode": "color",
            "mode": "polygon",
            "filter_speckle": 6,
            "color_precision": 3,
            "corner_threshold": 40,
            "hierarchical": "stacked",
            "layer_difference": 15,
        },
        "photo": {
            "colormode": "color",
            "mode": "spline",
            "filter_speckle": 4,
            "color_precision": 6,
            "corner_threshold": 60,
            "hierarchical": "stacked",
        },
    }

    def __init__(self):
        self._params = self._default_params()
        self._conversion_thread = None
        self._cancelled = False

    def _default_params(self) -> dict:
        return {
            "colormode": "color",
            "hierarchical": "stacked",
            "mode": "spline",
            "filter_speckle": 4,
            "color_precision": 6,
            "layer_difference": 0,
            "corner_threshold": 60,
            "length_threshold": 3.5,
            "max_iterations": None,
            "splice_threshold": 45,
            "path_precision": 8,
        }

    def set_params(self, **kwargs):
        """Update conversion parameters."""
        self._params.update(kwargs)

    def get_params(self) -> dict:
        """Return current parameters dict (copy)."""
        return dict(self._params)

    def get_param(self, key: str):
        return self._params.get(key)

    def apply_preset(self, preset_name: str):
        """Apply a named preset. 'custom' resets to defaults."""
        if preset_name == "custom":
            self._params = self._default_params()
        elif preset_name in self.PRESETS:
            self._params.update(self.PRESETS[preset_name])

    # --- Sync conversion (for batch/simple use) ---

    def convert_sync(self, input_path: str, output_path: str, **overrides) -> ConversionResult:
        """Run conversion synchronously in the calling thread."""
        import vtracer

        params = dict(self._params)
        params.update(overrides)
        # Strip None values so vtracer uses its defaults
        clean = {k: v for k, v in params.items() if v is not None}
        # Coerce types: SpinRow returns float, but vtracer expects int for some params
        for k, v in clean.items():
            if k in self.INT_PARAMS and v is not None:
                clean[k] = int(v)

        try:
            vtracer.convert_image_to_svg_py(
                image_path=input_path,
                out_path=output_path,
                **clean,
            )
            return ConversionResult(
                success=True,
                input_path=input_path,
                output_path=output_path,
            )
        except Exception as e:
            return ConversionResult(
                success=False,
                input_path=input_path,
                output_path=output_path,
                error=str(e),
            )

    # --- Async conversion (for single-image with UI callback) ---

    def convert_async(self, input_path: str, output_path: str,
                      on_done=None, **overrides):
        """Run conversion in a background thread. Calls ``on_done(result)`` on the main thread."""
        self._cancelled = False
        params = dict(self._params)
        params.update(overrides)

        def _run():
            result = self.convert_sync(input_path, output_path, **params)
            if self._cancelled:
                return
            GLib.idle_add(lambda: on_done(result) if on_done else None, priority=GLib.PRIORITY_DEFAULT)

        self._conversion_thread = threading.Thread(target=_run, daemon=True)
        self._conversion_thread.start()

    def cancel(self):
        """Cancel the current conversion (marks the next callback as no-op)."""
        self._cancelled = True

    def is_running(self) -> bool:
        return self._conversion_thread is not None and self._conversion_thread.is_alive()

    # --- Helpers ---

    @staticmethod
    def supported_input_extensions() -> list:
        return [".png", ".jpg", ".jpeg", ".webp", ".tiff", ".tif", ".bmp"]

    @staticmethod
    def is_supported_image(path: str) -> bool:
        ext = Path(path).suffix.lower()
        return ext in Converter.supported_input_extensions()

    @staticmethod
    def suggest_output_path(input_path: str, output_dir: str = "") -> str:
        """Generate an .svg output path from an input image path."""
        inp = Path(input_path)
        if output_dir:
            return str(Path(output_dir) / f"{inp.stem}.svg")
        return str(inp.with_suffix(".svg"))
