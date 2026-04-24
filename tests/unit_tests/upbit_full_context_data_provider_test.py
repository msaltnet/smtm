import unittest
from unittest.mock import MagicMock

from smtm import UpbitFullContextDataProvider


class UpbitFullContextDataProviderTests(unittest.TestCase):
    def test_factory_metadata(self):
        self.assertEqual(UpbitFullContextDataProvider.CODE, "UFC")
        self.assertEqual(UpbitFullContextDataProvider.NAME, "UPBIT FULL CONTEXT DP")

    def test_default_providers_cover_expected_sources(self):
        dp = UpbitFullContextDataProvider("BTC")
        type_names = {type(p).__name__ for p in dp.providers}

        for expected in [
            "CoinGeckoDataProvider",
            "BlockchainInfoDataProvider",
            "MempoolFeesDataProvider",
            "BinanceFundingRateDataProvider",
            "FearGreedDataProvider",
            "ExchangeRateDataProvider",
            "UpbitNoticeDataProvider",
            "MultiNewsDataProvider",
            "CryptoCurrencyRedditDataProvider",
            "BitcoinRedditDataProvider",
            "HackerNewsDataProvider",
        ]:
            self.assertIn(expected, type_names)

    def test_get_info_merges_candle_with_each_provider_output(self):
        dp = UpbitFullContextDataProvider("BTC")
        dp.upbit_dp = MagicMock()
        dp.upbit_dp.get_info.return_value = [
            {"market": "BTC", "closing_price": 50_000_000}
        ]
        p1 = MagicMock()
        p1.get_info.return_value = [{"type": "price_snapshot", "source": "coingecko"}]
        p2 = MagicMock()
        p2.get_info.return_value = [{"type": "funding_rate", "source": "binance"}]
        p3 = MagicMock()
        p3.get_info.return_value = []
        dp.providers = [p1, p2, p3]

        info = dp.get_info()

        self.assertEqual(len(info), 3)
        self.assertEqual(info[0]["type"], "primary_candle")
        self.assertEqual(info[1]["type"], "price_snapshot")
        self.assertEqual(info[2]["type"], "funding_rate")
