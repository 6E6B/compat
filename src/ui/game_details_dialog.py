from __future__ import annotations

import logging
from gettext import gettext as _
from typing import Any

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, GLib, Gtk, Pango

from ..core.constants import DETAIL_HEADER_H, DETAIL_HEADER_W
from ..core.formatters import (
    format_list,
    format_named_list,
    format_platforms,
    format_price,
    html_to_text,
)
from ..services.image_loader import create_badge, set_picture_from_url, start_daemon_thread
from ..services.steam_service import get_game_details


LOGGER = logging.getLogger(__name__)


class GameDetailsDialog(Adw.Window):
    def __init__(
        self,
        parent: Gtk.Window,
        app_id: int,
        game_name: str,
        proton_tier: str,
    ) -> None:
        super().__init__(transient_for=parent)

        self.app_id = app_id
        self.game_name = game_name
        self.proton_tier = proton_tier
        self._closed = False

        self.set_modal(True)
        self.set_title(game_name)
        self.set_default_size(760, 720)
        self.set_size_request(560, 480)
        self.connect("close-request", self._on_close_request)

        toolbar = Adw.ToolbarView()

        header_bar = Adw.HeaderBar()
        title_widget = Adw.WindowTitle(title=game_name, subtitle=f"App ID: {app_id}")
        header_bar.set_title_widget(title_widget)
        toolbar.add_top_bar(header_bar)

        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        loading_page = Adw.StatusPage()
        loading_page.set_title(_("Loading game details…"))
        loading_page.set_description(_("Fetching Steam app info."))

        loading_spinner = Gtk.Spinner()
        loading_spinner.set_spinning(True)
        loading_spinner.set_size_request(40, 40)
        loading_spinner.set_halign(Gtk.Align.CENTER)
        loading_page.set_child(loading_spinner)

        self.stack.add_named(loading_page, "loading")

        self.error_page = Adw.StatusPage()
        self.error_page.set_icon_name("dialog-error-symbolic")
        self.error_page.set_title(_("Could not load game details"))
        self.error_page.set_description(_("The Steam details request failed."))
        self.stack.add_named(self.error_page, "error")

        self.content_scroll = Gtk.ScrolledWindow()
        self.content_scroll.set_vexpand(True)
        self.content_scroll.set_hexpand(True)
        self.stack.add_named(self.content_scroll, "content")

        self.stack.set_visible_child_name("loading")
        toolbar.set_content(self.stack)
        self.set_content(toolbar)

        start_daemon_thread(self._load_details)

    def _on_close_request(self, *_args) -> bool:
        self._closed = True
        return False

    def _build_heading(self, text: str, css_class: str = "title-4") -> Gtk.Label:
        heading = Gtk.Label(xalign=0)
        heading.set_markup(f"<b>{GLib.markup_escape_text(text)}</b>")
        heading.add_css_class(css_class)
        return heading

    def _build_body_label(self, text: str, selectable: bool = False) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0)
        label.set_wrap(True)
        label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)
        label.set_selectable(selectable)
        return label

    def _build_info_row(self, title: str, value: str) -> Gtk.Box:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        box.add_css_class("detail-block")

        heading = self._build_heading(title, css_class="caption-heading")
        content = self._build_body_label(value or _("Unknown"), selectable=False)

        box.append(heading)
        box.append(content)
        return box

    def _build_content(self, data: dict[str, Any]) -> Gtk.Box:
        outer = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=18,
            margin_top=18,
            margin_bottom=18,
            margin_start=18,
            margin_end=18,
        )

        hero_picture = Gtk.Picture()
        hero_picture.add_css_class("detail-hero")
        hero_picture.set_size_request(DETAIL_HEADER_W, DETAIL_HEADER_H)
        hero_picture.set_content_fit(Gtk.ContentFit.COVER)
        hero_picture.set_halign(Gtk.Align.CENTER)
        hero_picture.set_can_shrink(False)

        header_image = data.get("header_image")
        if header_image:
            start_daemon_thread(set_picture_from_url, header_image, hero_picture)

        outer.append(hero_picture)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)

        title = Gtk.Label(xalign=0)
        title.set_markup(
            "<span size='x-large' weight='bold'>"
            f"{GLib.markup_escape_text(data.get('name', self.game_name))}"
            "</span>"
        )
        title.set_wrap(True)

        badge = Gtk.Label()
        badge.set_halign(Gtk.Align.START)
        badge.set_xalign(0.0)
        create_badge(badge, self.proton_tier)

        title_box.append(title)
        title_box.append(badge)
        outer.append(title_box)

        summary = data.get("short_description") or html_to_text(
            data.get("about_the_game")
        )
        if summary:
            outer.append(self._build_body_label(summary, selectable=False))

        info_grid = Gtk.Grid(column_spacing=24, row_spacing=16)
        info_grid.set_column_homogeneous(True)

        release_date = data.get("release_date", {}).get("date", _("Unknown"))
        developers = format_list(data.get("developers"))
        publishers = format_list(data.get("publishers"))
        price = format_price(data.get("price_overview"), data.get("is_free", False))
        platforms = format_platforms(data.get("platforms"))
        genres = format_named_list(data.get("genres"))
        categories = format_named_list(data.get("categories"))
        languages = html_to_text(data.get("supported_languages")) or _("Unknown")
        metacritic = str(data.get("metacritic", {}).get("score", _("N/A")))
        recommendations = str(data.get("recommendations", {}).get("total", _("N/A")))

        rows = [
            (_("Release date"), release_date),
            (_("Developers"), developers),
            (_("Publishers"), publishers),
            (_("Price"), price),
            (_("Platforms"), platforms),
            (_("Genres"), genres),
            (_("Categories"), categories),
            (_("Languages"), languages),
            (_("Metacritic"), metacritic),
            (_("Recommendations"), recommendations),
        ]

        for index, (label, value) in enumerate(rows):
            info_grid.attach(
                self._build_info_row(label, value),
                index % 2,
                index // 2,
                1,
                1,
            )

        outer.append(info_grid)

        about_text = html_to_text(
            data.get("about_the_game") or data.get("detailed_description")
        )
        if about_text:
            outer.append(self._build_heading(_("About")))
            outer.append(self._build_body_label(about_text))

        minimum_pc = html_to_text(data.get("pc_requirements", {}).get("minimum"))
        if minimum_pc:
            outer.append(self._build_heading(_("Minimum PC requirements")))
            outer.append(self._build_body_label(minimum_pc))

        website = data.get("website")
        if website:
            outer.append(self._build_heading(_("Website")))
            link_button = Gtk.LinkButton(uri=website, label=website)
            link_button.set_halign(Gtk.Align.START)
            outer.append(link_button)

        return outer

    def _load_details(self) -> None:
        try:
            data = get_game_details(self.app_id)
            GLib.idle_add(self._show_content, data)
        except Exception as error:
            LOGGER.error("Game details error for %s: %s", self.app_id, error)
            GLib.idle_add(
                self._show_error,
                _("The game details could not be loaded. Please try again later."),
            )

    def _show_content(self, data: dict[str, Any]) -> bool:
        if self._closed:
            return False

        content = self._build_content(data)
        self.content_scroll.set_child(content)
        self.stack.set_visible_child_name("content")
        GLib.idle_add(self._scroll_content_to_top)
        return False

    def _scroll_content_to_top(self) -> bool:
        adjustment = self.content_scroll.get_vadjustment()
        adjustment.set_value(adjustment.get_lower())
        return False

    def _show_error(self, error_text: str) -> bool:
        if self._closed:
            return False

        self.error_page.set_description(error_text or _("Unknown error."))
        self.stack.set_visible_child_name("error")
        return False
