import unittest
from unittest.mock import MagicMock

from smtm import MultiNewsDataProvider


class MultiNewsDataProviderTests(unittest.TestCase):
    def _news(self, source, title):
        return {
            "type": "news",
            "date_time": "Mon, 20 Apr 2026 10:00:00 +0000",
            "source": source,
            "title": title,
            "summary": "...",
            "url": f"https://example.com/{source}/{title}",
        }

    def test_aggregates_items_from_all_providers(self):
        p1 = MagicMock()
        p1.get_info.return_value = [self._news("src1", "A"), self._news("src1", "B")]
        p2 = MagicMock()
        p2.get_info.return_value = [self._news("src2", "C")]

        dp = MultiNewsDataProvider(providers=[p1, p2])
        info = dp.get_info()

        self.assertEqual(len(info), 3)
        self.assertEqual(info[0]["source"], "src1")
        self.assertEqual(info[2]["source"], "src2")

    def test_failed_provider_does_not_block_others(self):
        failing = MagicMock()
        failing.get_info.return_value = []
        ok = MagicMock()
        ok.get_info.return_value = [self._news("src2", "C")]

        dp = MultiNewsDataProvider(providers=[failing, ok])
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["source"], "src2")

    def test_default_providers_compose_four_sources(self):
        dp = MultiNewsDataProvider()
        self.assertEqual(len(dp.providers), 4)
        sources = [p.DEFAULT_SOURCE for p in dp.providers]
        self.assertIn("coindesk", sources)
        self.assertIn("cointelegraph", sources)
        self.assertIn("decrypt", sources)
        self.assertIn("cryptoslate", sources)

    def test_per_source_count_propagates_to_default_providers(self):
        dp = MultiNewsDataProvider(per_source_count=7)
        for provider in dp.providers:
            self.assertEqual(provider._count, 7)
