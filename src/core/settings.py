from __future__ import annotations

import json
import logging

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk

from .constants import APP_ID, MIN_WINDOW_HEIGHT, MIN_WINDOW_WIDTH
from .models import GameSummary


LOGGER = logging.getLogger(__name__)

MAX_RECENT_SEARCHES = 8


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


class RecentSearchesManager:
    def __init__(self, settings: Gio.Settings | None) -> None:
        self._settings = settings

    def list(self) -> list[str]:
        if self._settings is None:
            return []
        return list(self._settings.get_strv("recent-searches"))

    def add(self, query: str) -> None:
        if self._settings is None:
            return

        normalized = query.strip()
        if not normalized:
            return

        recent = [
            item for item in self.list() if item.casefold() != normalized.casefold()
        ]
        recent.insert(0, normalized)
        self._settings.set_strv("recent-searches", recent[:MAX_RECENT_SEARCHES])


class SavedGamesManager:
    def __init__(self, settings: Gio.Settings | None) -> None:
        self._settings = settings

    def list(self) -> list[GameSummary]:
        if self._settings is None:
            return []

        summaries: list[GameSummary] = []
        for item in self._settings.get_strv("saved-games"):
            try:
                data = json.loads(item)
                if isinstance(data, dict):
                    summary = GameSummary.from_settings_dict(data)
                    if summary.app_id:
                        summaries.append(summary)
            except (TypeError, ValueError) as error:
                LOGGER.warning("Ignoring invalid saved game setting: %s", error)
        return summaries

    def is_saved(self, app_id: int) -> bool:
        return any(summary.app_id == app_id for summary in self.list())

    def save(self, summary: GameSummary) -> None:
        if self._settings is None or not summary.app_id:
            return

        summaries = [item for item in self.list() if item.app_id != summary.app_id]
        summaries.insert(0, summary)
        self._settings.set_strv("saved-games", self._serialize(summaries))

    def remove(self, app_id: int) -> None:
        if self._settings is None:
            return

        summaries = [item for item in self.list() if item.app_id != app_id]
        self._settings.set_strv("saved-games", self._serialize(summaries))

    def _serialize(self, summaries: list[GameSummary]) -> list[str]:
        return [
            json.dumps(summary.to_settings_dict(), separators=(",", ":"))
            for summary in summaries
        ]
