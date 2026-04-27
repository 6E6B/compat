import unittest

from src.core.formatters import (
    format_platforms,
    format_price,
    html_to_text,
    normalize_tier,
)


class FormatterTests(unittest.TestCase):
    def test_html_to_text_removes_markup_and_decodes_entities(self):
        self.assertEqual(
            html_to_text("<p>Hello&nbsp;there<br>Deck</p>"),
            "Hello there\nDeck",
        )

    def test_normalize_tier_known_and_unknown_values(self):
        self.assertEqual(normalize_tier("platinum"), "Platinum")
        self.assertEqual(normalize_tier("not rated"), "Not Rated")
        self.assertEqual(normalize_tier(None), "Unknown")

    def test_format_price_handles_common_store_values(self):
        self.assertEqual(format_price(None, True), "Free")
        self.assertEqual(
            format_price({"final": 1999, "currency": "USD"}, False),
            "USD 19.99",
        )
        self.assertEqual(format_price(None, False), "Unavailable")

    def test_format_platforms_lists_enabled_platforms(self):
        self.assertEqual(
            format_platforms({"windows": True, "mac": False, "linux": True}),
            "Windows, Linux",
        )
        self.assertEqual(format_platforms({}), "Unknown")


if __name__ == "__main__":
    unittest.main()
