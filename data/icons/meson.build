icon_source_id = application_id

symbolic_dir = 'hicolor' / 'symbolic' / 'apps'
install_data(
  symbolic_dir / ('@0@-symbolic.svg').format(icon_source_id),
  rename: '@0@-symbolic.svg'.format(application_id),
  install_dir: get_option('datadir') / 'icons' / symbolic_dir
)

scalable_dir = 'hicolor' / 'scalable' / 'apps'
install_data(
  scalable_dir / ('@0@.svg').format(icon_source_id),
  rename: '@0@.svg'.format(application_id),
  install_dir: get_option('datadir') / 'icons' / scalable_dir
)

png_dir = 'hicolor' / '512x512' / 'apps'
png_icon = png_dir / ('@0@.png').format(icon_source_id)
install_data(
  png_icon,
  rename: '@0@.png'.format(application_id),
  install_dir: get_option('datadir') / 'icons' / png_dir
)

install_data(
  png_icon,
  rename: '@0@.png'.format(application_id),
  install_dir: get_option('datadir') / 'pixmaps'
)
