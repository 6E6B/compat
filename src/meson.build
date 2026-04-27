pkgdatadir = get_option('prefix') / get_option('datadir') / meson.project_name()
moduledir = pkgdatadir / 'compat'
gnome = import('gnome')

gnome.compile_resources('compat',
  'compat.gresource.xml',
  gresource_bundle: true,
  install: true,
  install_dir: pkgdatadir,
)

python = import('python')

conf = configuration_data()
conf.set('PYTHON', python.find_installation('python3').full_path())
conf.set('VERSION', meson.project_version())
conf.set('localedir', get_option('prefix') / get_option('localedir'))
conf.set('pkgdatadir', pkgdatadir)

configure_file(
  input: 'compat.in',
  output: 'compat',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x'
)

compat_sources = [
  'main.py',
]

install_data(compat_sources, install_dir: moduledir)
install_subdir('core', install_dir: moduledir, exclude_directories: ['__pycache__'])
install_subdir('services', install_dir: moduledir, exclude_directories: ['__pycache__'])
install_subdir('ui', install_dir: moduledir, exclude_directories: ['__pycache__'])
