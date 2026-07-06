import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import YahooFinanceDataProvider


def _chart_payload(price, prev):
    return {
        "chart": {
            "result": [
                {
                    "meta": {
                        "regularMarketPrice": price,
                        "chartPreviousClose": prev,
                        "currency": "USD",
                        "exchangeName": "NYSE",
                        "regularMarketTime": 1712345678,
                    }
                }
            ]
        }
    }


class YahooFinanceDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_entry_per_symbol_with_change_pct(self, mock_get):
        responses = [
            MagicMock(json=MagicMock(return_value=_chart_payload(110.0, 100.0))),
            MagicMock(json=MagicMock(return_value=_chart_payload(4500.0, 4500.0))),
        ]
        for r in responses:
            r.raise_for_status.return_value = None
        mock_get.side_effect = responses

        dp = YahooFinanceDataProvider(symbols=[("DX-Y.NYB", "DXY"), ("^GSPC", "SP500")])
        info = dp.get_info()

        self.assertEqual(len(info), 2)
        self.assertEqual(info[0]["type"], "macro_market")
        self.assertEqual(info[0]["symbol"], "DX-Y.NYB")
        self.assertEqual(info[0]["label"], "DXY")
        self.assertAlmostEqual(info[0]["change_24h_pct"], 10.0)
        self.assertEqual(info[1]["label"], "SP500")
        self.assertEqual(info[1]["change_24h_pct"], 0.0)

    @patch("requests.get")
    def test_network_error_returns_empty_list(self, mock_get):
        mock_get.side_effect = requests.exceptions.RequestException("boom")

        dp = YahooFinanceDataProvider(symbols=[("^GSPC", "SP500")])
        self.assertEqual(dp.get_info(), [])

    @patch("requests.get")
    def test_malformed_payload_skipped(self, mock_get):
        response = MagicMock()
        response.json.return_value = {"chart": {"error": "invalid"}}
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = YahooFinanceDataProvider(symbols=[("DX-Y.NYB", "DXY")])
        self.assertEqual(dp.get_info(), [])

    @patch("requests.get")
    def test_sets_user_agent_header(self, mock_get):
        response = MagicMock()
        response.json.return_value = _chart_payload(1.0, 1.0)
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        YahooFinanceDataProvider(symbols=[("^VIX", "VIX")]).get_info()

        self.assertIn("User-Agent", mock_get.call_args.kwargs["headers"])

    def test_default_symbol_set_includes_core_macro(self):
        labels = {entry[1] for entry in YahooFinanceDataProvider.DEFAULT_SYMBOLS}
        self.assertIn("DXY", labels)
        self.assertIn("SP500", labels)
        self.assertIn("VIX", labels)
        self.assertIn("GOLD", labels)
        self.assertIn("US10Y", labels)
