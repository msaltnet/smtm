import unittest
from unittest.mock import patch, MagicMock
import requests

from smtm import (
    RedditDataProvider,
    CryptoCurrencyRedditDataProvider,
    BitcoinRedditDataProvider,
)


SAMPLE_ATOM = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>CryptoCurrency</title>
  <entry>
    <title>BTC discussion</title>
    <link href="https://www.reddit.com/r/CryptoCurrency/comments/abc/" />
    <updated>2026-04-20T10:00:00+00:00</updated>
    <content type="html">Body A</content>
    <author><name>u/alice</name></author>
  </entry>
  <entry>
    <title>ETH news</title>
    <link href="https://www.reddit.com/r/CryptoCurrency/comments/def/" />
    <updated>2026-04-20T09:30:00+00:00</updated>
    <content type="html">Body B</content>
    <author><name>u/bob</name></author>
  </entry>
  <entry>
    <title>Weekly thread</title>
    <link href="https://www.reddit.com/r/CryptoCurrency/comments/ghi/" />
    <updated>2026-04-20T08:00:00+00:00</updated>
    <content type="html">Body C</content>
    <author><name>u/carol</name></author>
  </entry>
</feed>
"""


class RedditDataProviderTests(unittest.TestCase):
    @patch("requests.get")
    def test_get_info_returns_typed_reddit_items(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_ATOM
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = RedditDataProvider(count=3)
        info = dp.get_info()

        self.assertEqual(len(info), 3)
        first = info[0]
        self.assertEqual(first["type"], "reddit")
        self.assertEqual(first["title"], "BTC discussion")
        self.assertEqual(first["summary"], "Body A")
        self.assertEqual(
            first["url"], "https://www.reddit.com/r/CryptoCurrency/comments/abc/"
        )
        self.assertEqual(first["author"], "u/alice")
        self.assertEqual(first["source"], "reddit/CryptoCurrency")
        self.assertEqual(first["date_time"], "2026-04-20T10:00:00+00:00")

    @patch("requests.get")
    def test_count_limit(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_ATOM
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = RedditDataProvider(count=2)
        info = dp.get_info()

        self.assertEqual(len(info), 2)

    @patch("requests.get")
    def test_user_agent_header_sent(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_ATOM
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = RedditDataProvider(user_agent="custom-agent/1.0")
        dp.get_info()

        kwargs = mock_get.call_args.kwargs
        self.assertEqual(kwargs["headers"]["User-Agent"], "custom-agent/1.0")

    @patch("requests.get")
    def test_returns_empty_on_http_error(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("boom")

        dp = RedditDataProvider()
        info = dp.get_info()

        self.assertEqual(info, [])

    @patch("requests.get")
    def test_returns_empty_on_invalid_xml(self, mock_get):
        response = MagicMock()
        response.text = "<<<not-xml>>>"
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = RedditDataProvider()
        info = dp.get_info()

        self.assertEqual(info, [])

    def test_subreddit_presets(self):
        self.assertEqual(
            CryptoCurrencyRedditDataProvider.DEFAULT_SUBREDDIT, "CryptoCurrency"
        )
        self.assertEqual(CryptoCurrencyRedditDataProvider.CODE, "RCC")
        self.assertEqual(BitcoinRedditDataProvider.DEFAULT_SUBREDDIT, "Bitcoin")
        self.assertEqual(BitcoinRedditDataProvider.CODE, "RBT")

    def test_feed_url_built_from_subreddit(self):
        dp = RedditDataProvider(subreddit="ethereum")
        self.assertEqual(dp.feed_url, "https://www.reddit.com/r/ethereum/.rss")
