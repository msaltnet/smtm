import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import HackerNewsDataProvider


SAMPLE = {
    "hits": [
        {
            "objectID": "123",
            "title": "Bitcoin hits new ATH",
            "url": "https://example.com/a",
            "author": "alice",
            "points": 250,
            "num_comments": 88,
            "created_at": "2026-04-20T10:00:00.000Z",
        },
        {
            "objectID": "124",
            "title": "Ethereum devcon",
            "url": None,
            "author": "bob",
            "points": 100,
            "num_comments": 20,
            "created_at": "2026-04-20T09:00:00.000Z",
        },
    ]
}


class HackerNewsDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_returns_hackernews_items(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = HackerNewsDataProvider(count=5)
        info = dp.get_info()

        self.assertEqual(len(info), 2)
        first = info[0]
        self.assertEqual(first["type"], "hackernews")
        self.assertEqual(first["title"], "Bitcoin hits new ATH")
        self.assertEqual(first["points"], 250)
        self.assertEqual(first["num_comments"], 88)
        self.assertEqual(first["url"], "https://example.com/a")

    @patch("requests.get")
    def test_missing_url_falls_back_to_hn_story_url(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = HackerNewsDataProvider().get_info()

        self.assertEqual(info[1]["url"], "https://news.ycombinator.com/item?id=124")

    @patch("requests.get")
    def test_query_sent_as_param(self, mock_get):
        response = MagicMock()
        response.json.return_value = SAMPLE
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = HackerNewsDataProvider(query="solana", count=3)
        dp.get_info()

        params = mock_get.call_args.kwargs["params"]
        self.assertEqual(params["query"], "solana")
        self.assertEqual(params["hitsPerPage"], 3)

    @patch("requests.get")
    def test_http_error_returns_empty(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")
        self.assertEqual(HackerNewsDataProvider().get_info(), [])
