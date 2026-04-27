import unittest

from src.core.models import GameSummary
from src.core.settings import RecentSearchesManager, SavedGamesManager


class FakeSettings:
    def __init__(self):
        self.values = {
            "recent-searches": [],
            "saved-games": [],
        }

    def get_strv(self, key):
        return self.values[key]

    def set_strv(self, key, value):
        self.values[key] = list(value)


class SettingsTests(unittest.TestCase):
    def test_recent_searches_are_deduplicated_and_newest_first(self):
        settings = FakeSettings()
        manager = RecentSearchesManager(settings)

        manager.add("Portal")
        manager.add("Hades")
        manager.add(" portal ")

        self.assertEqual(manager.list(), ["portal", "Hades"])

    def test_saved_games_round_trip_and_remove(self):
        settings = FakeSettings()
        manager = SavedGamesManager(settings)
        summary = GameSummary(
            app_id=70,
            name="Half-Life",
            tier="Platinum",
            price="USD 9.99",
            is_free=False,
            has_windows=True,
            has_mac=True,
            has_linux=True,
            metascore="96",
            proton_confidence="strong",
            proton_reports=120,
        )

        manager.save(summary)

        self.assertTrue(manager.is_saved(70))
        self.assertEqual(manager.list(), [summary])

        manager.remove(70)

        self.assertFalse(manager.is_saved(70))
        self.assertEqual(manager.list(), [])

    def test_saved_games_tolerate_invalid_numeric_fields(self):
        settings = FakeSettings()
        settings.set_strv(
            "saved-games",
            [
                (
                    '{"app_id":"not-an-int","name":"Broken",'
                    '"proton_reports":"also-broken"}'
                )
            ],
        )
        manager = SavedGamesManager(settings)

        self.assertEqual(manager.list(), [])


if __name__ == "__main__":
    unittest.main()
