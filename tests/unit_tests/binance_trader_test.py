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
class BinanceTraderAccountTest(unittest.TestCase):
    def test_get_trade_tick_calls_ticker_endpoint(self):
        trader = BinanceTrader(currency="BTC")
        trader._request_get = MagicMock(return_value={"symbol": "BTCUSDT", "price": "50000.0"})
        result = trader.get_trade_tick()
        args, kwargs = trader._request_get.call_args
        self.assertIn("/api/v3/ticker/price", args[0])
        self.assertEqual(kwargs["params"], {"symbol": "BTCUSDT"})
        self.assertEqual(result["price"], "50000.0")

    def test_get_account_info_returns_local_balance_and_live_quote(self):
        trader = BinanceTrader(budget=1000, currency="BTC")
        trader.balance = 1000
        trader.asset = (50000, 0.02)
        trader.get_trade_tick = MagicMock(return_value={"symbol": "BTCUSDT", "price": "51000.0"})
        info = trader.get_account_info()
        self.assertEqual(info["balance"], 1000)
        self.assertEqual(info["asset"], {"BTC": (50000, 0.02)})
        self.assertEqual(info["quote"], {"BTC": 51000.0})
        self.assertIn("date_time", info)


@patch.dict(os.environ, TEST_BINANCE_ENV)
class BinanceTraderFactoryTest(unittest.TestCase):
    def test_factory_creates_binance_trader_for_bnc(self):
        trader = TraderFactory.create("BNC", budget=1000, currency="BTC")
        self.assertIsInstance(trader, BinanceTrader)

    def test_factory_get_name_for_bnc(self):
        self.assertEqual(TraderFactory.get_name("BNC"), "Binance")


@patch.dict(os.environ, TEST_BINANCE_ENV)
class BinanceTraderOrderTest(unittest.TestCase):
    def _trader(self):
        trader = BinanceTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (50000, 1.0)
        trader._start_timer = MagicMock()
        return trader

    def test_limit_order_sends_price_and_quantity_gtc(self):
        trader = self._trader()
        trader._request_post = MagicMock(return_value={"orderId": 111})
        trader._execute_order({
            "request": {"id": "l1", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": MagicMock(),
        })
        # 서명된 쿼리스트링(bytes)로 전송됨 → 문자열로 디코드해 검증
        params = trader._request_post.call_args[1]["params"]
        qs = params.decode() if isinstance(params, (bytes, bytearray)) else params
        self.assertIn("type=LIMIT", qs)
        self.assertIn("timeInForce=GTC", qs)
        self.assertIn("price=50000", qs)
        self.assertIn("quantity=0.1", qs)
        self.assertIn("side=BUY", qs)

    def test_market_sell_sends_quantity(self):
        trader = self._trader()
        trader._request_post = MagicMock(return_value={"orderId": 222})
        trader._execute_order({
            "request": {"id": "ms", "type": "sell", "price": 0, "amount": 0.5,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        qs = trader._request_post.call_args[1]["params"]
        qs = qs.decode() if isinstance(qs, (bytes, bytearray)) else qs
        self.assertIn("type=MARKET", qs)
        self.assertIn("side=SELL", qs)
        self.assertIn("quantity=0.5", qs)
        self.assertNotIn("quoteOrderQty", qs)

    def test_market_buy_sends_quote_order_qty(self):
        trader = self._trader()
        trader._request_post = MagicMock(return_value={"orderId": 333})
        trader._execute_order({
            "request": {"id": "mb", "type": "buy", "price": 50000, "amount": 0.1,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        qs = trader._request_post.call_args[1]["params"]
        qs = qs.decode() if isinstance(qs, (bytes, bytearray)) else qs
        self.assertIn("type=MARKET", qs)
        self.assertIn("side=BUY", qs)
        # quoteOrderQty = price*amount = 5000
        self.assertIn("quoteOrderQty=5000", qs)
        self.assertNotIn("quantity=", qs)

    def test_unsupported_ord_type_rejected(self):
        trader = self._trader()
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "x", "type": "sell", "price": 0, "amount": 1,
                        "ord_type": "oco"},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        self.assertEqual(callback.call_args[0][0]["state"], "failed")

    def test_buy_rejected_when_balance_too_small(self):
        trader = self._trader()
        trader.balance = 100
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "b2", "type": "buy", "price": 50000, "amount": 1.0},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        callback.assert_called_once_with("error!")

    def test_sell_rejected_when_amount_exceeds_asset(self):
        trader = self._trader()
        trader.asset = (50000, 0.1)
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "s2", "type": "sell", "price": 50000, "amount": 1.0},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        callback.assert_called_once_with("error!")

    def test_successful_order_registers_and_callbacks(self):
        trader = self._trader()
        trader._request_post = MagicMock(return_value={"orderId": 444})
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "ok", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": callback,
        })
        self.assertEqual(trader.order_map["ok"]["order_id"], 444)
        callback.assert_called_once()
        trader._start_timer.assert_called_once()
