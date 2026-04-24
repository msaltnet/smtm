import unittest
from unittest.mock import MagicMock

from smtm import UpbitMultiNewsDataProvider


class UpbitMultiNewsDataProviderTests(unittest.TestCase):
    def test_get_info_merges_candle_and_multi_source_news(self):
        dp = UpbitMultiNewsDataProvider("BTC")
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
                "source": "coindesk",
                "title": "A",
                "summary": "",
                "url": "",
                "date_time": "",
            },
            {
                "type": "news",
                "source": "cointelegraph",
                "title": "B",
                "summary": "",
                "url": "",
                "date_time": "",
            },
        ]

        info = dp.get_info()

        self.assertEqual(len(info), 3)
        self.assertEqual(info[0]["type"], "primary_candle")
        self.assertEqual(info[1]["source"], "coindesk")
        self.assertEqual(info[2]["source"], "cointelegraph")

    def test_factory_code_is_umn(self):
        self.assertEqual(UpbitMultiNewsDataProvider.CODE, "UMN")
        self.assertEqual(UpbitMultiNewsDataProvider.NAME, "UPBIT MULTI NEWS DP")
