from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gio, GLib, Gtk

from ..core.constants import CARD_W, MAX_TIER_WORKERS, SEARCH_PAGE_SIZE
from ..core.models import GameSummary
from ..core.settings import WindowStateManager, create_settings
from ..services.image_loader import start_daemon_thread
from ..services.steam_service import build_game_summary, search_steam_games_page
from .game_card import GameCard


LOGGER = logging.getLogger(__name__)


@Gtk.Template(resource_path="/io/github/_6e6b/compat/window.ui")
class CompatWindow(Adw.ApplicationWindow):
    __gtype_name__ = "CompatWindow"

    search_entry = Gtk.Template.Child()
    main_stack = Gtk.Template.Child()
    search_error_page = Gtk.Template.Child()
    results_scroll = Gtk.Template.Child()
    results_grid = Gtk.Template.Child()
    primary_menu_button = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.current_search_id = 0
        self._current_query = ""
        self._next_search_start = 0
        self._has_more_results = False
        self._is_loading_more = False
        self._loaded_app_ids: set[int] = set()
        self._window_state = WindowStateManager(create_settings())

        self._configure_primary_menu()
        self._window_state.restore(self)
        self.main_stack.set_visible_child_name("empty")

        self.search_entry.connect("activate", self.on_search_activated)
        self.results_scroll.get_vadjustment().connect(
            "value-changed",
            self._on_results_scroll,
        )
        self.connect("close-request", self._on_close_request)

    def _configure_primary_menu(self) -> None:
        menu = Gio.Menu()
        menu.append(_("Keyboard Shortcuts"), "app.shortcuts")
        menu.append(_("About Compat"), "app.about")
        menu.append(_("Quit"), "app.quit")
        self.primary_menu_button.set_menu_model(menu)

    def _on_close_request(self, *_args) -> bool:
        self._window_state.persist(self)
        return False

    def _is_stale_search(self, search_id: int) -> bool:
        return search_id != self.current_search_id

    def clear_results(self) -> None:
        self._loaded_app_ids.clear()
        child = self.results_grid.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.results_grid.remove(child)
            child = next_child

    def _insert_game_card(self, summary: GameSummary) -> None:
        card = GameCard(self, summary)
        self.results_grid.insert(card, -1)

        flow_child = card.get_parent()
        if flow_child is not None:
            flow_child.add_css_class("game-flow-child")
            flow_child.set_size_request(CARD_W, -1)
            flow_child.set_halign(Gtk.Align.CENTER)
            flow_child.set_valign(Gtk.Align.START)

    def _show_search_error(self, message: str, search_id: int) -> bool:
        if self._is_stale_search(search_id):
            return False

        self.search_error_page.set_description(message)
        self.main_stack.set_visible_child_name("error")
        return False

    def _show_search_results(
        self,
        summaries: list[GameSummary],
        search_id: int,
        has_more_results: bool,
    ) -> bool:
        if self._is_stale_search(search_id):
            return False

        for summary in summaries:
            self._insert_game_card(summary)

        self._has_more_results = has_more_results
        self._is_loading_more = False
        self.main_stack.set_visible_child_name("results")
        return False

    def _show_search_state(self, state_name: str, search_id: int) -> bool:
        if self._is_stale_search(search_id):
            return False

        self._is_loading_more = False
        self.main_stack.set_visible_child_name(state_name)
        return False

    def _perform_search(self, query: str, search_id: int, start: int) -> None:
        try:
            games, total_count = search_steam_games_page(
                query,
                start=start,
                count=SEARCH_PAGE_SIZE,
            )
        except Exception as error:
            LOGGER.error("Steam search error for %r: %s", query, error)
            self._is_loading_more = False
            GLib.idle_add(
                self._show_search_error,
                _("Search failed. Please check your connection and try again."),
                search_id,
            )
            return

        if self._is_stale_search(search_id):
            return

        self._next_search_start = start + SEARCH_PAGE_SIZE
        has_more_results = self._next_search_start < total_count

        if not games:
            if start == 0:
                GLib.idle_add(self._show_search_state, "no-results", search_id)
            else:
                self._has_more_results = False
                self._is_loading_more = False
            return

        unique_games = []
        for game in games:
            try:
                app_id = int(game.get("id") or 0)
            except (TypeError, ValueError):
                app_id = 0
            if app_id and app_id in self._loaded_app_ids:
                continue
            if app_id:
                self._loaded_app_ids.add(app_id)
            unique_games.append(game)

        if not unique_games:
            self._has_more_results = has_more_results
            self._is_loading_more = False
            return

        with ThreadPoolExecutor(max_workers=MAX_TIER_WORKERS) as executor:
            summaries = list(executor.map(build_game_summary, unique_games))

        if self._is_stale_search(search_id):
            return

        if not summaries:
            if start == 0:
                GLib.idle_add(self._show_search_state, "no-results", search_id)
            else:
                self._has_more_results = False
                self._is_loading_more = False
            return

        GLib.idle_add(
            self._show_search_results,
            summaries,
            search_id,
            has_more_results,
        )

    def _load_next_search_page(self) -> None:
        if not self._current_query or self._is_loading_more or not self._has_more_results:
            return

        self._is_loading_more = True
        start_daemon_thread(
            self._perform_search,
            self._current_query,
            self.current_search_id,
            self._next_search_start,
        )

    def _on_results_scroll(self, adjustment: Gtk.Adjustment) -> None:
        distance_to_bottom = (
            adjustment.get_upper()
            - adjustment.get_page_size()
            - adjustment.get_value()
        )
        if distance_to_bottom <= 300:
            self._load_next_search_page()

    def on_search_activated(self, entry: Gtk.SearchEntry) -> None:
        self.current_search_id += 1
        search_id = self.current_search_id

        query = entry.get_text().strip()
        if not query:
            self._current_query = ""
            self._next_search_start = 0
            self._has_more_results = False
            self._is_loading_more = False
            self.clear_results()
            self.main_stack.set_visible_child_name("empty")
            return

        self._current_query = query
        self._next_search_start = 0
        self._has_more_results = False
        self._is_loading_more = True
        self.clear_results()
        self.main_stack.set_visible_child_name("loading")
        start_daemon_thread(self._perform_search, query, search_id, 0)
