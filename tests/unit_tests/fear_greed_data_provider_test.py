import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import FearGreedDataProvider


SAMPLE_PAYLOAD = {
    "name": "Fear and Greed Index",
    "data": [
        {
            "value": "54",
            "value_classification": "Neutral",
            "timestamp": "1713628800",
            "time_until_update": "3600",
        }
    ],
    "metadata": {"error": None},
}


class FearGreedDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_get_info_returns_sentiment_index_item(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE_PAYLOAD
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = FearGreedDataProvider()
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        item = info[0]
        self.assertEqual(item["type"], "sentiment_index")
        self.assertEqual(item["index_name"], "crypto_fear_and_greed")
        self.assertEqual(item["value"], 54)
        self.assertEqual(item["classification"], "Neutral")
        self.assertEqual(item["source"], "alternative.me/fng")
        self.assertEqual(item["date_time"], "1713628800")

    @patch("requests.get")
    def test_limit_passed_as_query_param(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE_PAYLOAD
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = FearGreedDataProvider(limit=7)
        dp.get_info()

        kwargs = mock_get.call_args.kwargs
        self.assertEqual(kwargs["params"], {"limit": 7})

    @patch("requests.get")
    def test_returns_empty_on_http_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")

        dp = FearGreedDataProvider()
        info = dp.get_info()

        self.assertEqual(info, [])

    @patch("requests.get")
    def test_returns_empty_on_json_error(self, mock_get):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.side_effect = ValueError("bad json")
        mock_get.return_value = response

        dp = FearGreedDataProvider()
        info = dp.get_info()

        self.assertEqual(info, [])

    @patch("requests.get")
    def test_non_numeric_value_preserved_as_none(self, mock_get):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "data": [{"value": "n/a", "value_classification": "", "timestamp": "0"}]
        }
        mock_get.return_value = response

        dp = FearGreedDataProvider()
        info = dp.get_info()

        self.assertEqual(len(info), 1)
        self.assertIsNone(info[0]["value"])

    @patch("requests.get")
    def test_missing_data_key_returns_empty(self, mock_get):
        response = MagicMock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"metadata": {"error": "nope"}}
        mock_get.return_value = response

        dp = FearGreedDataProvider()
        info = dp.get_info()

        self.assertEqual(info, [])
