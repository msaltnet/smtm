import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import NewsDataProvider


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Crypto News</title>
    <link>https://example.com/</link>
    <description>Sample feed</description>
    <item>
      <title>Bitcoin hits new high</title>
      <link>https://example.com/news/1</link>
      <description>BTC surpasses previous ATH on strong inflows.</description>
      <pubDate>Mon, 20 Apr 2026 10:00:00 +0000</pubDate>
    </item>
    <item>
      <title>Ethereum upgrade ships</title>
      <link>https://example.com/news/2</link>
      <description>The latest upgrade goes live on mainnet.</description>
      <pubDate>Mon, 20 Apr 2026 09:30:00 +0000</pubDate>
    </item>
    <item>
      <title>Regulator comment</title>
      <link>https://example.com/news/3</link>
      <description>Officials weigh in on exchange licensing.</description>
      <pubDate>Mon, 20 Apr 2026 09:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""


class NewsDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_get_info_returns_news_items_in_typed_dict_format(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = NewsDataProvider(count=3)
        info = dp.get_info()

        self.assertEqual(len(info), 3)
        first = info[0]
        self.assertEqual(first["type"], "news")
        self.assertEqual(first["title"], "Bitcoin hits new high")
        self.assertEqual(first["summary"], "BTC surpasses previous ATH on strong inflows.")
        self.assertEqual(first["url"], "https://example.com/news/1")
        self.assertEqual(first["date_time"], "Mon, 20 Apr 2026 10:00:00 +0000")
        self.assertEqual(first["source"], NewsDataProvider.DEFAULT_SOURCE)

    @patch("requests.get")
    def test_get_info_respects_count_limit(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = NewsDataProvider(count=2)
        info = dp.get_info()

        self.assertEqual(len(info), 2)
        self.assertEqual(info[1]["title"], "Ethereum upgrade ships")

    @patch("requests.get")
    def test_get_info_returns_empty_list_on_http_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")

        dp = NewsDataProvider()
        info = dp.get_info()

        self.assertEqual(info, [])

    @patch("requests.get")
    def test_get_info_returns_empty_list_on_invalid_xml(self, mock_get):
        response = MagicMock()
        response.text = "<<<not-xml>>>"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = NewsDataProvider()
        info = dp.get_info()

        self.assertEqual(info, [])

    @patch("requests.get")
    def test_custom_url_and_source_are_used(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        custom_url = "https://custom.example.com/rss"
        dp = NewsDataProvider(url=custom_url, source="custom")
        info = dp.get_info()

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.args[0], custom_url)
        self.assertEqual(info[0]["source"], "custom")
