project('vtracer-gtk',
  version: '0.1.0',
  meson_version: '>= 0.63.0',
  license: 'MIT',
)

gnome = import('gnome')
python = import('python')

pkgdatadir = join_paths(get_option('prefix'), get_option('datadir'), meson.project_name())
moduledir = join_paths(pkgdatadir, 'src')

# Install all Python source files (including __init__.py)
install_subdir('src',
  install_dir: pkgdatadir,
  exclude_files: ['main.py.in'],
)

# Process main.py.in → /app/bin/vtracer-gtk
conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', join_paths(get_option('prefix'), get_option('localedir')))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'src/main.py.in',
  output: 'vtracer-gtk',
  configuration: conf,
  install_dir: get_option('bindir'),
)

# Desktop file
install_data(
  'data/com.github.z0uk.vtracer-gtk.desktop.in',
  install_dir: join_paths(get_option('datadir'), 'applications'),
  rename: ['com.github.z0uk.vtracer-gtk.desktop'],
)

desktop_utils = find_program('desktop-file-validate', required: false)
if desktop_utils.found()
  test('Validate desktop file', desktop_utils,
    args: [join_paths(meson.current_source_dir(), 'data', 'com.github.z0uk.vtracer-gtk.desktop.in')],
  )
endif

# AppStream metadata
install_data(
  'data/com.github.z0uk.vtracer-gtk.metainfo.xml',
  install_dir: join_paths(get_option('datadir'), 'metainfo'),
)

appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('Validate AppStream file', appstreamcli,
    args: ['validate', '--no-net', '--explain',
           join_paths(meson.current_source_dir(), 'data', 'com.github.z0uk.vtracer-gtk.metainfo.xml')],
  )
endif

# GSettings schema
install_data(
  'data/com.github.z0uk.vtracer-gtk.gschema.xml',
  install_dir: join_paths(get_option('datadir'), 'glib-2.0', 'schemas'),
)

compile_schemas = find_program('glib-compile-schemas', required: false)
if compile_schemas.found()
  test('Validate schema file', compile_schemas,
    args: ['--strict', meson.current_source_dir()],
  )
endif

# Icon
install_data(
  'data/icons/com.github.z0uk.vtracer-gtk.svg',
  install_dir: join_paths(get_option('datadir'), 'icons', 'hicolor', 'scalable', 'apps'),
)

gnome.post_install(
  glib_compile_schemas: true,
  gtk_update_icon_cache: true,
  update_desktop_database: true,
)
