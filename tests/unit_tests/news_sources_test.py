import unittest
from unittest.mock import patch, MagicMock

from smtm import (
    CoinTelegraphNewsDataProvider,
    DecryptNewsDataProvider,
    CryptoSlateNewsDataProvider,
    BitcoinMagazineNewsDataProvider,
    TheBlockNewsDataProvider,
    WSJMarketsNewsDataProvider,
    MarketWatchNewsDataProvider,
    CNBCFinanceNewsDataProvider,
)


SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Sample Feed</title>
    <item>
      <title>Headline A</title>
      <link>https://example.com/a</link>
      <description>Body A</description>
      <pubDate>Mon, 20 Apr 2026 10:00:00 +0000</pubDate>
    </item>
  </channel>
</rss>
"""


class NewsSourcePresetTests(unittest.TestCase):
    def _assert_preset(self, cls, expected_url, expected_source, expected_code):
        self.assertEqual(cls.DEFAULT_URL, expected_url)
        self.assertEqual(cls.DEFAULT_SOURCE, expected_source)
        self.assertEqual(cls.CODE, expected_code)

    def test_presets_expose_expected_constants(self):
        self._assert_preset(
            CoinTelegraphNewsDataProvider,
            "https://cointelegraph.com/rss",
            "cointelegraph",
            "CTN",
        )
        self._assert_preset(
            DecryptNewsDataProvider,
            "https://decrypt.co/feed",
            "decrypt",
            "DCN",
        )
        self._assert_preset(
            CryptoSlateNewsDataProvider,
            "https://cryptoslate.com/feed/",
            "cryptoslate",
            "CSN",
        )
        self._assert_preset(
            BitcoinMagazineNewsDataProvider,
            "https://bitcoinmagazine.com/.rss/full/",
            "bitcoinmagazine",
            "BMN",
        )
        self._assert_preset(
            TheBlockNewsDataProvider,
            "https://www.theblock.co/rss.xml",
            "theblock",
            "TBN",
        )
        self._assert_preset(
            WSJMarketsNewsDataProvider,
            "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
            "wsj_markets",
            "WSJ",
        )
        self._assert_preset(
            MarketWatchNewsDataProvider,
            "http://feeds.marketwatch.com/marketwatch/topstories/",
            "marketwatch",
            "MWN",
        )
        self._assert_preset(
            CNBCFinanceNewsDataProvider,
            "https://www.cnbc.com/id/10000664/device/rss/rss.html",
            "cnbc_finance",
            "CNB",
        )

    @patch("requests.get")
    def test_cointelegraph_fetches_from_preset_url(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = CoinTelegraphNewsDataProvider()
        info = dp.get_info()

        mock_get.assert_called_once()
        self.assertEqual(mock_get.call_args.args[0], "https://cointelegraph.com/rss")
        self.assertEqual(len(info), 1)
        self.assertEqual(info[0]["type"], "news")
        self.assertEqual(info[0]["source"], "cointelegraph")
        self.assertEqual(info[0]["title"], "Headline A")

    @patch("requests.get")
    def test_decrypt_source_label_applied(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = DecryptNewsDataProvider()
        info = dp.get_info()

        self.assertEqual(info[0]["source"], "decrypt")

    @patch("requests.get")
    def test_cryptoslate_source_label_applied(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = CryptoSlateNewsDataProvider()
        info = dp.get_info()

        self.assertEqual(info[0]["source"], "cryptoslate")

    @patch("requests.get")
    def test_bitcoin_magazine_source_label_applied(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        dp = BitcoinMagazineNewsDataProvider()
        info = dp.get_info()

        self.assertEqual(info[0]["source"], "bitcoinmagazine")

    @patch("requests.get")
    def test_theblock_fetches_from_preset_url(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = TheBlockNewsDataProvider().get_info()

        self.assertEqual(mock_get.call_args.args[0], "https://www.theblock.co/rss.xml")
        self.assertEqual(info[0]["source"], "theblock")

    @patch("requests.get")
    def test_wsj_source_label_applied(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = WSJMarketsNewsDataProvider().get_info()

        self.assertEqual(info[0]["source"], "wsj_markets")

    @patch("requests.get")
    def test_marketwatch_source_label_applied(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = MarketWatchNewsDataProvider().get_info()

        self.assertEqual(info[0]["source"], "marketwatch")

    @patch("requests.get")
    def test_cnbc_finance_source_label_applied(self, mock_get):
        response = MagicMock()
        response.text = SAMPLE_RSS
        response.raise_for_status.return_value = None
        mock_get.return_value = response

        info = CNBCFinanceNewsDataProvider().get_info()

        self.assertEqual(info[0]["source"], "cnbc_finance")
