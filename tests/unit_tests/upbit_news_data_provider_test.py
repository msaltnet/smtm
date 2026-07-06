import unittest
from unittest.mock import MagicMock

from smtm import UpbitNewsDataProvider


class UpbitNewsDataProviderTests(unittest.TestCase):
    def test_get_info_merges_candle_and_news(self):
        dp = UpbitNewsDataProvider("BTC")
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
        dp.news_dp = MagicMock()
        dp.news_dp.get_info.return_value = [
            {
                "type": "news",
                "date_time": "Mon, 20 Apr 2026 10:00:00 +0000",
                "source": "coindesk",
                "title": "Bitcoin rallies",
                "summary": "Short summary.",
                "url": "https://example.com/1",
            },
            {
                "type": "news",
                "date_time": "Mon, 20 Apr 2026 09:30:00 +0000",
                "source": "coindesk",
                "title": "Regulator comment",
                "summary": "...",
                "url": "https://example.com/2",
            },
        ]

        info = dp.get_info()

        self.assertEqual(len(info), 3)
        self.assertEqual(info[0]["type"], "primary_candle")
        self.assertEqual(info[0]["market"], "BTC")
        self.assertEqual(info[1]["type"], "news")
        self.assertEqual(info[1]["title"], "Bitcoin rallies")
        self.assertEqual(info[2]["type"], "news")
        self.assertEqual(info[2]["title"], "Regulator comment")

    def test_get_info_returns_only_candle_when_news_empty(self):
        dp = UpbitNewsDataProvider("BTC")
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
        dp.news_dp = MagicMock()
        dp.news_dp.get_info.return_value = []

        info = dp.get_info()

        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["type"], "primary_candle")

    def test_get_info_returns_only_news_when_candle_empty(self):
        dp = UpbitNewsDataProvider("BTC")
        dp.upbit_dp = MagicMock()
        dp.upbit_dp.get_info.return_value = []
        dp.news_dp = MagicMock()
        dp.news_dp.get_info.return_value = [
            {
                "type": "news",
                "date_time": "...",
                "source": "coindesk",
                "title": "T",
                "summary": "S",
                "url": "U",
            }
        ]

        info = dp.get_info()

        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["type"], "news")
