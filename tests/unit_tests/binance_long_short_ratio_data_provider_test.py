import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import BinanceLongShortRatioDataProvider


SAMPLE = [
    {
        "symbol": "BTCUSDT",
        "longShortRatio": "2.35",
        "longAccount": "0.70",
        "shortAccount": "0.30",
        "timestamp": 1712345678000,
    }
]


class BinanceLongShortRatioTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_normalized_entry(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = BinanceLongShortRatioDataProvider().get_info()

        self.assertEqual(len(info), 1)
        entry = info[0]
        self.assertEqual(entry["type"], "long_short_ratio")
        self.assertEqual(entry["symbol"], "BTCUSDT")
        self.assertEqual(entry["scope"], "global")
        self.assertAlmostEqual(entry["long_short_ratio"], 2.35)
        self.assertAlmostEqual(entry["long_account_pct"], 70.0)
        self.assertAlmostEqual(entry["short_account_pct"], 30.0)

    @patch("requests.get")
    def test_top_scope_hits_different_endpoint(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        BinanceLongShortRatioDataProvider(scope="top").get_info()

        self.assertIn("topLongShortAccountRatio", mock_get.call_args.args[0])

    @patch("requests.get")
    def test_network_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("boom")
        self.assertEqual(BinanceLongShortRatioDataProvider().get_info(), [])

    @patch("requests.get")
    def test_percent_passthrough_when_already_scaled(self, mock_get):
        response = MagicMock()
        response.json.return_value = [
            {
                "symbol": "BTCUSDT",
                "longShortRatio": "1.0",
                "longAccount": "55",
                "shortAccount": "45",
                "timestamp": 1,
            }
        ]
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = BinanceLongShortRatioDataProvider().get_info()
        self.assertAlmostEqual(info[0]["long_account_pct"], 55.0)
        self.assertAlmostEqual(info[0]["short_account_pct"], 45.0)
