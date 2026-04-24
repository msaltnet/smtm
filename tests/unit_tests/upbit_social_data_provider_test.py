import unittest
from unittest.mock import MagicMock

from smtm import UpbitSocialDataProvider


class UpbitSocialDataProviderTests(unittest.TestCase):
    def test_factory_metadata(self):
        self.assertEqual(UpbitSocialDataProvider.CODE, "USC")
        self.assertEqual(UpbitSocialDataProvider.NAME, "UPBIT SOCIAL DP")

    def test_default_providers_include_news_reddit_sentiment(self):
        dp = UpbitSocialDataProvider("BTC")
        type_names = [type(p).__name__ for p in dp.providers]
        self.assertIn("MultiNewsDataProvider", type_names)
        self.assertIn("CryptoCurrencyRedditDataProvider", type_names)
        self.assertIn("BitcoinRedditDataProvider", type_names)
        self.assertIn("FearGreedDataProvider", type_names)

    def test_get_info_merges_candle_and_mixed_sources(self):
        dp = UpbitSocialDataProvider("BTC")
        dp.upbit_dp = MagicMock()
        dp.upbit_dp.get_info.return_value = [
            {
                "market": "BTC",
                "date_time": "2026-04-20T22:52:00",
                "opening_price": 50_000_000,
                "high_price": 50_200_000,
                "low_price": 49_800_000,
                "closing_price": 50_100_000,
                "acc_price": 1_000_000_000,
                "acc_volume": 20.0,
            }
        ]
        news = MagicMock()
        news.get_info.return_value = [
            {"type": "news", "source": "coindesk", "title": "N1"}
        ]
        reddit = MagicMock()
        reddit.get_info.return_value = [
            {"type": "reddit", "source": "reddit/CryptoCurrency", "title": "R1"}
        ]
        sentiment = MagicMock()
        sentiment.get_info.return_value = [
            {"type": "sentiment_index", "value": 42, "classification": "Fear"}
        ]
        dp.providers = [news, reddit, sentiment]

        info = dp.get_info()

        self.assertEqual(len(info), 4)
        self.assertEqual(info[0]["type"], "primary_candle")
        self.assertEqual(info[1]["type"], "news")
        self.assertEqual(info[2]["type"], "reddit")
        self.assertEqual(info[3]["type"], "sentiment_index")

    def test_failed_extra_provider_does_not_break_others(self):
        dp = UpbitSocialDataProvider("BTC")
        dp.upbit_dp = MagicMock()
        dp.upbit_dp.get_info.return_value = []
        failing = MagicMock()
        failing.get_info.return_value = []
        ok = MagicMock()
        ok.get_info.return_value = [{"type": "reddit", "title": "ok"}]
        dp.providers = [failing, ok]

        info = dp.get_info()

        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["title"], "ok")
