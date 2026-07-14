import os
import unittest
from unittest.mock import patch, MagicMock
from smtm.trader.binance_trader import BinanceTrader
from smtm.trader.trader_factory import TraderFactory

TEST_BINANCE_ENV = {
    "BINANCE_API_ACCESS_KEY": "test_access_key",
    "BINANCE_API_SECRET_KEY": "test_secret_key",
    "BINANCE_API_SERVER_URL": "http://test_server",
}


@patch.dict(os.environ, TEST_BINANCE_ENV)
class BinanceTraderScaffoldTest(unittest.TestCase):
    def test_currency_maps_to_symbol_and_coin(self):
        trader = BinanceTrader(budget=1000, currency="BTC")
        self.assertEqual(trader.market, "BTCUSDT")
        self.assertEqual(trader.market_currency, "BTC")

    def test_unsupported_currency_raises(self):
        with self.assertRaises(UserWarning):
            BinanceTrader(currency="SOL")

    def test_supported_ord_types(self):
        self.assertEqual(
            BinanceTrader(currency="BTC").SUPPORTED_ORD_TYPES,
            frozenset({"limit", "market"}),
        )

    def test_signature_is_deterministic_hmac_sha256(self):
        import hmac, hashlib
        trader = BinanceTrader(currency="BTC")
        query = "symbol=BTCUSDT&side=BUY&type=MARKET&quoteOrderQty=100&timestamp=1"
        expected = hmac.new(
            b"test_secret_key", query.encode(), hashlib.sha256
        ).hexdigest()
        self.assertEqual(trader._create_signature(query), expected)

    def test_signed_query_appends_timestamp_and_signature(self):
        trader = BinanceTrader(currency="BTC")
        qs = trader._signed_query({"symbol": "BTCUSDT", "side": "BUY"})
        self.assertIn("symbol=BTCUSDT", qs)
        self.assertIn("side=BUY", qs)
        self.assertIn("timestamp=", qs)
        self.assertIn("signature=", qs)

    def test_auth_headers(self):
        trader = BinanceTrader(currency="BTC")
        self.assertEqual(trader._auth_headers(), {"X-MBX-APIKEY": "test_access_key"})


@patch.dict(os.environ, TEST_BINANCE_ENV)
class BinanceTraderFactoryTest(unittest.TestCase):
    def test_factory_creates_binance_trader_for_bnc(self):
        trader = TraderFactory.create("BNC", budget=1000, currency="BTC")
        self.assertIsInstance(trader, BinanceTrader)

    def test_factory_get_name_for_bnc(self):
        self.assertEqual(TraderFactory.get_name("BNC"), "Binance")
