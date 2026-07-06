import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import CoinGeckoDataProvider


SAMPLE = {
    "bitcoin": {
        "usd": 67000.0,
        "krw": 90000000.0,
        "usd_market_cap": 1_300_000_000_000,
        "usd_24h_vol": 30_000_000_000,
        "usd_24h_change": 2.5,
    }
}


class CoinGeckoDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_price_snapshot(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = CoinGeckoDataProvider("BTC")
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        item = info[0]
        self.assertEqual(item["type"], "price_snapshot")
        self.assertEqual(item["source"], "coingecko")
        self.assertEqual(item["coin_id"], "bitcoin")
        self.assertEqual(item["prices"]["usd"], 67000.0)
        self.assertEqual(item["prices"]["krw"], 90000000.0)
        self.assertEqual(item["market_cap_usd"], 1_300_000_000_000)
        self.assertEqual(item["volume_24h_usd"], 30_000_000_000)
        self.assertEqual(item["change_24h_pct"], 2.5)

    @patch("requests.get")
    def test_currency_mapping_used(self, mock_get):
        response = MagicMock()
        response.json.return_value = {"ethereum": {"usd": 3000}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = CoinGeckoDataProvider("ETH")
        info = dp.get_info()

        self.assertEqual(mock_get.call_args.kwargs["params"]["ids"], "ethereum")
        self.assertEqual(info[0]["coin_id"], "ethereum")

    def test_unknown_currency_returns_empty(self):
        dp = CoinGeckoDataProvider("UNKNOWN")
        self.assertEqual(dp.get_info(), [])

    @patch("requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        dp = CoinGeckoDataProvider("BTC")
        self.assertEqual(dp.get_info(), [])

    @patch("requests.get")
    def test_invalid_json_returns_empty(self, mock_get):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("bad json")
        mock_get.return_value = response
        dp = CoinGeckoDataProvider("BTC")
        self.assertEqual(dp.get_info(), [])
