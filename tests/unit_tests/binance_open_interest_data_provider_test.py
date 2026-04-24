import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import BinanceOpenInterestDataProvider


SAMPLE = [
    {
        "symbol": "BTCUSDT",
        "sumOpenInterest": "123456.7",
        "sumOpenInterestValue": "9876543210.5",
        "timestamp": 1712345678000,
    }
]


class BinanceOpenInterestTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_normalized_entry(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = BinanceOpenInterestDataProvider().get_info()

        self.assertEqual(len(info), 1)
        entry = info[0]
        self.assertEqual(entry["type"], "open_interest")
        self.assertEqual(entry["symbol"], "BTCUSDT")
        self.assertAlmostEqual(entry["open_interest_contracts"], 123456.7)
        self.assertAlmostEqual(entry["open_interest_notional_usd"], 9876543210.5)

    @patch("requests.get")
    def test_uses_symbol_from_currency(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        BinanceOpenInterestDataProvider(currency="ETH").get_info()

        self.assertEqual(mock_get.call_args.kwargs["params"]["symbol"], "ETHUSDT")

    @patch("requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("boom")
        self.assertEqual(BinanceOpenInterestDataProvider().get_info(), [])

    @patch("requests.get")
    def test_empty_payload_returns_empty(self, mock_get):
        response = MagicMock()
        response.json.return_value = []
        response.raise_for_status.return_value = None
        mock_get.return_value = response
        self.assertEqual(BinanceOpenInterestDataProvider().get_info(), [])
