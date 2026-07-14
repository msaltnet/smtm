# BinanceTrader 구현 계획 — 하위 프로젝트 ②

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Binance 현물(spot) 주문 실행 Trader를 신규 구현해 `BNC` 거래소 코드로 실제 시장가/지정가 매매와 계좌 조회가 가능하게 한다.

**Architecture:** `BaseExchangeTrader`를 상속한 `BinanceTrader`가 Binance 현물 REST API(`/api/v3/*`)를 HMAC-SHA256 서명으로 호출한다. 기존 Upbit/Bithumb Trader와 동일한 수명주기(주문 등록 → `order_map` 추적 → 타이머 폴링으로 체결 확인 → 콜백)를 따르며, ①에서 만든 `order_spec` 역량 모델을 그대로 사용한다. 조건부/OCO 주문은 이 계획 범위 밖(③)이다.

**Tech Stack:** Python 3.9+, `requests`(기존), 표준 `hmac`/`hashlib`/`time`, `unittest`/`pytest`. 신규 외부 의존성 없음.

## Global Constraints

- **하위호환**: 기존 Trader/전략/파이프라인에 영향 금지. `BinanceTrader`는 신규 추가만.
- **역량 모델 사용**: `SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})` (조건부는 ③). 미지원 유형은 `order_spec.make_rejected_result`로 거부.
- **인터페이스 준수**: `Trader` 추상 메서드 시그니처(`send_request`, `cancel_request`, `cancel_all_requests`, `get_account_info`)를 그대로 구현/상속.
- **시장가 매수 계약**: Binance 시장가 매수는 `quoteOrderQty = price * amount`(USDT 총액). 시장가 매도는 `quantity = amount`(코인). 지정가는 `price` + `quantity = amount` + `timeInForce=GTC`.
- **예산/통화**: USDT 기준. 지원 통화 심볼은 `{"BTC":"BTCUSDT","ETH":"ETHUSDT","DOGE":"DOGEUSDT","XRP":"XRPUSDT"}` (BinanceDataProvider와 동일).
- **인증**: signed 엔드포인트는 쿼리스트링에 `timestamp`(ms) 추가 후 HMAC-SHA256(secret, query) 서명을 `signature`로 append, 헤더 `X-MBX-APIKEY: <access_key>`.
- **환경변수**: `BINANCE_API_ACCESS_KEY`, `BINANCE_API_SECRET_KEY`, `BINANCE_API_SERVER_URL`(기본 `https://api.binance.com`).
- **신규 의존성 추가 금지**. 테스트는 `unittest.TestCase`, 실행 `python -m pytest`. HTTP는 mock(`_request_get`/`_request_post`), 실 API는 통합 테스트 계층.

**범위 밖 (③):** stop/take-profit/OCO 네이티브 주문, 세션 손절/익절 정책, `price` 최적화(opt_mode)는 이 계획에서 적용하지 않음(생성자 인자는 받되 미사용).

---

## File Structure

- **Create** `smtm/trader/binance_trader.py` — `BinanceTrader` (상속 `BaseExchangeTrader`). 인증 서명, 주문 전송, 체결 폴링, 취소, 계좌/시세 조회.
- **Create** `tests/unit_tests/binance_trader_test.py` — 위 클래스 단위 테스트(HTTP mock).
- **Modify** `smtm/trader/trader_factory.py` — `TRADER_LIST`에 `BinanceTrader` 추가.
- **Modify** `smtm/trader/__init__.py` — `BinanceTrader` export(기존 Trader export 패턴 따름).
- **Modify** `tests/unit_tests/trader_factory_account_test.py` 또는 관련 팩토리 테스트 — `BNC` 코드가 `BinanceTrader`를 생성함을 검증(해당 테스트 파일이 없으면 factory 테스트에 케이스 추가).
- **Modify** `README.md`, `README-ko-kr.md` — Binance 환경변수 추가 및 거래소 표에서 `BNC`를 "Trader 구현"으로 갱신.

> `smtm/trader/__init__.py`에 기존 export가 어떻게 되어 있는지 먼저 확인하고 동일 패턴으로 추가할 것.

---

## Task 1: BinanceTrader 스캐폴드 + HMAC 인증 + 팩토리 등록

**Files:**
- Create: `smtm/trader/binance_trader.py`
- Modify: `smtm/trader/trader_factory.py`
- Modify: `smtm/trader/__init__.py`
- Test: `tests/unit_tests/binance_trader_test.py`

**Interfaces:**
- Consumes: `BaseExchangeTrader` (`smtm/trader/base_exchange_trader.py`), `order_spec` (`smtm/trader/order_spec.py`).
- Produces:
  - `class BinanceTrader(BaseExchangeTrader)` with `NAME="Binance"`, `CODE="BNC"`, `SUPPORTED_ORD_TYPES=frozenset({"limit","market"})`, `AVAILABLE_CURRENCY={"BTC":("BTCUSDT","BTC"),"ETH":("ETHUSDT","ETH"),"DOGE":("DOGEUSDT","DOGE"),"XRP":("XRPUSDT","XRP")}`
  - `__init__(self, budget=50000, currency="BTC", commission_ratio=0.001, opt_mode=True, access_key_env=None, secret_key_env=None)` → sets `self.market` (symbol e.g. "BTCUSDT"), `self.market_currency` (coin e.g. "BTC")
  - `_create_signature(self, query_string: str) -> str` — HMAC-SHA256 hex digest of `query_string` using `self.SECRET_KEY`
  - `_signed_query(self, params: dict) -> str` — urlencodes params + `timestamp`, appends `&signature=<sig>`, returns full query string
  - `_auth_headers(self) -> dict` — `{"X-MBX-APIKEY": self.ACCESS_KEY}`
  - `TraderFactory` returns `BinanceTrader` for code `"BNC"` (non-paper)

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/binance_trader_test.py`:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'smtm.trader.binance_trader'`

- [ ] **Step 3: 구현 — binance_trader.py 스캐폴드**

`smtm/trader/binance_trader.py`:
```python
import time
import hmac
import hashlib
from urllib.parse import urlencode
from .base_exchange_trader import BaseExchangeTrader
from . import order_spec


class BinanceTrader(BaseExchangeTrader):
    """
    바이낸스 현물(spot) 거래소를 통한 거래 요청 및 계좌 조회를 처리하는 Trader

    BinanceTrader processes spot trading requests and account inquiries via Binance.

    id: 요청 정보 id
    type: 거래 유형 buy, sell, cancel
    price: 거래 가격 (USDT)
    amount: 거래 수량 (코인)
    """

    AVAILABLE_CURRENCY = {
        "BTC": ("BTCUSDT", "BTC"),
        "ETH": ("ETHUSDT", "ETH"),
        "DOGE": ("DOGEUSDT", "DOGE"),
        "XRP": ("XRPUSDT", "XRP"),
    }
    NAME = "Binance"
    CODE = "BNC"
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})

    def __init__(
        self, budget=50000, currency="BTC", commission_ratio=0.001, opt_mode=True,
        access_key_env=None, secret_key_env=None,
    ):
        if currency not in self.AVAILABLE_CURRENCY:
            raise UserWarning(f"not supported currency: {currency}")

        super().__init__(
            budget=budget,
            currency=currency,
            commission_ratio=commission_ratio,
            opt_mode=opt_mode,
            logger_name="BinanceTrader",
            worker_name="BinanceTrader-Worker",
            env_key_names=(
                access_key_env or "BINANCE_API_ACCESS_KEY",
                secret_key_env or "BINANCE_API_SECRET_KEY",
                "BINANCE_API_SERVER_URL",
            ),
        )
        if not self.SERVER_URL:
            self.SERVER_URL = "https://api.binance.com"
        currency_info = self.AVAILABLE_CURRENCY[currency]
        self.market = currency_info[0]
        self.market_currency = currency_info[1]

    def _create_signature(self, query_string):
        return hmac.new(
            self.SECRET_KEY.encode(), query_string.encode(), hashlib.sha256
        ).hexdigest()

    def _signed_query(self, params):
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        query_string = urlencode(params)
        signature = self._create_signature(query_string)
        return f"{query_string}&signature={signature}"

    def _auth_headers(self):
        return {"X-MBX-APIKEY": self.ACCESS_KEY}
```

- [ ] **Step 4: 팩토리 등록**

`smtm/trader/trader_factory.py` 상단 import에 추가:
```python
from .binance_trader import BinanceTrader
```
`TRADER_LIST`에 추가:
```python
    TRADER_LIST = [
        UpbitTrader,
        BithumbTrader,
        BinanceTrader,
    ]
```

- [ ] **Step 5: __init__ export**

`smtm/trader/__init__.py`를 열어 기존 `UpbitTrader`/`BithumbTrader` export 패턴을 확인하고 동일하게 `BinanceTrader`를 추가한다. 예: 파일에 `from .upbit_trader import UpbitTrader` 형태가 있으면
```python
from .binance_trader import BinanceTrader
```
를 추가하고, `__all__`이 있으면 `"BinanceTrader"`를 목록에 추가.

- [ ] **Step 6: 통과 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py -v`
Expected: PASS (8 tests)

- [ ] **Step 7: 전체 스위트 회귀 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/ -q`
Expected: 기존 + 신규 전부 PASS

```bash
git add smtm/trader/binance_trader.py smtm/trader/trader_factory.py smtm/trader/__init__.py tests/unit_tests/binance_trader_test.py
git commit -m "[feat] add BinanceTrader scaffold with HMAC auth and factory registration"
```

---

## Task 2: 시세 조회 + 계좌 정보

**Files:**
- Modify: `smtm/trader/binance_trader.py`
- Test: `tests/unit_tests/binance_trader_test.py`

**Interfaces:**
- Consumes: `BaseExchangeTrader._request_get`, `self.market`, `self.market_currency`, `self.balance`, `self.asset`, `self.ISO_DATEFORMAT`, `self._validate_credentials`.
- Produces:
  - `get_trade_tick(self) -> dict | None` — GET `/api/v3/ticker/price?symbol=<market>`; 반환 예 `{"symbol":"BTCUSDT","price":"50000.0"}`
  - `get_account_info(self) -> dict` — `{"balance", "asset": {coin: (avg, amount)}, "quote": {coin: price}, "date_time"}` (로컬 잔고/자산 + 실시간 시세, Upbit 패턴)

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/binance_trader_test.py`에 추가:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py::BinanceTraderAccountTest -v`
Expected: FAIL — `AttributeError: 'BinanceTrader' object has no attribute 'get_trade_tick'`

- [ ] **Step 3: 구현**

`smtm/trader/binance_trader.py`에 메서드 추가:
```python
    def get_trade_tick(self):
        """최근 체결가(현재가) 조회 — public 엔드포인트"""
        return self._request_get(
            self.SERVER_URL + "/api/v3/ticker/price",
            params={"symbol": self.market},
        )

    def get_account_info(self):
        """계좌 정보를 요청한다 (로컬 잔고/자산 + 실시간 시세)

        Returns:
            {
                balance: 계좌 현금 잔고 (USDT)
                asset: {코인: (평균 매입가, 수량)}
                quote: {코인: 현재가}
                date_time: 현재 시간
            }
        """
        from datetime import datetime

        result = {
            "balance": self.balance,
            "asset": {self.market_currency: self.asset},
            "quote": {},
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        trade_info = self.get_trade_tick()
        if trade_info is not None and "price" in trade_info:
            result["quote"][self.market_currency] = float(trade_info["price"])
        else:
            self.logger.error("fail query quote")
        self.logger.debug(f"account info {result}")
        return result
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py -v`
Expected: PASS (신규 2개 포함)

- [ ] **Step 5: 커밋**

```bash
git add smtm/trader/binance_trader.py tests/unit_tests/binance_trader_test.py
git commit -m "[feat] BinanceTrader account info and ticker query"
```

---

## Task 3: 주문 전송 (지정가/시장가) + 실행 라우팅 + 역량 가드

**Files:**
- Modify: `smtm/trader/binance_trader.py`
- Test: `tests/unit_tests/binance_trader_test.py`

**Interfaces:**
- Consumes: `order_spec.get_ord_type`, `order_spec.MARKET`, `order_spec.make_rejected_result`; `BaseExchangeTrader._request_post`, `_create_success_result`, `_start_timer`, `self.order_map`, `self.balance`, `self.asset`.
- Produces:
  - `_send_order(self, side, ord_type, price, amount) -> dict | None` — signed POST `/api/v3/order`. LIMIT: `{symbol, side, type:"LIMIT", timeInForce:"GTC", quantity, price}`; MARKET SELL: `{symbol, side:"SELL", type:"MARKET", quantity}`; MARKET BUY: `{symbol, side:"BUY", type:"MARKET", quoteOrderQty}`. 반환: 응답 dict(포함 `orderId`).
  - `_execute_order(self, task)` — cancel/역량거부/잔고·수량 가드/라우팅/`order_map` 등록/`"requested"` 콜백/타이머 시작 (Upbit 패턴). `side`는 `"BUY"`/`"SELL"`.

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/binance_trader_test.py`에 추가:
```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py::BinanceTraderOrderTest -v`
Expected: FAIL — `_execute_order`/`_send_order` 미구현.

- [ ] **Step 3: 구현**

`smtm/trader/binance_trader.py`에 추가:
```python
    def _execute_order(self, task):
        request = task["request"]
        if request["type"] == "cancel":
            self.cancel_request(request["id"])
            return

        ord_type = order_spec.get_ord_type(request)
        if ord_type not in self.SUPPORTED_ORD_TYPES:
            task["callback"](order_spec.make_rejected_result(
                request, f"unsupported ord_type: {ord_type}"))
            return

        is_buy = request["type"] == "buy"
        is_market = ord_type == order_spec.MARKET

        if not is_market and request["price"] == 0:
            # price==0 은 기존 no-op(hold) 신호 — 지정가에서는 무시
            self.logger.warning("[REJECT] limit order requires price")
            return

        if is_buy and float(request["price"]) * float(request["amount"]) > self.balance:
            self.logger.warning(
                f"[REJECT] balance is too small! "
                f"{float(request['price']) * float(request['amount'])} > {self.balance}"
            )
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                f"[REJECT] invalid amount {float(request['amount'])} > {self.asset[1]}"
            )
            task["callback"]("error!")
            return

        side = "BUY" if is_buy else "SELL"
        response = self._send_order(
            side, ord_type, request["price"], request["amount"])
        if response is None or "orderId" not in response:
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.order_map[request["id"]] = {
            "order_id": response["orderId"],
            "callback": task["callback"],
            "result": result,
        }
        task["callback"](result)
        self.logger.debug(f"request inserted {self.order_map[request['id']]}")
        self._start_timer()

    def _send_order(self, side, ord_type, price, amount):
        """Binance 현물 주문 전송 (signed POST /api/v3/order)

        - 지정가:      type=LIMIT, timeInForce=GTC, quantity, price
        - 시장가 매도:  type=MARKET, quantity
        - 시장가 매수:  type=MARKET, quoteOrderQty(=price*amount, USDT 총액)
        """
        if not self._validate_credentials():
            return None

        params = {"symbol": self.market, "side": side}
        if ord_type == order_spec.MARKET and side == "BUY":
            params["type"] = "MARKET"
            params["quoteOrderQty"] = float(price) * float(amount)
        elif ord_type == order_spec.MARKET:
            params["type"] = "MARKET"
            params["quantity"] = float(amount)
        else:
            params["type"] = "LIMIT"
            params["timeInForce"] = "GTC"
            params["quantity"] = float(amount)
            params["price"] = float(price)

        self.logger.info(f"ORDER ##### {side} {params['type']}")
        self.logger.info(f"{self.market}, params: {params}")

        query_string = self._signed_query(params).encode()
        return self._request_post(
            self.SERVER_URL + "/api/v3/order",
            params=query_string,
            headers=self._auth_headers(),
        )
```

> 참고: `_request_post(url, headers=None, params=None, data=None)`는 `params`를 `requests.post`의 `params`로 전달한다. bytes 쿼리스트링을 그대로 넘기면 서명이 보존된다(Upbit와 동일 패턴).

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py -v`
Expected: PASS (신규 7개 포함)

- [ ] **Step 5: 커밋**

```bash
git add smtm/trader/binance_trader.py tests/unit_tests/binance_trader_test.py
git commit -m "[feat] BinanceTrader places limit/market orders with capability guard"
```

---

## Task 4: 체결 폴링 + 주문 취소

**Files:**
- Modify: `smtm/trader/binance_trader.py`
- Test: `tests/unit_tests/binance_trader_test.py`

**Interfaces:**
- Consumes: `BaseExchangeTrader._request_get`, `_request_post`(취소는 DELETE → `requests.delete` 직접 사용), `_call_callback`, `_start_timer`, `_stop_timer`, `self.order_map`, `self.commission_ratio`.
- Produces:
  - `_query_order(self, order_id) -> dict | None` — signed GET `/api/v3/order` (`symbol`, `orderId`). 반환 예 `{"orderId":..,"status":"FILLED","price":"50000.0","executedQty":"0.1","cummulativeQuoteQty":"5000.0"}`
  - `_update_order_result(self, task)` — `order_map` 순회, `status=="FILLED"`이면 결과 갱신 후 `_call_callback(done)`, 미체결은 유지, 타이머 재조정 (Upbit 패턴)
  - `cancel_request(self, request_id)` — `order_map`에서 제거 후 `_cancel_order` 호출, done 콜백
  - `_cancel_order(self, order_id) -> dict | None` — signed DELETE `/api/v3/order`

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/binance_trader_test.py`에 추가:
```python
@patch.dict(os.environ, TEST_BINANCE_ENV)
class BinanceTraderPollingTest(unittest.TestCase):
    def _trader_with_open_order(self):
        trader = BinanceTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (0, 0)
        trader._start_timer = MagicMock()
        trader._stop_timer = MagicMock()
        cb = MagicMock()
        trader.order_map["ok"] = {
            "order_id": 444,
            "callback": cb,
            "result": {"state": "requested", "request": {"id": "ok"},
                       "type": "buy", "price": 50000, "amount": 0.1, "msg": "success"},
        }
        return trader, cb

    def test_filled_order_triggers_done_callback_and_clears_map(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "orderId": 444, "status": "FILLED", "price": "50000.0",
            "executedQty": "0.1", "cummulativeQuoteQty": "5000.0",
        })
        trader._update_order_result(None)
        done = cb.call_args[0][0]
        self.assertEqual(done["state"], "done")
        self.assertEqual(done["amount"], 0.1)
        self.assertNotIn("ok", trader.order_map)

    def test_unfilled_order_stays_in_map(self):
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "orderId": 444, "status": "NEW", "price": "50000.0",
            "executedQty": "0.0", "cummulativeQuoteQty": "0.0",
        })
        trader._update_order_result(None)
        self.assertIn("ok", trader.order_map)

    def test_market_buy_fill_derives_price_from_quote(self):
        # 시장가 주문은 price가 0으로 오므로 체결총액/체결수량으로 평단 산출
        trader, cb = self._trader_with_open_order()
        trader._query_order = MagicMock(return_value={
            "orderId": 444, "status": "FILLED", "price": "0.0",
            "executedQty": "0.1", "cummulativeQuoteQty": "5000.0",
        })
        trader._update_order_result(None)
        done = cb.call_args[0][0]
        self.assertEqual(done["price"], 50000.0)  # 5000 / 0.1

    def test_cancel_request_calls_delete_and_removes_order(self):
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock(return_value={"orderId": 444, "status": "CANCELED"})
        trader.cancel_request("ok")
        trader._cancel_order.assert_called_once_with(444)
        self.assertNotIn("ok", trader.order_map)

    def test_cancel_unknown_id_is_noop(self):
        trader, cb = self._trader_with_open_order()
        trader._cancel_order = MagicMock()
        trader.cancel_request("does-not-exist")
        trader._cancel_order.assert_not_called()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py::BinanceTraderPollingTest -v`
Expected: FAIL — `_query_order`/`_update_order_result`/`cancel_request`/`_cancel_order` 미구현.

- [ ] **Step 3: 구현**

`smtm/trader/binance_trader.py` 상단 import에 추가:
```python
import requests
from ..http_session import request_with_retry
```

메서드 추가:
```python
    def _query_order(self, order_id):
        """주문 상태 조회 (signed GET /api/v3/order)"""
        if not self._validate_credentials():
            return None
        query_string = self._signed_query(
            {"symbol": self.market, "orderId": order_id}).encode()
        return self._request_get(
            self.SERVER_URL + "/api/v3/order",
            params=query_string,
            headers=self._auth_headers(),
        )

    def _update_order_result(self, task):
        del task
        waiting_request = {}
        self.logger.debug(f"waiting order count {len(self.order_map)}")
        for request_id, order in self.order_map.items():
            response = self._query_order(order["order_id"])
            if response is None:
                waiting_request[request_id] = order
                continue
            if response.get("status") == "FILLED":
                from datetime import datetime

                result = order["result"]
                result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
                result["price"] = self._fill_price(response)
                result["amount"] = float(response.get("executedQty", 0))
                result["state"] = "done"
                self._call_callback(order["callback"], result)
            else:
                waiting_request[request_id] = order

        self.order_map = waiting_request
        self.logger.debug(f"After update, waiting order count {len(self.order_map)}")
        self._stop_timer()
        if len(self.order_map) > 0:
            self._start_timer()

    @staticmethod
    def _fill_price(response):
        """체결 단가. 시장가 주문은 price가 0으로 오므로
        체결총액(cummulativeQuoteQty)/체결수량(executedQty)으로 평단을 산출한다."""
        price = float(response["price"]) if response.get("price") else 0
        if price > 0:
            return price
        executed = float(response.get("executedQty", 0))
        quote = float(response.get("cummulativeQuoteQty", 0))
        return quote / executed if executed else 0

    def cancel_request(self, request_id):
        """거래 요청을 취소한다"""
        if request_id not in self.order_map:
            self.logger.debug(f"already canceled or unknown: {request_id}")
            return

        order = self.order_map[request_id]
        del self.order_map[request_id]
        result = order["result"]
        response = self._cancel_order(order["order_id"])

        if response is None:
            # 이미 체결됐을 수 있으므로 조회로 확정
            response = self._query_order(order["order_id"])
            if response is None:
                return

        from datetime import datetime

        result["date_time"] = datetime.now().strftime(self.ISO_DATEFORMAT)
        result["price"] = self._fill_price(response)
        result["amount"] = float(response.get("executedQty", 0))
        result["state"] = "done"
        self._call_callback(order["callback"], result)

    def _cancel_order(self, order_id):
        """주문 취소 (signed DELETE /api/v3/order)"""
        if not self._validate_credentials():
            return None
        query_string = self._signed_query(
            {"symbol": self.market, "orderId": order_id}).encode()
        try:
            response = request_with_retry(
                requests.delete,
                self.SERVER_URL + "/api/v3/order",
                params=query_string,
                headers=self._auth_headers(),
            )
            response.raise_for_status()
            return response.json()
        except (ValueError, requests.exceptions.RequestException) as err:
            self.logger.error(f"cancel order fail: {err}")
            return None
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/binance_trader_test.py -v`
Expected: PASS (신규 4개 포함, 파일 전체 GREEN)

- [ ] **Step 5: 전체 회귀 후 커밋**

Run: `python -m pytest tests/unit_tests/ -q`
Expected: 전부 PASS

```bash
git add smtm/trader/binance_trader.py tests/unit_tests/binance_trader_test.py
git commit -m "[feat] BinanceTrader order status polling and cancellation"
```

---

## Task 5: 문서 갱신 (환경변수 + 거래소 표)

**Files:**
- Modify: `README.md`
- Modify: `README-ko-kr.md`

**Interfaces:** 없음(문서만).

- [ ] **Step 1: 환경변수 섹션 추가**

`README-ko-kr.md`의 환경변수 예시 블록에서 Bithumb 항목 다음에 Binance를 추가:
```bash
# Binance 거래소 (거래소 코드 BNC)
BINANCE_API_ACCESS_KEY=your_binance_access_key
BINANCE_API_SECRET_KEY=your_binance_secret_key
BINANCE_API_SERVER_URL=https://api.binance.com
```
`README.md`(영문)에도 동일하게 대응 항목 추가.

- [ ] **Step 2: 거래소 표 갱신**

`README-ko-kr.md`의 지원 거래소 표에서 `BNC` 행을 갱신:
```
| `BNC` | Binance | Binance | 현물(spot) 매매 지원, 예산은 USDT 기준 |
```
(기존 "데이터만 지원, Trader 미구현" → 위와 같이 변경). `README.md`의 대응 표도 동일하게 갱신.

- [ ] **Step 3: 커밋**

```bash
git add README.md README-ko-kr.md
git commit -m "[docs] document Binance trading support (BNC) and env vars"
```

---

## 최종 검증

- [ ] **전체 단위 테스트**

Run: `python -m pytest tests/unit_tests/ -q`
Expected: 전부 PASS

- [ ] **E2E 회귀**

Run: `python -m pytest tests/e2e_tests/ -q`
Expected: 전부 PASS (BinanceTrader 추가가 기존 흐름에 영향 없음)

---

## Self-Review 결과 (작성자 체크)

- **Spec 커버리지 (§5.3, §6 ②)**: HMAC 인증=Task1, USDT 마켓/통화 매핑=Task1, 팩토리 등록=Task1, 계좌/시세=Task2, 시장가/지정가 주문=Task3, 체결 확인·취소=Task4, 문서=Task5. ✅
- **§10 이슈 반영**: 이슈 #2(시장가 매수 의미)를 quoteOrderQty(=price*amount, USDT 총액)로 확정·문서화(Global Constraints + Task3). 이슈 #1/#3/#4는 조건부/producer 관련이라 ③ 범위 — ②에서 조건부 주문을 지원하지 않으므로 발생하지 않음. ✅
- **Placeholder 스캔**: 모든 코드 스텝에 완전한 코드 포함. TBD/TODO 없음. ✅
- **타입 일관성**: `_create_signature`/`_signed_query`/`_auth_headers`/`_send_order(side, ord_type, price, amount)`/`_query_order`/`_cancel_order` 이름·시그니처가 전 태스크에서 일관. `order_map` 항목 키(`order_id`,`callback`,`result`)는 Bithumb 패턴과 동일. ✅
- **주의(구현자 확인 필요)**:
  - `smtm/trader/__init__.py`의 기존 export 형식을 먼저 확인 후 동일 패턴으로 추가(Task1 Step5).
  - Binance API 엔드포인트/파라미터(`quoteOrderQty`, `timeInForce`, `/api/v3/order` 응답 필드 `status/price/executedQty/cummulativeQuoteQty`)는 단위 테스트에서 mock으로만 검증됨. 실제 계정/서명/체결은 `tests/integration_tests/`에서 Binance **testnet**(`https://testnet.binance.vision`)로 확인 권장.
  - `_call_callback`(base)는 `result["price"]*result["amount"]`로 잔고/자산을 갱신한다. 시장가 주문은 `_query_order`의 `price`가 0으로 오므로 Task4의 `_fill_price`가 `cummulativeQuoteQty/executedQty`로 평단을 산출해 이 계산을 정확히 유지한다(전용 테스트 `test_market_buy_fill_derives_price_from_quote`로 검증).
  - 부분 체결(partial fill) 정합성(잔여 수량 재주문/누적)은 이 계획 범위 밖 — 현재는 FILLED만 done 처리하고 그 외는 대기 유지. 필요 시 후속 개선.
