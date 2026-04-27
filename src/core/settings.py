from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk

from .constants import APP_ID, MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH


def create_settings() -> Gio.Settings | None:
    schema_source = Gio.SettingsSchemaSource.get_default()
    if schema_source is None:
        return None

    schema = schema_source.lookup(APP_ID, True)
    if schema is None:
        return None

    return Gio.Settings.new_full(schema, None, None)


class WindowStateManager:
    def __init__(self, settings: Gio.Settings | None) -> None:
        self._settings = settings

    def restore(self, window: Gtk.Window) -> None:
        if self._settings is None:
            return

        width = max(self._settings.get_int("window-width"), MIN_WINDOW_WIDTH)
        height = max(self._settings.get_int("window-height"), MIN_WINDOW_HEIGHT)
        window.set_default_size(width, height)

        if self._settings.get_boolean("window-maximized"):
            window.maximize()

    def persist(self, window: Gtk.Window) -> None:
        if self._settings is None:
            return

        self._settings.set_int("window-width", max(window.get_width(), MIN_WINDOW_WIDTH))
        self._settings.set_int(
            "window-height", max(window.get_height(), MIN_WINDOW_HEIGHT)
        )
        self._settings.set_boolean("window-maximized", window.is_maximized())
