import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import BinanceFundingRateDataProvider


SAMPLE = {
    "symbol": "BTCUSDT",
    "markPrice": "67000.5",
    "indexPrice": "67010.2",
    "lastFundingRate": "0.0001",
    "nextFundingTime": 1713628800000,
    "time": 1713628000000,
}


class BinanceFundingRateDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_funding_rate(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = BinanceFundingRateDataProvider("BTC")
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        item = info[0]
        self.assertEqual(item["type"], "funding_rate")
        self.assertEqual(item["symbol"], "BTCUSDT")
        self.assertAlmostEqual(item["funding_rate"], 0.0001)
        self.assertAlmostEqual(item["funding_rate_pct"], 0.01)
        self.assertAlmostEqual(item["mark_price"], 67000.5)
        self.assertAlmostEqual(item["index_price"], 67010.2)

    @patch("requests.get")
    def test_symbol_built_from_currency(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = BinanceFundingRateDataProvider("ETH")
        dp.get_info()

        self.assertEqual(mock_get.call_args.kwargs["params"]["symbol"], "ETHUSDT")

    @patch("requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        self.assertEqual(BinanceFundingRateDataProvider("BTC").get_info(), [])

    @patch("requests.get")
    def test_non_numeric_values_preserved_as_none(self, mock_get):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "symbol": "BTCUSDT",
            "markPrice": "n/a",
            "indexPrice": None,
            "lastFundingRate": None,
        }
        mock_get.return_value = response

        info = BinanceFundingRateDataProvider("BTC").get_info()

        self.assertEqual(len(info), 1)
        self.assertIsNone(info[0]["funding_rate"])
        self.assertIsNone(info[0]["mark_price"])
