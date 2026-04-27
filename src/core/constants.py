from __future__ import annotations

APP_ID = "io.github._6e6b.compat"

DEFAULT_STEAM_LANGUAGE = "english"
DEFAULT_STEAM_COUNTRY = "US"

MIN_WINDOW_WIDTH = 860
MIN_WINDOW_HEIGHT = 640

THUMB_W = 460
THUMB_H = 215
CARD_W = 460
CARD_TITLE_CHARS = 40
DETAIL_HEADER_W = 460
DETAIL_HEADER_H = 215

STEAM_SEARCH_ENDPOINT = "https://store.steampowered.com/search/results/"
STEAM_APP_DETAILS_ENDPOINT = "https://store.steampowered.com/api/appdetails"
STEAM_HEADER_IMAGE_TEMPLATE = "https://steamcdn-a.akamaihd.net/steam/apps/{app_id}/header.jpg"
PROTON_SUMMARY_ENDPOINT = (
    "https://www.protondb.com/api/v1/reports/summaries/{app_id}.json"
)

REQUEST_TIMEOUT_SECONDS = 20
SEARCH_PAGE_SIZE = 50
MAX_TIER_WORKERS = 6

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

KNOWN_TIERS = {
    "borked": "Borked",
    "bronze": "Bronze",
    "silver": "Silver",
    "gold": "Gold",
    "platinum": "Platinum",
    "native": "Native",
    "pending": "Pending",
}
