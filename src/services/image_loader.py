from __future__ import annotations

import logging
import threading
from collections.abc import Callable

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gdk, GLib, Gtk

from ..core.constants import STEAM_HEADER_IMAGE_TEMPLATE
from ..core.formatters import normalize_tier
from .steam_service import fetch_bytes


LOGGER = logging.getLogger(__name__)


def start_daemon_thread(
    target: Callable[..., object], *args: object
) -> threading.Thread:
    thread = threading.Thread(target=target, args=args, daemon=True)
    thread.start()
    return thread


def apply_image_data(
    image_data: bytes,
    picture_widget: Gtk.Picture,
    stack_widget: Gtk.Stack | None = None,
) -> bool:
    try:
        bytes_data = GLib.Bytes.new(image_data)
        texture = Gdk.Texture.new_from_bytes(bytes_data)
        picture_widget.set_paintable(texture)
        if stack_widget is not None:
            stack_widget.set_visible_child(picture_widget)
    except Exception as error:
        LOGGER.debug("Texture creation error: %s", error)
    return False


def set_picture_from_url(
    url: str,
    picture_widget: Gtk.Picture,
    stack_widget: Gtk.Stack | None = None,
) -> None:
    try:
        image_data = fetch_bytes(url)
        GLib.idle_add(apply_image_data, image_data, picture_widget, stack_widget)
    except Exception as error:
        LOGGER.debug("Image load error for %s: %s", url, error)


def fetch_and_set_game_image(
    app_id: int,
    picture_widget: Gtk.Picture,
    stack_widget: Gtk.Stack | None = None,
) -> None:
    url = STEAM_HEADER_IMAGE_TEMPLATE.format(app_id=app_id)
    set_picture_from_url(url, picture_widget, stack_widget)


def create_badge(label: Gtk.Label, tier: str) -> None:
    normalized_tier = normalize_tier(tier)
    label.set_label(normalized_tier)
    label.add_css_class("pill")
    label.add_css_class("proton-badge")
    label.add_css_class(normalized_tier.lower())
