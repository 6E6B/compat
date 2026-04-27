import logging
import os
import sys
from gettext import gettext as _

import gi

gi.require_version('Gtk', '4.0')
gi.require_version('Adw', '1')

from gi.repository import Adw, Gdk, Gio, GLib, Gtk

from .core.constants import APP_ID
from .ui.window import CompatWindow


LOGGER = logging.getLogger(__name__)

class CompatApplication(Adw.Application):
    def __init__(self, version):
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.DEFAULT_FLAGS,
            resource_base_path='/io/github/_6e6b/compat'
        )
        self.version = version
        self._css_loaded = False

        self.create_action('about', self.on_about_action)
        self.create_action('quit', self.on_quit_action, ['<primary>q'])
        self.create_action('shortcuts', self.on_shortcuts_action, ['<primary>question'])

    def do_startup(self):
        Adw.Application.do_startup(self)
        self.load_css()

    def load_css(self):
        if self._css_loaded:
            return

        display = Gdk.Display.get_default()
        if display is None:
            LOGGER.warning('No display available; skipping CSS loading.')
            return

        provider = Gtk.CssProvider()
        provider.load_from_resource('/io/github/_6e6b/compat/style.css')
        Gtk.StyleContext.add_provider_for_display(
            display,
            provider,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
        )
        self._css_loaded = True

    def do_activate(self):
        win = self.props.active_window
        if not win:
            win = CompatWindow(application=self)
        win.present()

    def on_about_action(self, *args):
        about = Adw.AboutDialog(
            application_name='Compat',
            application_icon=APP_ID,
            developer_name='Compat contributors',
            version=self.version,
            developers=['Compat contributors'],
            copyright='© 2026 Compat contributors',
        )
        about.set_translator_credits(_('translator-credits'))
        about.present(self.props.active_window)

    def on_quit_action(self, *_args):
        self.quit()

    def on_shortcuts_action(self, *_args):
        window = self.props.active_window
        if window is None:
            return

        try:
            builder = Gtk.Builder.new_from_resource('/io/github/_6e6b/compat/shortcuts-dialog.ui')
            shortcuts_window = builder.get_object('shortcuts_dialog')
        except GLib.Error as error:
            LOGGER.exception('Failed to load shortcuts window: %s', error)
            return

        if shortcuts_window is None:
            LOGGER.error('Shortcuts window was not found in the UI resource.')
            return

        shortcuts_window.set_transient_for(window)
        shortcuts_window.present()

    def create_action(self, name, callback, shortcuts=None):
        """Add an application action.

        Args:
            name: the name of the action
            callback: the function to be called when the action is
              activated
            shortcuts: an optional list of accelerators
        """
        action = Gio.SimpleAction.new(name, None)
        action.connect("activate", callback)
        self.add_action(action)
        if shortcuts:
            self.set_accels_for_action(f"app.{name}", shortcuts)


def main(version):
    """The application's entry point."""
    log_level_name = os.environ.get('COMPAT_LOG_LEVEL', 'WARNING').upper()
    log_level = getattr(logging, log_level_name, logging.WARNING)
    logging.basicConfig(
        level=log_level,
        format='%(name)s: %(levelname)s: %(message)s',
    )

    app = CompatApplication(version)
    return app.run(sys.argv)
