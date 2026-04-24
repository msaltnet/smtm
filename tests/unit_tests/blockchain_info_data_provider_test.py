import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import BlockchainInfoDataProvider


SAMPLE = {
    "hash_rate": 500000000.0,
    "difficulty": 72e12,
    "totalbc": 19700000,
    "n_blocks_total": 840000,
    "n_tx": 350000,
    "minutes_between_blocks": 9.8,
    "miners_revenue_usd": 40000000,
    "market_price_usd": 67000,
    "timestamp": 1713628800,
}


class BlockchainInfoDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_onchain_stats(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = BlockchainInfoDataProvider("BTC")
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        item = info[0]
        self.assertEqual(item["type"], "onchain_stats")
        self.assertEqual(item["chain"], "bitcoin")
        self.assertEqual(item["hash_rate_ghs"], 500000000.0)
        self.assertEqual(item["n_tx_24h"], 350000)
        self.assertEqual(item["market_price_usd"], 67000)

    def test_non_btc_returns_empty(self):
        dp = BlockchainInfoDataProvider("ETH")
        self.assertEqual(dp.get_info(), [])

    @patch("requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        self.assertEqual(BlockchainInfoDataProvider("BTC").get_info(), [])
