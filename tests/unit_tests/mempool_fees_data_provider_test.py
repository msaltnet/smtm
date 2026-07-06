import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import MempoolFeesDataProvider


SAMPLE = {
    "fastestFee": 42,
    "halfHourFee": 38,
    "hourFee": 30,
    "economyFee": 25,
    "minimumFee": 2,
}


class MempoolFeesDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_mempool_fees(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = MempoolFeesDataProvider("BTC")
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        item = info[0]
        self.assertEqual(item["type"], "mempool_fees")
        self.assertEqual(item["unit"], "sat/vB")
        self.assertEqual(item["fastest_fee"], 42)
        self.assertEqual(item["minimum_fee"], 2)

    def test_non_btc_returns_empty(self):
        dp = MempoolFeesDataProvider("ETH")
        self.assertEqual(dp.get_info(), [])

    @patch("requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        self.assertEqual(MempoolFeesDataProvider("BTC").get_info(), [])
