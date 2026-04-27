from __future__ import annotations

from collections.abc import Callable
from gettext import gettext as _

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Pango

from ..core.constants import CARD_TITLE_CHARS, CARD_W, THUMB_H, THUMB_W
from ..core.formatters import normalize_tier
from ..core.models import GameSummary
from ..services.image_loader import (
    create_badge,
    fetch_and_set_game_image,
    start_daemon_thread,
)
from .game_details_dialog import GameDetailsDialog


class GameCard(Gtk.Overlay):
    def __init__(
        self,
        parent_window: Gtk.Window,
        summary: GameSummary,
        is_saved: bool = False,
        saved_changed: Callable[[GameSummary, bool], None] | None = None,
    ) -> None:
        super().__init__()

        self.parent_window = parent_window
        self.summary = summary
        self.app_id = summary.app_id
        self.game_name = summary.name
        self.tier = summary.tier
        self._saved_changed = saved_changed

        self.add_css_class("card")
        self.add_css_class("game-card")
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.START)
        self.set_size_request(CARD_W, -1)
        self.set_tooltip_text(f"{summary.name} — {normalize_tier(summary.tier)}")

        button = Gtk.Button()
        button.add_css_class("flat")
        button.add_css_class("game-card-button")
        button.set_size_request(CARD_W, -1)
        button.set_can_focus(True)

        content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        content.set_size_request(CARD_W, -1)
        content.set_halign(Gtk.Align.FILL)

        self.cover_stack = Gtk.Stack()
        self.cover_stack.set_size_request(THUMB_W, THUMB_H)
        self.cover_stack.set_hhomogeneous(True)
        self.cover_stack.set_vhomogeneous(True)
        self.cover_stack.set_halign(Gtk.Align.FILL)
        self.cover_stack.set_valign(Gtk.Align.START)
        self.cover_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)

        placeholder = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        placeholder.add_css_class("game-cover")
        placeholder.add_css_class("game-cover-placeholder")
        placeholder.set_size_request(THUMB_W, THUMB_H)
        placeholder.set_hexpand(True)
        placeholder.set_vexpand(True)
        placeholder.set_halign(Gtk.Align.FILL)
        placeholder.set_valign(Gtk.Align.START)

        top_spacer = Gtk.Box()
        top_spacer.set_vexpand(True)

        placeholder_icon = Gtk.Image.new_from_icon_name("image-missing-symbolic")
        placeholder_icon.set_pixel_size(72)
        placeholder_icon.add_css_class("game-cover-placeholder-icon")
        placeholder_icon.set_halign(Gtk.Align.CENTER)
        placeholder_icon.set_valign(Gtk.Align.CENTER)

        bottom_spacer = Gtk.Box()
        bottom_spacer.set_vexpand(True)

        placeholder.append(top_spacer)
        placeholder.append(placeholder_icon)
        placeholder.append(bottom_spacer)

        self.picture = Gtk.Picture()
        self.picture.add_css_class("game-cover")
        self.picture.set_size_request(THUMB_W, THUMB_H)
        self.picture.set_can_shrink(False)
        self.picture.set_content_fit(Gtk.ContentFit.COVER)
        self.picture.set_hexpand(True)
        self.picture.set_vexpand(True)
        self.picture.set_halign(Gtk.Align.FILL)
        self.picture.set_valign(Gtk.Align.START)

        self.cover_stack.add_named(placeholder, "placeholder")
        self.cover_stack.add_named(self.picture, "image")
        self.cover_stack.set_visible_child_name("placeholder")
        self.cover_stack.set_overflow(Gtk.Overflow.HIDDEN)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        body.set_margin_top(10)
        body.set_margin_bottom(10)
        body.set_margin_start(10)
        body.set_margin_end(10)

        title = Gtk.Label(label=summary.name)
        title.set_halign(Gtk.Align.START)
        title.set_xalign(0.0)
        title.set_single_line_mode(True)
        title.set_wrap(False)
        title.set_width_chars(CARD_TITLE_CHARS)
        title.set_max_width_chars(CARD_TITLE_CHARS)
        title.set_ellipsize(Pango.EllipsizeMode.END)
        title.add_css_class("title-4")

        badge_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        badge_row.set_hexpand(True)

        badge = Gtk.Label()
        badge.set_halign(Gtk.Align.START)
        badge.set_xalign(0.0)
        create_badge(badge, summary.tier)
        badge_row.append(badge)

        pills_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        pills_row.set_halign(Gtk.Align.END)
        pills_row.set_hexpand(True)

        price_pill = Gtk.Label(label=summary.price)
        price_pill.add_css_class("card-pill")
        price_pill.add_css_class("price-pill")
        if summary.is_free:
            price_pill.add_css_class("free")
        pills_row.append(price_pill)

        if summary.proton_reports > 0:
            pills_row.append(self._build_reports_pill(summary.proton_reports))

        badge_row.append(pills_row)

        body.append(title)
        body.append(badge_row)

        content.append(self.cover_stack)
        content.append(body)

        button.set_child(content)
        button.connect("clicked", self._on_clicked)
        self.set_child(button)

        self.saved_button = Gtk.ToggleButton()
        self.saved_button.add_css_class("flat")
        self.saved_button.add_css_class("circular")
        self.saved_button.add_css_class("favorite-button")
        self.saved_button.set_icon_name("non-starred-symbolic")
        self.saved_button.set_tooltip_text(_("Save game"))
        self.saved_button.set_halign(Gtk.Align.END)
        self.saved_button.set_valign(Gtk.Align.START)
        self.saved_button.set_margin_top(8)
        self.saved_button.set_margin_end(8)
        self.saved_button.set_active(is_saved)
        self.saved_button.connect("toggled", self._on_saved_toggled)
        self.add_overlay(self.saved_button)
        self._sync_saved_button()

        if summary.app_id:
            start_daemon_thread(
                fetch_and_set_game_image,
                summary.app_id,
                self.picture,
                self.cover_stack,
            )

    def _build_reports_pill(self, report_count: int) -> Gtk.Box:
        reports_pill = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=4)
        reports_pill.add_css_class("card-pill")
        reports_pill.add_css_class("reports-pill")
        reports_pill.set_tooltip_text(
            _("{count} ProtonDB reports").format(count=report_count)
        )

        reports_icon = Gtk.Image.new_from_icon_name("view-list-symbolic")
        reports_icon.set_pixel_size(16)
        reports_icon.add_css_class("reports-pill-icon")

        reports_label = Gtk.Label(label=str(report_count))
        reports_label.add_css_class("reports-pill-label")

        reports_pill.append(reports_icon)
        reports_pill.append(reports_label)
        return reports_pill

    def _sync_saved_button(self) -> None:
        if self.saved_button.get_active():
            self.saved_button.set_icon_name("starred-symbolic")
            self.saved_button.set_tooltip_text(_("Remove from saved games"))
        else:
            self.saved_button.set_icon_name("non-starred-symbolic")
            self.saved_button.set_tooltip_text(_("Save game"))

    def _on_saved_toggled(self, button: Gtk.ToggleButton) -> None:
        self._sync_saved_button()
        if self._saved_changed is not None:
            self._saved_changed(self.summary, button.get_active())

    def _on_clicked(self, _button: Gtk.Button) -> None:
        dialog = GameDetailsDialog(
            self.parent_window,
            self.app_id,
            self.game_name,
            self.tier,
        )
        dialog.present()
