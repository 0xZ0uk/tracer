# vtracer-gtk

A modern GTK4 + libadwaita GUI for [VTracer](https://github.com/visioncortex/vtracer) — convert raster images (PNG, JPG) to vector SVG graphics.

![screenshot](data/icons/com.github.z0uk.vtracer-gtk.svg)

## Features

- **Single image conversion** — open PNG/JPG, tweak settings, export SVG
- **Batch mode** — process entire folders with one click
- **All VTracer parameters** — full control over color mode, corner threshold, filtering, curves, presets
- **Presets** — built-in `bw`, `poster`, `photo` presets
- **Drag & drop** — drop images directly onto the window
- **Before/after preview** — compare original and vectorized result

## Building

### Flatpak (recommended)

```sh
flatpak install org.gnome.Platform//47 org.gnome.Sdk//47
cd vtracer-gtk
flatpak-builder build flatpak/com.github.z0uk.vtracer-gtk.yml --install
```

### Local

```sh
pip install vtracer
python3 src/main.py
```

## Dependencies

- Python 3.10+
- GTK 4 (with PyGObject)
- libadwaita (>= 1.4)
- VTracer Python bindings (`pip install vtracer`)
- librsvg (for SVG preview rendering)
