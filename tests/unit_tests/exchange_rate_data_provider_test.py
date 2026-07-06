import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import ExchangeRateDataProvider


SAMPLE = {
    "result": "success",
    "base_code": "USD",
    "rates": {"KRW": 1365.5, "JPY": 155.2, "EUR": 0.91, "CNY": 7.2, "XYZ": 1.0},
    "time_last_update_utc": "Mon, 21 Apr 2026 00:00:00 +0000",
}


class ExchangeRateDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_exchange_rate_item(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = ExchangeRateDataProvider()
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        item = info[0]
        self.assertEqual(item["type"], "exchange_rate")
        self.assertEqual(item["base"], "USD")
        self.assertEqual(item["rates"]["KRW"], 1365.5)
        self.assertNotIn("XYZ", item["rates"])

    @patch("requests.get")
    def test_unknown_quote_filtered_out(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = ExchangeRateDataProvider(quotes=("KRW", "MISSING"))
        info = dp.get_info()

        self.assertEqual(info[0]["rates"], {"KRW": 1365.5})

    @patch("requests.get")
    def test_failure_result_returns_empty(self, mock_get):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"result": "error"}
        mock_get.return_value = response

        self.assertEqual(ExchangeRateDataProvider().get_info(), [])

    @patch("requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        self.assertEqual(ExchangeRateDataProvider().get_info(), [])
