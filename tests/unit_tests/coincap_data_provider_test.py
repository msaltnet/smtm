import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import CoinCapDataProvider


SAMPLE = {
    "data": {
        "id": "bitcoin",
        "rank": "1",
        "symbol": "BTC",
        "priceUsd": "65000.123456",
        "marketCapUsd": "1275000000000.0",
        "volumeUsd24Hr": "32000000000.0",
        "changePercent24Hr": "-1.234",
        "supply": "19600000",
        "maxSupply": "21000000",
        "vwap24Hr": "64500.0",
    }
}


class CoinCapTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_price_snapshot(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = CoinCapDataProvider().get_info()

        self.assertEqual(len(info), 1)
        entry = info[0]
        self.assertEqual(entry["type"], "price_snapshot")
        self.assertEqual(entry["source"], "coincap")
        self.assertEqual(entry["coin_id"], "bitcoin")
        self.assertAlmostEqual(entry["prices"]["usd"], 65000.123456)
        self.assertAlmostEqual(entry["market_cap_usd"], 1275000000000.0)
        self.assertAlmostEqual(entry["change_24h_pct"], -1.234)
        self.assertAlmostEqual(entry["supply"], 19600000.0)

    @patch("requests.get")
    def test_unsupported_currency_returns_empty(self, mock_get):
        self.assertEqual(CoinCapDataProvider(currency="ZZZ").get_info(), [])
        mock_get.assert_not_called()

    @patch("requests.get")
    def test_asset_id_mapping(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        CoinCapDataProvider(currency="ETH").get_info()

        self.assertTrue(mock_get.call_args.args[0].endswith("/ethereum"))

    @patch("requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("boom")
        self.assertEqual(CoinCapDataProvider().get_info(), [])
