from __future__ import annotations

import json
import logging
import urllib.error
import urllib.parse
import urllib.request
from functools import lru_cache
from gettext import gettext as _
from html.parser import HTMLParser
from typing import Any

from ..core.constants import (
    DEFAULT_STEAM_COUNTRY,
    DEFAULT_STEAM_LANGUAGE,
    PROTON_SUMMARY_ENDPOINT,
    REQUEST_TIMEOUT_SECONDS,
    STEAM_APP_DETAILS_ENDPOINT,
    STEAM_SEARCH_ENDPOINT,
    USER_AGENT,
)
from ..core.formatters import format_price, normalize_tier, parse_search_price
from ..core.models import GameSummary, ProtonSummary


LOGGER = logging.getLogger(__name__)


STEAM_SEARCH_CURRENCY = "USD"


class SteamSearchResultParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.games: list[dict[str, Any]] = []
        self._current: dict[str, Any] | None = None
        self._capture: str | None = None

    def handle_starttag(
        self,
        tag: str,
        attrs: list[tuple[str, str | None]],
    ) -> None:
        attrs_dict = dict(attrs)
        classes = set((attrs_dict.get("class") or "").split())

        if tag == "a" and "search_result_row" in classes:
            app_id = _int_or_default(attrs_dict.get("data-ds-appid"))
            self._current = {
                "id": app_id,
                "name": _("Unknown game"),
                "platforms": {},
                "price": None,
                "metascore": "",
            }
            return

        if self._current is None:
            return

        if tag == "span" and "title" in classes:
            self._capture = "name"
            return

        if tag == "span" and "platform_img" in classes:
            platforms = self._current["platforms"]
            platforms["windows"] = platforms.get("windows", False) or "win" in classes
            platforms["mac"] = platforms.get("mac", False) or "mac" in classes
            platforms["linux"] = platforms.get("linux", False) or "linux" in classes
            return

        if tag == "div" and "search_metascore" in classes:
            self._capture = "metascore"
            return

        if tag == "div" and (
            "discount_final_price" in classes or "search_price" in classes
        ):
            self._capture = "price_text"

        price_final = attrs_dict.get("data-price-final")
        if price_final is not None:
            final = _int_or_default(price_final, default=-1)
            if final >= 0:
                self._current["price"] = {
                    "currency": STEAM_SEARCH_CURRENCY,
                    "final": final,
                }

    def handle_data(self, data: str) -> None:
        if self._current is None or self._capture is None:
            return

        value = data.strip()
        if not value:
            return

        if self._capture == "name":
            self._current["name"] = value
        elif self._capture == "metascore":
            self._current["metascore"] = value
        elif self._capture == "price_text" and value.lower() in {"free", "free to play"}:
            self._current["price"] = {"currency": STEAM_SEARCH_CURRENCY, "final": 0}

    def handle_endtag(self, tag: str) -> None:
        if tag in {"span", "div"}:
            self._capture = None
        if tag == "a" and self._current is not None:
            if self._current["id"]:
                self.games.append(self._current)
            self._current = None
            self._capture = None


def build_request(url: str) -> urllib.request.Request:
    return urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "application/json,text/plain;q=0.9,*/*;q=0.8",
        },
    )


def fetch_bytes(url: str) -> bytes:
    with urllib.request.urlopen(
        build_request(url), timeout=REQUEST_TIMEOUT_SECONDS
    ) as response:
        return response.read()


def fetch_json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(
        build_request(url), timeout=REQUEST_TIMEOUT_SECONDS
    ) as response:
        return json.loads(response.read().decode("utf-8", errors="replace"))


def _int_or_default(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


@lru_cache(maxsize=256)
def get_proton_summary(app_id: int) -> ProtonSummary:
    url = PROTON_SUMMARY_ENDPOINT.format(app_id=app_id)

    try:
        payload = fetch_json(url)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return ProtonSummary(tier="Unknown", confidence=None, total=0)
        raise

    return ProtonSummary(
        tier=normalize_tier(payload.get("tier")),
        confidence=payload.get("confidence"),
        total=_int_or_default(payload.get("total")),
    )


@lru_cache(maxsize=256)
def get_game_details(app_id: int) -> dict[str, Any]:
    params = urllib.parse.urlencode(
        {
            "appids": app_id,
            "l": DEFAULT_STEAM_LANGUAGE,
            "cc": DEFAULT_STEAM_COUNTRY,
        }
    )
    payload = fetch_json(f"{STEAM_APP_DETAILS_ENDPOINT}?{params}")
    app_payload = payload.get(str(app_id), {})
    if not app_payload.get("success"):
        raise RuntimeError("Steam appdetails returned success=false")

    data = app_payload.get("data")
    if not data:
        raise RuntimeError("No data in Steam appdetails response")

    return data


def search_steam_games_page(
    query: str,
    start: int = 0,
    count: int | None = None,
) -> tuple[list[dict[str, Any]], int]:
    params_data: dict[str, Any] = {
        "term": query,
        "l": DEFAULT_STEAM_LANGUAGE,
        "cc": DEFAULT_STEAM_COUNTRY,
        "query": "",
        "start": max(0, start),
        "dynamic_data": "",
        "sort_by": "_ASC",
        "snr": "1_7_7_151_7",
        "infinite": 1,
    }
    if count is not None:
        params_data["count"] = count

    params = urllib.parse.urlencode(params_data)
    payload = fetch_json(f"{STEAM_SEARCH_ENDPOINT}?{params}")
    parser = SteamSearchResultParser()
    parser.feed(payload.get("results_html", ""))
    return parser.games, _int_or_default(payload.get("total_count"))


def search_steam_games(
    query: str,
    start: int = 0,
    count: int | None = None,
) -> list[dict[str, Any]]:
    games, _total_count = search_steam_games_page(query, start=start, count=count)
    return games


def _resolve_search_price(game: dict[str, Any], app_id: int) -> tuple[str, bool]:
    price, is_free = parse_search_price(game.get("price"))
    if game.get("price") is not None or not app_id:
        return price, is_free

    try:
        details = get_game_details(app_id)
    except Exception as error:
        LOGGER.warning("Failed to fetch Steam details for %s: %s", app_id, error)
        return price, is_free

    details_is_free = bool(details.get("is_free"))
    return format_price(details.get("price_overview"), details_is_free), details_is_free


def build_game_summary(game: dict[str, Any]) -> GameSummary:
    app_id = _int_or_default(game.get("id"))
    game_name = str(game.get("name") or _("Unknown game"))
    tier = "Unknown"
    proton_confidence = ""
    proton_reports = 0

    price, is_free = _resolve_search_price(game, app_id)
    platforms = game.get("platforms") or {}
    metascore = str(game.get("metascore") or "")

    if app_id:
        try:
            proton_data = get_proton_summary(app_id)
            tier = proton_data.tier
            proton_confidence = proton_data.confidence or ""
            proton_reports = proton_data.total
        except Exception as error:
            LOGGER.warning(
                "Failed to fetch ProtonDB summary for %s: %s", app_id, error
            )

    return GameSummary(
        app_id=app_id,
        name=game_name,
        tier=tier,
        price=price,
        is_free=is_free,
        has_windows=bool(platforms.get("windows")),
        has_mac=bool(platforms.get("mac")),
        has_linux=bool(platforms.get("linux")),
        metascore=metascore,
        proton_confidence=proton_confidence,
        proton_reports=proton_reports,
    )
