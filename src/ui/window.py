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
from ..core.settings import (
    RecentSearchesManager,
    SavedGamesManager,
    WindowStateManager,
    create_settings,
)
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
    results_content = Gtk.Template.Child()
    results_grid = Gtk.Template.Child()
    primary_menu_button = Gtk.Template.Child()
    saved_toggle_button = Gtk.Template.Child()
    recent_searches_box = Gtk.Template.Child()
    recent_searches_list = Gtk.Template.Child()

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)

        self.current_search_id = 0
        self._current_query = ""
        self._next_search_start = 0
        self._has_more_results = False
        self._is_loading_more = False
        self._loaded_app_ids: set[int] = set()
        self._all_results: list[GameSummary] = []
        self._showing_saved_games = False
        self._settings = create_settings()
        self._window_state = WindowStateManager(self._settings)
        self._recent_searches = RecentSearchesManager(self._settings)
        self._saved_games = SavedGamesManager(self._settings)

        self._configure_primary_menu()
        self._refresh_recent_searches()
        self._window_state.restore(self)
        self.main_stack.set_visible_child_name("empty")

        self.search_entry.connect("activate", self.on_search_activated)
        self.saved_toggle_button.connect("toggled", self._on_saved_toggle)
        self.recent_searches_list.connect("row-activated", self._on_recent_activated)
        self.results_scroll.connect("notify::width", self._on_results_width_changed)
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

    def _update_results_content_width(self) -> None:
        available_width = max(1, self.results_scroll.get_width() - 36)
        column_spacing = self.results_grid.get_column_spacing()
        max_columns = self.results_grid.get_max_children_per_line()
        columns = max(
            1,
            min(
                max_columns,
                (available_width + column_spacing) // (CARD_W + column_spacing),
            ),
        )
        content_width = (columns * CARD_W) + ((columns - 1) * column_spacing)
        self.results_content.set_size_request(content_width, -1)
        self.results_grid.set_size_request(content_width, -1)

    def _on_results_width_changed(self, *_args) -> None:
        self._update_results_content_width()

    def _on_close_request(self, *_args) -> bool:
        self._window_state.persist(self)
        return False

    def _is_stale_search(self, search_id: int) -> bool:
        return search_id != self.current_search_id

    def _clear_grid(self) -> None:
        child = self.results_grid.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.results_grid.remove(child)
            child = next_child

    def clear_results(self) -> None:
        self._loaded_app_ids.clear()
        self._clear_grid()

    def _insert_game_card(self, summary: GameSummary) -> None:
        card = GameCard(
            self,
            summary,
            is_saved=self._saved_games.is_saved(summary.app_id),
            saved_changed=self._on_saved_changed,
        )
        self.results_grid.insert(card, -1)

        flow_child = card.get_parent()
        if flow_child is not None:
            flow_child.add_css_class("game-flow-child")
            flow_child.set_size_request(CARD_W, -1)
            flow_child.set_halign(Gtk.Align.CENTER)
            flow_child.set_valign(Gtk.Align.START)

    def _render_summaries(self, summaries: list[GameSummary]) -> None:
        self._clear_grid()

        for summary in summaries:
            self._insert_game_card(summary)

    def _current_source_summaries(self) -> list[GameSummary]:
        if self._showing_saved_games:
            return self._saved_games.list()
        return self._all_results

    def _update_results_view(self) -> None:
        summaries = self._current_source_summaries()
        if not summaries:
            self._clear_grid()
            if self._showing_saved_games:
                self.main_stack.set_visible_child_name("saved-empty")
            elif self._current_query:
                self.main_stack.set_visible_child_name("no-results")
            else:
                self.main_stack.set_visible_child_name("empty")
            return

        self._render_summaries(summaries)
        has_visible_results = self.results_grid.get_first_child() is not None
        if has_visible_results:
            self.main_stack.set_visible_child_name("results")
        elif self._showing_saved_games:
            self.main_stack.set_visible_child_name("saved-empty")
        else:
            self.main_stack.set_visible_child_name("no-results")

    def _show_search_error(self, message: str, search_id: int) -> bool:
        if self._is_stale_search(search_id):
            return False

        self._is_loading_more = False
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

        self._all_results.extend(summaries)
        if not self._showing_saved_games:
            for summary in summaries:
                self._insert_game_card(summary)
            self.main_stack.set_visible_child_name("results")

        self._has_more_results = has_more_results
        self._is_loading_more = False
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
        if (
            self._showing_saved_games
            or not self._current_query
            or self._is_loading_more
            or not self._has_more_results
        ):
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

    def _on_saved_changed(self, summary: GameSummary, is_saved: bool) -> None:
        if is_saved:
            self._saved_games.save(summary)
        else:
            self._saved_games.remove(summary.app_id)

        if self._showing_saved_games and not is_saved:
            self._remove_game_card(summary.app_id)
            if self.results_grid.get_first_child() is None:
                self.main_stack.set_visible_child_name("saved-empty")

    def _remove_game_card(self, app_id: int) -> None:
        child = self.results_grid.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            card = child.get_child() if isinstance(child, Gtk.FlowBoxChild) else child
            if getattr(card, "app_id", None) == app_id:
                self.results_grid.remove(child)
                return
            child = next_child

    def _on_saved_toggle(self, button: Gtk.ToggleButton) -> None:
        self._showing_saved_games = button.get_active()
        if self._showing_saved_games:
            self.search_entry.set_sensitive(False)
        else:
            self.search_entry.set_sensitive(True)
        self._update_results_view()

    def _on_recent_activated(self, _listbox: Gtk.ListBox, row: Gtk.ListBoxRow) -> None:
        query = getattr(row, "query", "")
        if not query:
            return

        self.saved_toggle_button.set_active(False)
        self.search_entry.set_text(query)
        self.on_search_activated(self.search_entry)

    def _refresh_recent_searches(self) -> None:
        child = self.recent_searches_list.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            self.recent_searches_list.remove(child)
            child = next_child

        for query in self._recent_searches.list():
            row = Adw.ActionRow(title=query)
            row.query = query
            row.set_activatable(True)

            icon = Gtk.Image.new_from_icon_name("document-open-recent-symbolic")
            icon.add_css_class("dim-label")
            row.add_prefix(icon)

            self.recent_searches_list.append(row)

        self.recent_searches_box.set_visible(
            self.recent_searches_list.get_first_child() is not None
        )

    def on_search_activated(self, entry: Gtk.SearchEntry) -> None:
        self.current_search_id += 1
        search_id = self.current_search_id

        query = entry.get_text().strip()
        if not query:
            self._current_query = ""
            self._next_search_start = 0
            self._has_more_results = False
            self._is_loading_more = False
            self._all_results.clear()
            self.clear_results()
            self.main_stack.set_visible_child_name("empty")
            return

        self.saved_toggle_button.set_active(False)
        self._recent_searches.add(query)
        self._refresh_recent_searches()
        self._current_query = query
        self._next_search_start = 0
        self._has_more_results = False
        self._is_loading_more = True
        self._all_results.clear()
        self.clear_results()
        self.main_stack.set_visible_child_name("loading")
        start_daemon_thread(self._perform_search, query, search_id, 0)
