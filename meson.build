project('compat',
          version: '0.1.0',
    meson_version: '>= 1.0.0',
  default_options: [ 'warning_level=2', 'werror=false', ],
)

application_id = 'io.github._6e6b.compat'
resource_path = '/io/github/_6e6b/compat'

i18n = import('i18n')
gnome = import('gnome')




subdir('data')
subdir('src')
subdir('po')
subdir('tests')

gnome.post_install(
     glib_compile_schemas: true,
    gtk_update_icon_cache: true,
  update_desktop_database: true,
)
