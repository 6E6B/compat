from __future__ import annotations

import html
import re
from gettext import gettext as _
from typing import Any

from .constants import KNOWN_TIERS


def html_to_text(value: str | None) -> str:
    if not value:
        return ""

    text = value
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li[^>]*>", "* ", text, flags=re.IGNORECASE)
    text = re.sub(r"</h[1-6]\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<h[1-6][^>]*>", "", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def normalize_tier(value: Any) -> str:
    if not value:
        return "Unknown"

    normalized = str(value).strip().lower()
    return KNOWN_TIERS.get(normalized, str(value).strip().title() or "Unknown")


def format_price(price_overview: dict[str, Any] | None, is_free: bool) -> str:
    if is_free:
        return "Free"

    if not price_overview:
        return "Unavailable"

    final_formatted = price_overview.get("final_formatted")
    if final_formatted:
        return str(final_formatted)

    final_price = price_overview.get("final")
    currency = price_overview.get("currency", "")
    if final_price is not None:
        return f"{currency} {final_price / 100:.2f}".strip()

    return "Unavailable"


def format_platforms(platforms: dict[str, Any] | None) -> str:
    if not platforms:
        return "Unknown"

    items: list[str] = []
    if platforms.get("windows"):
        items.append("Windows")
    if platforms.get("mac"):
        items.append("macOS")
    if platforms.get("linux"):
        items.append("Linux")

    return ", ".join(items) if items else "Unknown"


def format_list(items: list[Any] | None) -> str:
    if not items:
        return "Unknown"
    return ", ".join(str(item) for item in items if item) or "Unknown"


def format_named_list(items: list[dict[str, Any]] | None) -> str:
    if not items:
        return "Unknown"

    return (
        ", ".join(
            item.get("description", "") for item in items if item.get("description")
        )
        or "Unknown"
    )


def parse_search_price(price_data: dict[str, Any] | None) -> tuple[str, bool]:
    if not price_data:
        return _("N/A"), False

    final_price = price_data.get("final")
    currency = price_data.get("currency", "")

    if final_price is None:
        return _("N/A"), False

    if final_price == 0:
        return _("Free"), True

    return f"{currency} {final_price / 100:.2f}".strip(), False
