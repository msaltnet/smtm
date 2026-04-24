import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import CryptoGlobalDataProvider


SAMPLE_PAYLOAD = {
    "data": {
        "total_market_cap": {"usd": 2_500_000_000_000},
        "total_volume": {"usd": 120_000_000_000},
        "market_cap_percentage": {
            "btc": 52.3,
            "eth": 15.1,
            "usdt": 4.0,
            "usdc": 1.5,
            "dai": 0.3,
        },
        "market_cap_change_percentage_24h_usd": -1.25,
        "active_cryptocurrencies": 13000,
        "markets": 900,
        "updated_at": 1712345678,
    }
}


class CryptoGlobalDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_normalized_entry(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE_PAYLOAD
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = CryptoGlobalDataProvider().get_info()

        self.assertEqual(len(info), 1)
        entry = info[0]
        self.assertEqual(entry["type"], "crypto_global")
        self.assertEqual(entry["source"], "coingecko")
        self.assertEqual(entry["total_market_cap_usd"], 2_500_000_000_000)
        self.assertEqual(entry["total_volume_24h_usd"], 120_000_000_000)
        self.assertAlmostEqual(entry["btc_dominance_pct"], 52.3)
        self.assertAlmostEqual(entry["eth_dominance_pct"], 15.1)
        self.assertAlmostEqual(entry["stablecoin_dominance_pct"], 5.8)
        self.assertEqual(entry["active_cryptocurrencies"], 13000)

    @patch("requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("boom")
        self.assertEqual(CryptoGlobalDataProvider().get_info(), [])

    @patch("requests.get")
    def test_missing_data_field_returns_empty(self, mock_get):
        response = MagicMock()
        response.json.return_value = {"no_data": True}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        self.assertEqual(CryptoGlobalDataProvider().get_info(), [])

    @patch("requests.get")
    def test_hits_default_endpoint(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE_PAYLOAD
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        CryptoGlobalDataProvider().get_info()

        self.assertEqual(
            mock_get.call_args.args[0],
            "https://api.coingecko.com/api/v3/global",
        )
