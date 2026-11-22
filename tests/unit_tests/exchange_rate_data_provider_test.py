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

    @patch("requests.get")
    def test_default_provider_preserves_url_and_source(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        mock_get.return_value = response
        item = ExchangeRateDataProvider().get_info()[0]
        mock_get.assert_called_once_with(
            "https://open.er-api.com/v6/latest/USD", timeout=5,
        )
        self.assertEqual(item["source"], "open.er-api.com")
        self.assertEqual(item["date_time"], SAMPLE["time_last_update_utc"])

    @patch("requests.get")
    def test_opt_in_allratestoday_uses_daily_reference_endpoint_and_source(self, mock_get):
        response = MagicMock()
        response.json.return_value = {
            **SAMPLE,
            "date": "2026-11-20",
            "attribution": "Exchange rates by AllRatesToday — https://allratestoday.com",
        }
        mock_get.return_value = response
        item = ExchangeRateDataProvider(provider="allratestoday").get_info()[0]
        mock_get.assert_called_once_with(
            "https://allratestoday.com/api/open/latest/USD", timeout=5,
        )
        self.assertEqual(item["source"], "allratestoday")
        self.assertEqual(item["rates"], {
            "KRW": 1365.5, "JPY": 155.2, "EUR": 0.91, "CNY": 7.2,
        })
        self.assertEqual(item["date_time"], SAMPLE["time_last_update_utc"])

    @patch("requests.get")
    def test_alternate_provider_respects_requested_base_and_quotes(self, mock_get):
        response = MagicMock()
        response.json.return_value = {
            "result": "success", "base_code": "EUR",
            "rates": {"KRW": 1500.1, "USD": 1.1},
            "time_last_update_utc": "Fri, 20 Nov 2026 15:00:00 GMT",
        }
        mock_get.return_value = response
        item = ExchangeRateDataProvider(
            provider="allratestoday", base="eur", quotes=("krw", "usd"),
        ).get_info()[0]
        mock_get.assert_called_once_with(
            "https://allratestoday.com/api/open/latest/EUR", timeout=5,
        )
        self.assertEqual(item["base"], "EUR")
        self.assertEqual(item["rates"], {"KRW": 1500.1, "USD": 1.1})

    def test_invalid_provider_rejected_before_any_network(self):
        for provider in ("unknown", "", 0, False, [], {}):
            with self.subTest(provider=provider), self.assertRaises(ValueError):
                ExchangeRateDataProvider(provider=provider)

    def test_custom_url_conflict_is_rejected(self):
        with self.assertRaises(ValueError):
            ExchangeRateDataProvider(
                provider="allratestoday", url="https://example.invalid/latest/USD",
            )

    @patch("requests.get")
    def test_existing_custom_url_remains_supported(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        mock_get.return_value = response
        item = ExchangeRateDataProvider(
            "BTC", 60, "USD", None, "https://example.invalid/latest/USD"
        ).get_info()[0]
        mock_get.assert_called_once_with(
            "https://example.invalid/latest/USD", timeout=5,
        )
        self.assertEqual(item["source"], "open.er-api.com")

    @patch("requests.get")
    def test_alternate_provider_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.HTTPError("429 Too Many Requests")
        self.assertEqual(ExchangeRateDataProvider(provider="allratestoday").get_info(), [])
