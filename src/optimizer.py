# SPDX-License-Identifier: MIT

"""SVG optimization using scour — post-processing step after vtracer conversion."""

from scour.scour import scourString, generateDefaultOptions

__all__ = ["optimize_svg_file", "OptimizerOptions"]


class OptimizerOptions:
    """Aggressive but safe SVG optimization settings."""

    def __init__(self):
        opt = generateDefaultOptions()
        # Remove editor metadata (Inkscape, Adobe, etc.)
        opt.remove_descriptive_elements = True
        opt.strip_comments = True
        # Join styles inline, remove default attr values
        opt.style_to_xml = True
        opt.simple_colors = True
        # Collapse empty <g> groups, remove unused defs
        opt.group_collapse = True
        opt.keep_defs = False
        # Shorten IDs (a, b, c...)
        opt.shorten_ids = True
        # Coordinate precision (fewer decimal places = smaller files)
        opt.digits = 4
        # Strip XML prolog? vtracer output doesn't have one, but just in case
        opt.strip_xml_prolog = False
        # Don't embed rasters (we're converting FROM rasters)
        opt.embed_rasters = False
        # Protect nothing — we want everything optimized
        opt.protect_ids_list = None
        opt.protect_ids_noninkscape = False
        # Minimal formatting
        opt.newlines = True
        opt.indent_depth = 0
        opt.indent_type = "space"
        # Don't strip IDs that are referenced
        opt.strip_ids = False
        self._opt = opt

    def to_scour_options(self):
        return self._opt


def optimize_svg_file(input_path: str, output_path: str | None = None,
                      options: OptimizerOptions | None = None) -> tuple[bool, str]:
    """Optimize an SVG file in-place (or to a different output path).

    Returns (success, message).
    """
    if options is None:
        options = OptimizerOptions()

    try:
        with open(input_path, "r", encoding="utf-8") as f:
            original = f.read()
    except OSError as e:
        return False, f"Failed to read SVG: {e}"

    original_size = len(original)

    try:
        optimized = scourString(original, options.to_scour_options())
    except Exception as e:
        return False, f"Optimization failed: {e}"

    optimized_size = len(optimized)
    target = output_path or input_path

    try:
        with open(target, "w", encoding="utf-8") as f:
            f.write(optimized)
    except OSError as e:
        return False, f"Failed to write optimized SVG: {e}"

    savings = (1 - optimized_size / original_size) * 100 if original_size > 0 else 0
    return True, f"Optimized: {original_size:,} → {optimized_size:,} bytes  ({savings:.0f}% savings)"
