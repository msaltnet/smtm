import base64
import hashlib
import hmac
import json
import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
from smtm.trader.okx_trader import OkxTrader
from smtm.trader.trader_factory import TraderFactory

TEST_OKX_ENV = {
    "OKX_API_ACCESS_KEY": "test_access_key",
    "OKX_API_SECRET_KEY": "test_secret_key",
    "OKX_API_PASSPHRASE": "test_passphrase",
    "OKX_API_SERVER_URL": "http://test_server",
}


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderScaffoldTest(unittest.TestCase):
    def test_currency_maps_to_inst_id_and_coin(self):
        trader = OkxTrader(budget=1000, currency="BTC")
        self.assertEqual(trader.market, "BTC-USDT")
        self.assertEqual(trader.market_currency, "BTC")

    def test_unsupported_currency_raises(self):
        with self.assertRaises(UserWarning):
            OkxTrader(currency="SOL")

    def test_supported_ord_types(self):
        self.assertEqual(
            OkxTrader(currency="BTC").SUPPORTED_ORD_TYPES,
            frozenset({"limit", "market"}),
        )

    def test_declares_passphrase_usage(self):
        self.assertTrue(OkxTrader.USES_PASSPHRASE)

    def test_passphrase_read_from_env(self):
        self.assertEqual(OkxTrader(currency="BTC").PASSPHRASE, "test_passphrase")

    def test_custom_passphrase_env_name(self):
        with patch.dict(os.environ, {"MY_OKX_PASS": "custom-pass"}):
            trader = OkxTrader(currency="BTC", passphrase_env="MY_OKX_PASS")
        self.assertEqual(trader.PASSPHRASE, "custom-pass")

    def test_timestamp_is_utc_iso8601_with_milliseconds(self):
        stamp = OkxTrader._timestamp()
        self.assertTrue(stamp.endswith("Z"))
        self.assertEqual(len(stamp), 24)  # 2026-07-25T09:08:57.715Z
        self.assertEqual(stamp[10], "T")
        self.assertEqual(stamp[19], ".")
        # local-time 구현(datetime.now() without tz)도 위 네 조건은 통과하지만
        # OKX는 그런 타임스탬프를 50102 Timestamp request expired로 거부한다.
        # 실제 UTC 시각과 몇 초 이내로 일치하는지까지 확인해 회귀를 막는다.
        parsed = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S.%fZ").replace(
            tzinfo=timezone.utc)
        now_utc = datetime.now(timezone.utc)
        self.assertLess(abs((now_utc - parsed).total_seconds()), 5)

    def test_signature_is_base64_hmac_sha256_of_prehash(self):
        trader = OkxTrader(currency="BTC")
        prehash = "2026-07-25T09:08:57.715ZGET/api/v5/trade/order?instId=BTC-USDT"
        expected = base64.b64encode(
            hmac.new(b"test_secret_key", prehash.encode(), hashlib.sha256).digest()
        ).decode()
        self.assertEqual(
            trader._create_signature(
                "2026-07-25T09:08:57.715Z", "GET",
                "/api/v5/trade/order?instId=BTC-USDT"),
            expected,
        )

    def test_signature_includes_body_for_post(self):
        trader = OkxTrader(currency="BTC")
        body = '{"instId": "BTC-USDT"}'
        prehash = "2026-07-25T09:08:57.715ZPOST/api/v5/trade/order" + body
        expected = base64.b64encode(
            hmac.new(b"test_secret_key", prehash.encode(), hashlib.sha256).digest()
        ).decode()
        self.assertEqual(
            trader._create_signature(
                "2026-07-25T09:08:57.715Z", "POST", "/api/v5/trade/order", body),
            expected,
        )

    def test_auth_headers_contain_all_four_okx_headers(self):
        trader = OkxTrader(currency="BTC")
        headers = trader._auth_headers("GET", "/api/v5/account/balance")
        self.assertEqual(headers["OK-ACCESS-KEY"], "test_access_key")
        self.assertEqual(headers["OK-ACCESS-PASSPHRASE"], "test_passphrase")
        self.assertEqual(headers["Content-Type"], "application/json")
        self.assertIn("OK-ACCESS-SIGN", headers)
        self.assertIn("OK-ACCESS-TIMESTAMP", headers)
        # 서명은 헤더에 실린 그 타임스탬프로 만들어져야 한다
        self.assertEqual(
            headers["OK-ACCESS-SIGN"],
            trader._create_signature(
                headers["OK-ACCESS-TIMESTAMP"], "GET", "/api/v5/account/balance"),
        )

    def test_no_demo_header_by_default(self):
        trader = OkxTrader(currency="BTC")
        self.assertFalse(trader.is_demo)
        self.assertNotIn("x-simulated-trading", trader._auth_headers("GET", "/x"))

    def test_demo_header_added_when_env_enabled(self):
        with patch.dict(os.environ, {"OKX_API_DEMO": "1"}):
            trader = OkxTrader(currency="BTC")
        self.assertTrue(trader.is_demo)
        self.assertEqual(
            trader._auth_headers("GET", "/x")["x-simulated-trading"], "1")

    def test_default_server_url_when_env_blank(self):
        with patch.dict(os.environ, {"OKX_API_SERVER_URL": ""}):
            trader = OkxTrader(currency="BTC")
        self.assertEqual(trader.SERVER_URL, "https://www.okx.com")

    def test_format_number_avoids_scientific_notation(self):
        self.assertEqual(OkxTrader._format_number(0.00005), "0.00005")
        self.assertEqual(OkxTrader._format_number(5000.0), "5000")
        self.assertEqual(OkxTrader._format_number(0), "0")


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderUnwrapTest(unittest.TestCase):
    def _trader(self):
        return OkxTrader(currency="BTC")

    def test_unwrap_returns_first_data_item_on_success(self):
        result = self._trader()._unwrap(
            {"code": "0", "msg": "", "data": [{"ordId": "42"}]})
        self.assertEqual(result, {"ordId": "42"})

    def test_unwrap_returns_none_for_none_response(self):
        self.assertIsNone(self._trader()._unwrap(None))

    def test_unwrap_returns_none_on_top_level_error_code(self):
        # 최상위 code!=0 — 구체적 사유는 data[0].sMsg에만 담긴다
        self.assertIsNone(self._trader()._unwrap({
            "code": "1", "msg": "",
            "data": [{"sCode": "51008", "sMsg": "Insufficient balance"}],
        }))

    def test_unwrap_returns_none_on_item_level_error_code(self):
        self.assertIsNone(self._trader()._unwrap({
            "code": "0", "msg": "",
            "data": [{"ordId": "", "sCode": "51000", "sMsg": "Parameter error"}],
        }))

    def test_unwrap_accepts_item_with_scode_zero(self):
        result = self._trader()._unwrap({
            "code": "0", "msg": "",
            "data": [{"ordId": "7", "sCode": "0", "sMsg": ""}],
        })
        self.assertEqual(result["ordId"], "7")

    def test_unwrap_returns_none_on_empty_data(self):
        self.assertIsNone(self._trader()._unwrap({"code": "0", "msg": "", "data": []}))


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderSignedRequestTest(unittest.TestCase):
    def test_signed_get_signs_the_exact_url_query_it_sends(self):
        trader = OkxTrader(currency="BTC")
        trader._request_get = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"state": "live"}]})
        trader._signed_get("/api/v5/trade/order",
                           {"instId": "BTC-USDT", "ordId": "42"})
        args, kwargs = trader._request_get.call_args
        url = args[0]
        # params= 로 넘기지 않고 URL에 직접 인코딩해야 서명과 일치한다
        self.assertIsNone(kwargs.get("params"))
        self.assertEqual(
            url, "http://test_server/api/v5/trade/order?instId=BTC-USDT&ordId=42")
        request_path = url[len("http://test_server"):]
        self.assertEqual(
            kwargs["headers"]["OK-ACCESS-SIGN"],
            trader._create_signature(
                kwargs["headers"]["OK-ACCESS-TIMESTAMP"], "GET", request_path),
        )

    def test_signed_post_signs_the_exact_body_it_sends(self):
        trader = OkxTrader(currency="BTC")
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "9"}]})
        trader._signed_post("/api/v5/trade/order", {"instId": "BTC-USDT"})
        args, kwargs = trader._request_post.call_args
        body = kwargs["data"]
        self.assertEqual(json.loads(body), {"instId": "BTC-USDT"})
        self.assertEqual(
            kwargs["headers"]["OK-ACCESS-SIGN"],
            trader._create_signature(
                kwargs["headers"]["OK-ACCESS-TIMESTAMP"], "POST",
                "/api/v5/trade/order", body),
        )

    def test_signed_request_blocked_without_passphrase(self):
        with patch.dict(os.environ, {"OKX_API_PASSPHRASE": ""}):
            trader = OkxTrader(currency="BTC")
        trader._request_post = MagicMock()
        trader._request_get = MagicMock()
        self.assertIsNone(trader._signed_post("/api/v5/trade/order", {"a": 1}))
        self.assertIsNone(trader._signed_get("/api/v5/trade/order", {"a": 1}))
        trader._request_post.assert_not_called()
        trader._request_get.assert_not_called()


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderAccountTest(unittest.TestCase):
    def test_get_trade_tick_calls_public_ticker_endpoint(self):
        trader = OkxTrader(currency="BTC")
        trader._request_get = MagicMock(return_value={
            "code": "0", "msg": "", "data": [{"instId": "BTC-USDT", "last": "50000.0"}],
        })
        result = trader.get_trade_tick()
        args, kwargs = trader._request_get.call_args
        self.assertIn("/api/v5/market/ticker", args[0])
        self.assertEqual(kwargs["params"], {"instId": "BTC-USDT"})
        self.assertEqual(result["last"], "50000.0")

    def test_get_account_info_returns_local_balance_and_live_quote(self):
        trader = OkxTrader(budget=1000, currency="BTC")
        trader.balance = 1000
        trader.asset = (50000, 0.02)
        trader.get_trade_tick = MagicMock(return_value={"last": "51000.0"})
        info = trader.get_account_info()
        self.assertEqual(info["balance"], 1000)
        self.assertEqual(info["asset"], {"BTC": (50000, 0.02)})
        self.assertEqual(info["quote"], {"BTC": 51000.0})
        self.assertIn("date_time", info)

    def test_get_account_info_survives_quote_failure(self):
        trader = OkxTrader(budget=1000, currency="BTC")
        trader.get_trade_tick = MagicMock(return_value=None)
        info = trader.get_account_info()
        self.assertEqual(info["quote"], {})


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderFactoryTest(unittest.TestCase):
    def test_factory_creates_okx_trader_for_okx(self):
        trader = TraderFactory.create("OKX", budget=1000, currency="BTC")
        self.assertIsInstance(trader, OkxTrader)
        trader.worker.stop()

    def test_factory_get_name_for_okx(self):
        self.assertEqual(TraderFactory.get_name("OKX"), "OKX")

    def test_factory_passes_passphrase_env_to_okx_trader(self):
        with patch.dict(os.environ, {
            "SMTM_KEY_7": "a", "SMTM_SECRET_7": "b", "SMTM_PASS_7": "custom-pass",
        }):
            trader = TraderFactory.create(
                "OKX", budget=1000, currency="BTC",
                account={"access_key_env": "SMTM_KEY_7",
                         "secret_key_env": "SMTM_SECRET_7",
                         "passphrase_env": "SMTM_PASS_7"})
        self.assertEqual(trader.ACCESS_KEY, "a")
        self.assertEqual(trader.SECRET_KEY, "b")
        self.assertEqual(trader.PASSPHRASE, "custom-pass")
        trader.worker.stop()


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderCancelTest(unittest.TestCase):
    def _trader_with_open_order(self):
        trader = OkxTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (0, 0)
        trader._start_timer = MagicMock()
        trader._stop_timer = MagicMock()
        cb = MagicMock()
        trader.order_map["ok"] = {
            "order_id": "444",
            "callback": cb,
            "result": {"state": "requested", "request": {"id": "ok"},
                       "type": "buy", "price": 50000, "amount": 0.1, "msg": "success"},
        }
        return trader, cb

    def test_query_order_uses_signed_get_with_inst_id_and_ord_id(self):
        trader, _ = self._trader_with_open_order()
        trader._signed_get = MagicMock(return_value={"state": "live"})
        trader._query_order("444")
        trader._signed_get.assert_called_once_with(
            "/api/v5/trade/order", {"instId": "BTC-USDT", "ordId": "444"})

    def test_cancel_order_uses_post_cancel_endpoint(self):
        trader, _ = self._trader_with_open_order()
        trader._signed_post = MagicMock(return_value={"ordId": "444", "sCode": "0"})
        trader._cancel_order("444")
        trader._signed_post.assert_called_once_with(
            "/api/v5/trade/cancel-order", {"instId": "BTC-USDT", "ordId": "444"})

    def test_fill_price_and_amount_handle_empty_strings(self):
        # 미체결 주문은 avgPx/accFillSz가 빈 문자열로 온다
        self.assertEqual(OkxTrader._fill_price({"avgPx": ""}), 0)
        self.assertEqual(OkxTrader._fill_amount({"accFillSz": ""}), 0)
        self.assertEqual(OkxTrader._fill_price({"avgPx": "50000.0"}), 50000.0)
        self.assertEqual(OkxTrader._fill_amount({"accFillSz": "0.1"}), 0.1)

    def test_cancel_request_requeries_because_cancel_response_lacks_fill_info(self):
        # OKX cancel-order 응답에는 accFillSz/avgPx가 없다 → 항상 재조회해야 한다
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value={"ordId": "444", "sCode": "0"})
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "canceled", "avgPx": "", "accFillSz": "0",
        })
        trader.cancel_request("ok")
        trader._cancel_order.assert_called_once_with("444")
        trader._query_order.assert_called_once_with("444")
        self.assertNotIn("ok", trader.order_map)
        self.assertEqual(cb.call_args[0][0]["state"], "done")

    def test_cancel_request_reports_fill_when_already_filled(self):
        # 취소 실패(이미 체결)여도 재조회로 체결 결과를 확정한다
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value=None)
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "filled", "avgPx": "50000.0", "accFillSz": "0.1",
        })
        trader.cancel_request("ok")
        done = cb.call_args[0][0]
        self.assertEqual(done["state"], "done")
        self.assertEqual(done["price"], 50000.0)
        self.assertEqual(done["amount"], 0.1)
        self.assertNotIn("ok", trader.order_map)

    def test_cancel_request_without_query_result_does_not_callback(self):
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value=None)
        trader._query_order = MagicMock(return_value=None)
        trader.cancel_request("ok")
        cb.assert_not_called()
        self.assertNotIn("ok", trader.order_map)

    def test_cancel_request_keeps_tracking_when_still_live_after_failed_cancel(self):
        # 취소 POST가 실패했는데 재조회 결과가 아직 live면 주문은 거래소에
        # 살아있는 것 — done 콜백을 쏘지 않고 order_map에 되돌려 폴링을 이어간다.
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value=None)
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "live", "avgPx": "", "accFillSz": "0",
        })
        trader.cancel_request("ok")
        cb.assert_not_called()
        self.assertIn("ok", trader.order_map)
        self.assertEqual(trader.order_map["ok"]["order_id"], "444")
        trader._start_timer.assert_called_once()

    def test_cancel_request_keeps_tracking_partial_fill_as_still_live(self):
        # 취소 시도 중 부분체결만 반영된 경우도 non-terminal이므로 콜백 없이
        # 계속 추적해야 한다 (체결분만 확정하고 나머지를 잃어버리면 안 된다).
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value=None)
        trader._query_order = MagicMock(return_value={
            "ordId": "444", "state": "partially_filled",
            "avgPx": "50000.0", "accFillSz": "0.05",
        })
        trader.cancel_request("ok")
        cb.assert_not_called()
        self.assertIn("ok", trader.order_map)
        trader._start_timer.assert_called_once()

    def test_cancel_unknown_id_is_noop(self):
        trader, _ = self._trader_with_open_order()
        trader._cancel_order = MagicMock()
        trader.cancel_request("does-not-exist")
        trader._cancel_order.assert_not_called()

    def test_cancel_all_requests_cancels_every_open_order(self):
        trader, _ = self._trader_with_open_order()
        trader.order_map["ok2"] = dict(trader.order_map["ok"], order_id="555")
        cancelled = []
        trader.cancel_request = lambda request_id: cancelled.append(request_id)
        trader.cancel_all_requests()
        self.assertEqual(sorted(cancelled), ["ok", "ok2"])


@patch.dict(os.environ, TEST_OKX_ENV)
class OkxTraderOrderTest(unittest.TestCase):
    def _trader(self):
        trader = OkxTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (50000, 1.0)
        trader._start_timer = MagicMock()
        return trader

    @staticmethod
    def _sent_payload(trader):
        return json.loads(trader._request_post.call_args[1]["data"])

    def test_limit_order_sends_px_and_sz_with_cash_mode(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "111", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "l1", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": MagicMock(),
        })
        payload = self._sent_payload(trader)
        self.assertEqual(payload["instId"], "BTC-USDT")
        self.assertEqual(payload["tdMode"], "cash")
        self.assertEqual(payload["side"], "buy")
        self.assertEqual(payload["ordType"], "limit")
        self.assertEqual(payload["px"], "50000")
        self.assertEqual(payload["sz"], "0.1")
        self.assertNotIn("tgtCcy", payload)
        self.assertIn("/api/v5/trade/order", trader._request_post.call_args[0][0])

    def test_market_buy_sends_quote_ccy_total(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "222", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "mb", "type": "buy", "price": 50000, "amount": 0.1,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        payload = self._sent_payload(trader)
        self.assertEqual(payload["ordType"], "market")
        self.assertEqual(payload["side"], "buy")
        self.assertEqual(payload["tgtCcy"], "quote_ccy")
        self.assertEqual(payload["sz"], "5000")  # price * amount
        self.assertNotIn("px", payload)

    def test_market_sell_sends_base_ccy_amount(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "333", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "ms", "type": "sell", "price": 0, "amount": 0.5,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        payload = self._sent_payload(trader)
        self.assertEqual(payload["ordType"], "market")
        self.assertEqual(payload["side"], "sell")
        self.assertEqual(payload["tgtCcy"], "base_ccy")
        self.assertEqual(payload["sz"], "0.5")
        self.assertNotIn("px", payload)

    def test_small_quantity_not_scientific_notation(self):
        trader = self._trader()
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "444", "sCode": "0"}]})
        trader._execute_order({
            "request": {"id": "sm", "type": "sell", "price": 0, "amount": 0.00005,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        body = trader._request_post.call_args[1]["data"]
        self.assertIn('"sz": "0.00005"', body)
        self.assertNotIn("e-", body)

    def test_limit_order_with_zero_price_is_noop(self):
        # price==0은 기존 hold 신호 — 지정가에서는 주문을 내지 않는다
        trader = self._trader()
        trader._request_post = MagicMock()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "z1", "type": "buy", "price": 0, "amount": 0.1},
            "callback": callback,
        })
        trader._request_post.assert_not_called()
        callback.assert_not_called()

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
        trader._request_post = MagicMock(
            return_value={"code": "0", "msg": "", "data": [{"ordId": "555", "sCode": "0"}]})
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "ok", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": callback,
        })
        self.assertEqual(trader.order_map["ok"]["order_id"], "555")
        callback.assert_called_once()
        self.assertEqual(callback.call_args[0][0]["state"], "requested")
        trader._start_timer.assert_called_once()

    def test_business_error_envelope_reports_error(self):
        # code=1 + sCode 로 오는 업무 오류는 주문 실패로 처리한다
        trader = self._trader()
        trader._request_post = MagicMock(return_value={
            "code": "1", "msg": "",
            "data": [{"ordId": "", "sCode": "51008", "sMsg": "Insufficient balance"}],
        })
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "e1", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": callback,
        })
        callback.assert_called_once_with("error!")
        self.assertNotIn("e1", trader.order_map)

    def test_cancel_type_request_delegates_to_cancel_request(self):
        trader = self._trader()
        trader.cancel_request = MagicMock()
        trader._execute_order({
            "request": {"id": "c1", "type": "cancel", "price": 0, "amount": 0},
            "callback": MagicMock(),
        })
        trader.cancel_request.assert_called_once_with("c1")
