# 주문 유형 기반(Foundation) 구현 계획 — 하위 프로젝트 ①

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 주문 유형 확장의 거래소-무관 공통 기반을 구축한다 — 요청 스키마 additive 확장, 거래소 역량 모델, SafetyGuard 조건부 금액 계산, SimulationTrader 시장가/조건부(손절·익절) 에뮬레이션, Upbit/Bithumb 시장가 활성화.

**Architecture:** 신규 `order_spec` 모듈이 `ord_type` 상수와 헬퍼를 제공한다. 각 Trader는 `SUPPORTED_ORD_TYPES`로 역량을 선언하고, 미지원 유형은 오실행 대신 실패 결과로 거부한다. SimulationTrader는 조건부 주문을 로컬 보관 후 `update_quote` 시 트리거를 검사해 발동한다. 기존 요청(신규 필드 없음)은 전 구간에서 오늘과 100% 동일하게 동작한다.

**Tech Stack:** Python 3.9+, 표준 라이브러리 + `unittest`/`pytest`. 신규 외부 의존성 없음.

## Global Constraints

- **하위호환 최우선**: 신규 필드(`ord_type`/`trigger`)가 없는 요청은 기존과 동일하게 동작해야 한다.
- **인터페이스 시그니처 불변**: `Trader.send_request(request_list, callback)`, `Trader.cancel_request(request_id)`, `SafetyGuard.check_request(request)` 시그니처 변경 금지.
- **`price == 0`은 no-op(hold) 신호로 보존**: 시장가로 재해석 금지. 시장가는 `ord_type == "market"`로만.
- **`request["price"]`/`request["amount"]` 키 유지**: `BaseExchangeTrader._create_success_result`가 직접 참조하므로 삭제 금지.
- **신규 의존성 추가 금지** (`requirements.txt` 불변).
- **콜백 계약**: 결과는 dict. 실패 시 `{"state": "failed", "msg": ...}` dict를 콜백에 전달(문자열 아님).
- 테스트는 `unittest.TestCase` 스타일, 실행은 `python -m pytest`.

**본 계획 범위 밖 (하위 프로젝트 ②/③):** BinanceTrader, OCO 에뮬레이션, 세션 손절/익절 정책 producer, `ConditionalOrderManager`(비-sim 거래소 로컬 감시). ①은 stop_loss/take_profit **단일 다리** 조건부까지만 다룬다.

---

## File Structure

- **Create** `smtm/trader/order_spec.py` — `ord_type` 상수, `get_ord_type`, `is_conditional`, `make_rejected_result`.
- **Create** `tests/unit_tests/order_spec_test.py` — 위 모듈 단위 테스트.
- **Modify** `smtm/trader/trader.py` — 추상 `Trader`에 `SUPPORTED_ORD_TYPES = frozenset({"limit"})` 기본값 추가.
- **Modify** `smtm/llm/safety_guard.py` — `check_request`의 거래금액 계산을 `ord_type` 인지형으로 확장.
- **Modify** `tests/unit_tests/safety_guard_test.py` — 조건부 금액 계산 테스트 추가.
- **Modify** `smtm/trader/simulation_trader.py` — 역량 선언 + 미지원 거부 + 조건부 등록/발동/취소.
- **Modify** `tests/unit_tests/simulation_trader_test.py` — 시장가/역량/조건부 테스트 추가.
- **Modify** `smtm/trader/upbit_trader.py` — 시장가 활성화 + 역량 선언.
- **Modify** `tests/unit_tests/upbit_trader_test.py` — 시장가 라우팅/거부 테스트 추가.
- **Modify** `smtm/trader/bithumb_trader.py` — 시장가 주문 메서드 + 활성화 + 역량 선언.
- **Modify** `tests/unit_tests/bithumb_trader_test.py` — 시장가 라우팅/거부 테스트 추가.

---

## Task 1: order_spec 모듈 + 역량 모델 기본값

**Files:**
- Create: `smtm/trader/order_spec.py`
- Modify: `smtm/trader/trader.py` (추상 `Trader`에 클래스 속성 추가)
- Test: `tests/unit_tests/order_spec_test.py`

**Interfaces:**
- Produces:
  - 상수: `LIMIT="limit"`, `MARKET="market"`, `STOP_LOSS="stop_loss"`, `TAKE_PROFIT="take_profit"`, `OCO="oco"`
  - `CONDITIONAL_ORD_TYPES: frozenset` = {STOP_LOSS, TAKE_PROFIT, OCO}
  - `get_ord_type(request: dict) -> str` — 없거나 falsy면 `"limit"`
  - `is_conditional(request: dict) -> bool`
  - `make_rejected_result(request: dict, reason: str) -> dict` — `{"request","type","price":0,"amount":0,"msg":reason,"state":"failed"}`
  - `Trader.SUPPORTED_ORD_TYPES: frozenset` 기본값 `{"limit"}`

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/order_spec_test.py`:
```python
import unittest

from smtm.trader import order_spec
from smtm.trader.trader import Trader


class OrderSpecTest(unittest.TestCase):
    def test_get_ord_type_defaults_to_limit_when_absent(self):
        self.assertEqual(order_spec.get_ord_type({"type": "buy"}), "limit")

    def test_get_ord_type_defaults_to_limit_when_none(self):
        self.assertEqual(order_spec.get_ord_type({"ord_type": None}), "limit")

    def test_get_ord_type_returns_declared_value(self):
        self.assertEqual(order_spec.get_ord_type({"ord_type": "market"}), "market")

    def test_is_conditional_true_for_stop_loss(self):
        self.assertTrue(order_spec.is_conditional({"ord_type": "stop_loss"}))

    def test_is_conditional_false_for_limit(self):
        self.assertFalse(order_spec.is_conditional({"type": "buy"}))

    def test_make_rejected_result_shape(self):
        req = {"id": "1", "type": "buy", "price": 100, "amount": 2}
        result = order_spec.make_rejected_result(req, "unsupported ord_type: oco")
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["msg"], "unsupported ord_type: oco")
        self.assertEqual(result["price"], 0)
        self.assertEqual(result["amount"], 0)
        self.assertEqual(result["type"], "buy")
        self.assertIs(result["request"], req)

    def test_base_trader_supports_limit_only_by_default(self):
        self.assertEqual(Trader.SUPPORTED_ORD_TYPES, frozenset({"limit"}))
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/order_spec_test.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'smtm.trader.order_spec'`

- [ ] **Step 3: 모듈 구현**

`smtm/trader/order_spec.py`:
```python
"""주문 유형(ord_type) 상수와 요청 헬퍼.

기존 요청 스키마 {id, type, price, amount, date_time}에 additive로 얹는
선택 필드 `ord_type` / `trigger` 를 일관되게 다루기 위한 공용 모듈.
"""

LIMIT = "limit"
MARKET = "market"
STOP_LOSS = "stop_loss"
TAKE_PROFIT = "take_profit"
OCO = "oco"

CONDITIONAL_ORD_TYPES = frozenset({STOP_LOSS, TAKE_PROFIT, OCO})


def get_ord_type(request):
    """요청의 ord_type을 반환. 없거나 falsy면 'limit'(기존 동작)."""
    return request.get("ord_type") or LIMIT


def is_conditional(request):
    """조건부 주문(stop_loss/take_profit/oco) 여부."""
    return get_ord_type(request) in CONDITIONAL_ORD_TYPES


def make_rejected_result(request, reason):
    """콜백에 전달할 표준 실패 결과 dict."""
    return {
        "request": request,
        "type": request.get("type"),
        "price": 0,
        "amount": 0,
        "msg": reason,
        "state": "failed",
    }
```

- [ ] **Step 4: 역량 기본값 추가**

`smtm/trader/trader.py`의 `class Trader(metaclass=ABCMeta):` 본문 맨 위(docstring 다음)에 클래스 속성 추가:
```python
class Trader(metaclass=ABCMeta):
    """
    거래 요청과 계좌 정보 요청을 처리하는 Trader 추상클래스

    Abstract class for processing trading requests and account information requests
    """

    #: 이 Trader가 지원하는 ord_type 집합. 하위호환 기본값은 지정가만.
    SUPPORTED_ORD_TYPES = frozenset({"limit"})
```

- [ ] **Step 5: 통과 확인**

Run: `python -m pytest tests/unit_tests/order_spec_test.py -v`
Expected: PASS (7 tests)

- [ ] **Step 6: 커밋**

```bash
git add smtm/trader/order_spec.py smtm/trader/trader.py tests/unit_tests/order_spec_test.py
git commit -m "[feat] add order_spec helpers and Trader capability default"
```

---

## Task 2: SafetyGuard 조건부 거래금액 계산

**Files:**
- Modify: `smtm/llm/safety_guard.py` (`check_request` / 신규 `_trade_amount`)
- Test: `tests/unit_tests/safety_guard_test.py`

**Interfaces:**
- Consumes: `order_spec.get_ord_type`, `order_spec.STOP_LOSS`, `order_spec.TAKE_PROFIT`
- Produces: `SafetyGuard.check_request(request)` — 시그니처 불변. stop_loss/take_profit는 `trigger * amount`를, 그 외는 `price * amount`를 한도에 적용.

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/safety_guard_test.py`의 `SafetyGuardCheckRequestTests` 클래스 안에 추가:
```python
    def test_stop_loss_uses_trigger_for_amount(self):
        # trigger 48000 * amount 1 = 48000 <= max_trade_amount(100000) → 허용
        req = {"id": "s1", "type": "sell", "price": 0, "amount": 1.0,
               "ord_type": "stop_loss", "trigger": 48000,
               "date_time": "2026-07-03T12:00:00"}
        self.assertTrue(self.guard.check_request(req).allowed)

    def test_stop_loss_blocked_when_trigger_amount_exceeds_limit(self):
        # trigger 200000 * amount 1 = 200000 > 100000 → 차단
        req = {"id": "s2", "type": "sell", "price": 0, "amount": 1.0,
               "ord_type": "stop_loss", "trigger": 200000,
               "date_time": "2026-07-03T12:00:00"}
        self.assertFalse(self.guard.check_request(req).allowed)

    def test_take_profit_uses_trigger_for_amount(self):
        req = {"id": "t1", "type": "sell", "price": 0, "amount": 1.0,
               "ord_type": "take_profit", "trigger": 55000,
               "date_time": "2026-07-03T12:00:00"}
        self.assertTrue(self.guard.check_request(req).allowed)

    def test_legacy_limit_request_still_uses_price(self):
        # 신규 필드 없는 기존 요청은 price*amount 그대로 (회귀 방지)
        req = {"id": "l1", "type": "buy", "price": 50000, "amount": 1.0,
               "date_time": "2026-07-03T12:00:00"}
        self.assertTrue(self.guard.check_request(req).allowed)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/safety_guard_test.py -v`
Expected: FAIL — `test_stop_loss_blocked_when_trigger_amount_exceeds_limit`가 통과되어야 하는데 현재는 `price(0)*amount(1)=0`으로 계산되어 차단되지 않음 → assertion 실패.

- [ ] **Step 3: 구현**

`smtm/llm/safety_guard.py`의 `check_request`를 아래로 교체하고 `_trade_amount`를 추가:
```python
    def check_request(self, request: dict) -> SafetyResult:
        """거래 요청(request dict) 사전 검증. cancel 요청은 검사 제외."""
        if request.get("type") == "cancel":
            return SafetyResult(allowed=True)
        return self._check_limits(self._trade_amount(request))

    @staticmethod
    def _trade_amount(request: dict) -> float:
        """요청의 예상 거래금액. 조건부(stop_loss/take_profit)는 trigger 기준."""
        from ..trader.order_spec import get_ord_type, STOP_LOSS, TAKE_PROFIT

        amount = float(request.get("amount", 0) or 0)
        if get_ord_type(request) in (STOP_LOSS, TAKE_PROFIT):
            return float(request.get("trigger", 0) or 0) * amount
        return float(request.get("price", 0) or 0) * amount
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/safety_guard_test.py -v`
Expected: PASS (기존 + 신규 4개 전부)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/safety_guard.py tests/unit_tests/safety_guard_test.py
git commit -m "[feat] SafetyGuard computes trade amount from trigger for conditional orders"
```

---

## Task 3: SimulationTrader 역량 선언 + 미지원 거부 (시장가 포함)

**Files:**
- Modify: `smtm/trader/simulation_trader.py`
- Test: `tests/unit_tests/simulation_trader_test.py`

**Interfaces:**
- Consumes: `order_spec.get_ord_type`, `order_spec.make_rejected_result`
- Produces: `SimulationTrader.SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})`; `send_request`가 미지원 `ord_type`을 실패 결과로 거부. 시장가는 기존처럼 현재 시세로 체결.

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/simulation_trader_test.py` 하단에 추가:
```python
class SimulationTraderCapabilityTest(unittest.TestCase):
    def _trader(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        return trader

    def test_market_buy_fills_at_current_quote(self):
        trader = self._trader()
        results = []
        trader.send_request([{
            "id": "m1", "type": "buy", "price": 0, "amount": 0.01,
            "ord_type": "market", "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "done")
        self.assertEqual(results[0]["price"], 50000)

    def test_unknown_ord_type_is_rejected(self):
        trader = self._trader()
        results = []
        trader.send_request([{
            "id": "x1", "type": "buy", "price": 50000, "amount": 0.01,
            "ord_type": "banana", "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "failed")
        self.assertIn("banana", results[0]["msg"])
        self.assertEqual(trader.balance, 500000)  # 잔고 변화 없음

    def test_legacy_buy_without_ord_type_still_fills(self):
        trader = self._trader()
        results = []
        trader.send_request([{
            "id": "b1", "type": "buy", "price": 1, "amount": 0.01,
            "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "done")
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py::SimulationTraderCapabilityTest -v`
Expected: FAIL — `test_unknown_ord_type_is_rejected`에서 현재는 `banana`가 buy로 그대로 체결되어 state가 "done" → assertion 실패.

- [ ] **Step 3: 구현**

`smtm/trader/simulation_trader.py` 상단 import에 추가:
```python
from . import order_spec
```

클래스에 역량 속성 추가(클래스 본문 상단, `CODE = "SIM"` 다음):
```python
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})
```

`send_request`를 아래로 교체:
```python
    def send_request(
        self,
        request_list: List[Dict[str, Any]],
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        for request in request_list:
            ord_type = order_spec.get_ord_type(request)
            if request.get("type") != "cancel" and ord_type not in self.SUPPORTED_ORD_TYPES:
                callback(order_spec.make_rejected_result(
                    request, f"unsupported ord_type: {ord_type}"))
                continue
            result = self._execute_request(request)
            self.order_history.append(result)
            callback(result)
```

> 참고: 시장가/지정가 모두 `_execute_request`가 `quotes[currency]`로 체결하므로 별도 분기 불필요.
> cancel은 역량 검사에서 제외(기존 동작 유지, `_execute_request`가 그대로 처리).

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: PASS (기존 + 신규 3개)

- [ ] **Step 5: 커밋**

```bash
git add smtm/trader/simulation_trader.py tests/unit_tests/simulation_trader_test.py
git commit -m "[feat] SimulationTrader declares ord_type capability and rejects unsupported"
```

---

## Task 4: SimulationTrader 조건부(손절/익절) 에뮬레이션

**Files:**
- Modify: `smtm/trader/simulation_trader.py`
- Test: `tests/unit_tests/simulation_trader_test.py`

**Interfaces:**
- Consumes: `order_spec.is_conditional`, `order_spec.STOP_LOSS`, `order_spec.TAKE_PROFIT`, `order_spec.get_ord_type`
- Produces:
  - `SUPPORTED_ORD_TYPES`에 `stop_loss`, `take_profit` 추가
  - 조건부 요청은 `state: "requested"`로 콜백 후 `pending_conditionals`에 보관
  - `update_quote(currency, price)`가 보관된 조건을 검사해 발동 시 `state: "done"` 매도/매수 체결
  - `cancel_request(request_id)`가 보관된 조건을 id로 제거

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/simulation_trader_test.py` 하단에 추가:
```python
class SimulationTraderConditionalTest(unittest.TestCase):
    def _holding_trader(self):
        # BTC 1개를 50000에 보유한 상태로 세팅
        trader = SimulationTrader(budget=1000000, currency="BTC")
        trader.update_quote("BTC", 50000)
        trader.send_request([{
            "id": "buy", "type": "buy", "price": 50000, "amount": 1.0,
            "date_time": "2026-07-03T12:00:00",
        }], lambda r: None)
        return trader

    def test_stop_loss_registered_returns_requested(self):
        trader = self._holding_trader()
        results = []
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
            "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "requested")
        self.assertEqual(len(trader.pending_conditionals), 1)

    def test_stop_loss_fires_when_price_drops_to_trigger(self):
        trader = self._holding_trader()
        results = []
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
        }], results.append)
        trader.update_quote("BTC", 47000)  # 트리거 도달
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["type"], "sell")
        self.assertEqual(results[-1]["price"], 47000)
        self.assertNotIn("BTC", trader.assets)  # 전량 매도
        self.assertEqual(len(trader.pending_conditionals), 0)

    def test_stop_loss_does_not_fire_above_trigger(self):
        trader = self._holding_trader()
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
        }], lambda r: None)
        trader.update_quote("BTC", 48000)  # 아직 트리거 위
        self.assertEqual(len(trader.pending_conditionals), 1)

    def test_take_profit_fires_when_price_rises_to_trigger(self):
        trader = self._holding_trader()
        results = []
        trader.send_request([{
            "id": "tp", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "take_profit", "trigger": 55000,
        }], results.append)
        trader.update_quote("BTC", 55000)
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["price"], 55000)
        self.assertEqual(len(trader.pending_conditionals), 0)

    def test_cancel_removes_pending_conditional(self):
        trader = self._holding_trader()
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
        }], lambda r: None)
        trader.cancel_request("sl")
        self.assertEqual(len(trader.pending_conditionals), 0)
        trader.update_quote("BTC", 47000)  # 취소되었으므로 발동 안 함
        self.assertIn("BTC", trader.assets)  # 여전히 보유 (매도 안 됨)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py::SimulationTraderConditionalTest -v`
Expected: FAIL — `stop_loss`가 현재 미지원(Task 3 기준 SUPPORTED에 없음)이라 거부되고 `pending_conditionals` 속성도 없음(`AttributeError`).

- [ ] **Step 3: 구현**

`smtm/trader/simulation_trader.py` 수정:

(a) 역량 확장:
```python
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market", "stop_loss", "take_profit"})
```

(b) `__init__` 끝에 보관소 추가:
```python
        self.pending_conditionals = []  # [{"request":..., "callback":...}]
```

(c) `send_request`에 조건부 분기 추가(Task 3의 구현을 아래로 교체):
```python
    def send_request(
        self,
        request_list: List[Dict[str, Any]],
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        for request in request_list:
            if request.get("type") == "cancel":
                self.cancel_request(request.get("id"))
                continue
            ord_type = order_spec.get_ord_type(request)
            if ord_type not in self.SUPPORTED_ORD_TYPES:
                callback(order_spec.make_rejected_result(
                    request, f"unsupported ord_type: {ord_type}"))
                continue
            if order_spec.is_conditional(request):
                self._register_conditional(request, callback)
                continue
            result = self._execute_request(request)
            self.order_history.append(result)
            callback(result)
```

(d) `cancel_request` 교체:
```python
    def cancel_request(self, request_id: str) -> None:
        self.pending_conditionals = [
            e for e in self.pending_conditionals
            if e["request"].get("id") != request_id
        ]
```

(e) `update_quote` 교체:
```python
    def update_quote(self, currency: str, price: float) -> None:
        self.quotes[currency] = float(price)
        self._check_conditionals(currency, float(price))
```

(f) 신규 메서드 추가(클래스 하단):
```python
    def _register_conditional(self, request, callback):
        self.pending_conditionals.append({"request": request, "callback": callback})
        callback({
            "request": request,
            "type": request.get("type"),
            "price": request.get("price", 0),
            "amount": request.get("amount", 0),
            "msg": "success",
            "balance": self.balance,
            "state": "requested",
            "date_time": request.get(
                "date_time", datetime.now().strftime(self.ISO_DATEFORMAT)
            ),
        })

    def _condition_fired(self, request, price):
        ord_type = order_spec.get_ord_type(request)
        trigger = float(request.get("trigger", 0) or 0)
        if ord_type == order_spec.STOP_LOSS:
            return price <= trigger
        if ord_type == order_spec.TAKE_PROFIT:
            return price >= trigger
        return False

    def _check_conditionals(self, currency, price):
        remaining = []
        for entry in self.pending_conditionals:
            request = entry["request"]
            if request.get("currency", self.currency) == currency and \
                    self._condition_fired(request, price):
                result = self._fill_conditional(request, currency, price)
                self.order_history.append(result)
                entry["callback"](result)
            else:
                remaining.append(entry)
        self.pending_conditionals = remaining

    def _fill_conditional(self, request, currency, price):
        amount = float(request.get("amount", 0) or 0)
        result = {
            "request": request,
            "type": request.get("type"),
            "price": price,
            "amount": amount,
            "msg": "success",
            "balance": self.balance,
            "state": "done",
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        if amount <= 0:
            return self._fail(result, "잘못된 수량")
        if request.get("type") == "sell":
            self._sell(currency, price, amount, result)
        elif request.get("type") == "buy":
            self._buy(currency, price, amount, result)
        else:
            return self._fail(result, "지원하지 않는 주문 유형")
        result["balance"] = self.balance
        return result
```

> 주의: `_fill_conditional`은 성공 시 `_sell`/`_buy`가 `result`를 실패로 바꿀 수 있음(예: 보유 부족).
> `_sell`/`_buy`는 실패 시 `result["state"]="failed"`로 세팅하므로 그대로 전달된다.

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: PASS (Task 3 테스트 포함 전부)

- [ ] **Step 5: 커밋**

```bash
git add smtm/trader/simulation_trader.py tests/unit_tests/simulation_trader_test.py
git commit -m "[feat] SimulationTrader emulates stop_loss/take_profit via update_quote"
```

---

## Task 5: UpbitTrader 시장가 활성화 + 역량 선언

**Files:**
- Modify: `smtm/trader/upbit_trader.py` (`_execute_order`, 클래스 속성)
- Test: `tests/unit_tests/upbit_trader_test.py`

**Interfaces:**
- Consumes: `order_spec.get_ord_type`, `order_spec.MARKET`, `order_spec.make_rejected_result`
- Produces: `UpbitTrader.SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})`. `ord_type=="market"`이면 시장가(매수=총액 KRW, 매도=수량)로 `_send_order` 호출. `ord_type` 미지정이면 기존 지정가 경로 그대로, `price==0`은 no-op 유지.

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/upbit_trader_test.py` 하단에 추가(기존 mock 패턴 참고):
```python
class UpbitTraderMarketOrderTest(unittest.TestCase):
    def _trader(self):
        trader = UpbitTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (50000, 1.0)  # 평단 50000, 1개 보유
        return trader

    @patch("smtm.trader.upbit_trader.UpbitTrader._send_order")
    def test_market_sell_calls_send_order_with_volume_only(self, mock_send):
        mock_send.return_value = {"uuid": "u1"}
        trader = self._trader()
        trader.is_opt_mode = False
        task = {
            "request": {"id": "ms", "type": "sell", "price": 0, "amount": 0.5,
                        "ord_type": "market"},
            "callback": MagicMock(),
        }
        trader._execute_order(task)
        # 시장가 매도: price=None, volume=amount
        args, kwargs = mock_send.call_args
        self.assertIsNone(kwargs.get("price", args[2] if len(args) > 2 else None))
        self.assertEqual(kwargs.get("volume", args[3] if len(args) > 3 else None), 0.5)

    @patch("smtm.trader.upbit_trader.UpbitTrader._send_order")
    def test_unsupported_ord_type_rejected(self, mock_send):
        trader = self._trader()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "x", "type": "sell", "price": 0, "amount": 1,
                        "ord_type": "oco"},
            "callback": callback,
        })
        mock_send.assert_not_called()
        result = callback.call_args[0][0]
        self.assertEqual(result["state"], "failed")

    @patch("smtm.trader.upbit_trader.UpbitTrader._send_order")
    def test_legacy_limit_order_unchanged(self, mock_send):
        mock_send.return_value = {"uuid": "u2"}
        trader = self._trader()
        trader.is_opt_mode = False
        trader._execute_order({
            "request": {"id": "lim", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": MagicMock(),
        })
        # 지정가: price/amount 그대로 전달
        args, kwargs = mock_send.call_args
        self.assertEqual(args[2], 50000)
        self.assertEqual(args[3], 0.1)
```

> `upbit_trader_test.py` 상단 import에 `from unittest.mock import patch, MagicMock`이 없으면 추가.

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/upbit_trader_test.py::UpbitTraderMarketOrderTest -v`
Expected: FAIL — `ord_type=="market"` 매도가 현재는 `price==0` 거부 로직에 걸리고, `oco`도 거부 결과 dict를 콜백하지 않음.

- [ ] **Step 3: 구현**

`smtm/trader/upbit_trader.py` 상단 import에 추가:
```python
from . import order_spec
```

클래스 속성 추가(`CODE = "UPB"` 다음):
```python
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})
```

`_execute_order`를 아래로 교체:
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
            # price==0은 기존 no-op(hold) 신호 — 지정가에서는 그대로 무시
            self.logger.warning("[REJECT] limit order requires price")
            return

        if is_buy and float(request["price"]) * float(request["amount"]) > self.balance:
            request_price = float(request["price"]) * float(request["amount"])
            self.logger.warning(
                f"[REJECT] balance is too small! {request_price} > {self.balance}"
            )
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                f"[REJECT] invalid amount {float(request['amount'])} > {self.asset[1]}"
            )
            task["callback"]("error!")
            return

        if is_market and is_buy:
            # 시장가 매수: Upbit는 총액(KRW) 기준 → price 파라미터에 총액 전달
            total_krw = float(request["price"]) * float(request["amount"])
            response = self._send_order(self.market, True, price=total_krw, volume=None)
        elif is_market:
            # 시장가 매도: 수량 기준
            response = self._send_order(
                self.market, False, price=None, volume=float(request["amount"]))
        else:
            response = self._send_order(
                self.market, is_buy, request["price"], request["amount"])

        if response is None:
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.order_map[request["id"]] = {
            "uuid": response["uuid"],
            "callback": task["callback"],
            "result": result,
        }
        task["callback"](result)
        self.logger.debug(f"request inserted {self.order_map[request['id']]}")
        self._start_timer()
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/upbit_trader_test.py -v`
Expected: PASS (기존 + 신규 3개)

- [ ] **Step 5: 커밋**

```bash
git add smtm/trader/upbit_trader.py tests/unit_tests/upbit_trader_test.py
git commit -m "[feat] UpbitTrader activates market orders behind ord_type, keeps price==0 no-op"
```

---

## Task 6: BithumbTrader 시장가 주문 + 역량 선언

**Files:**
- Modify: `smtm/trader/bithumb_trader.py` (`_execute_order`, 신규 `_send_market_order`, 클래스 속성)
- Test: `tests/unit_tests/bithumb_trader_test.py`

**Interfaces:**
- Consumes: `order_spec.get_ord_type`, `order_spec.MARKET`, `order_spec.make_rejected_result`
- Produces: `BithumbTrader.SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})`; `_send_market_order(is_buy, volume)` → `/trade/market_buy` 또는 `/trade/market_sell` 호출(`units` 기준). `ord_type` 미지정이면 기존 지정가 경로 유지.

- [ ] **Step 1: 실패 테스트 작성**

`tests/unit_tests/bithumb_trader_test.py` 하단에 추가:
```python
class BithumbTraderMarketOrderTest(unittest.TestCase):
    def _trader(self):
        trader = BithumbTrader(budget=1000000, currency="BTC")
        trader.balance = 1000000
        trader.asset = (50000, 1.0)
        return trader

    @patch("smtm.trader.bithumb_trader.BithumbTrader.bithumb_api_call")
    def test_market_sell_calls_market_sell_endpoint(self, mock_call):
        mock_call.return_value = {"status": "0000", "order_id": "o1"}
        trader = self._trader()
        trader._execute_order({
            "request": {"id": "ms", "type": "sell", "price": 0, "amount": 0.5,
                        "ord_type": "market"},
            "callback": MagicMock(),
        })
        endpoint = mock_call.call_args[0][0]
        query = mock_call.call_args[0][1]
        self.assertEqual(endpoint, "/trade/market_sell")
        self.assertEqual(query["units"], "0.5000")

    @patch("smtm.trader.bithumb_trader.BithumbTrader.bithumb_api_call")
    def test_unsupported_ord_type_rejected(self, mock_call):
        trader = self._trader()
        callback = MagicMock()
        trader._execute_order({
            "request": {"id": "x", "type": "sell", "price": 0, "amount": 1,
                        "ord_type": "stop_loss"},
            "callback": callback,
        })
        mock_call.assert_not_called()
        self.assertEqual(callback.call_args[0][0]["state"], "failed")

    @patch("smtm.trader.bithumb_trader.BithumbTrader._send_limit_order")
    def test_legacy_limit_order_uses_limit_path(self, mock_limit):
        mock_limit.return_value = {"status": "0000", "order_id": "o2"}
        trader = self._trader()
        trader._execute_order({
            "request": {"id": "lim", "type": "buy", "price": 50000, "amount": 0.1},
            "callback": MagicMock(),
        })
        mock_limit.assert_called_once()
```

> `bithumb_trader_test.py` 상단에 `from unittest.mock import patch, MagicMock`이 없으면 추가.

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/bithumb_trader_test.py::BithumbTraderMarketOrderTest -v`
Expected: FAIL — 시장가 매도가 현재 `price==0` 거부에 걸리고 `_send_market_order`가 존재하지 않음.

- [ ] **Step 3: 구현**

`smtm/trader/bithumb_trader.py` 상단 import에 추가:
```python
from . import order_spec
```

클래스 속성 추가(`CODE` 정의 다음):
```python
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market"})
```

`_execute_order`를 아래로 교체:
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
            self.logger.warning("invalid price request.")
            return

        if is_buy and not is_market and \
                float(request["price"]) * float(request["amount"]) > self.balance:
            self.logger.warning("invalid price request. balance is too small!")
            task["callback"]("error!")
            return

        if is_buy is False and float(request["amount"]) > self.asset[1]:
            self.logger.warning(
                "invalid price request. rest asset amount is less than request!"
            )
            task["callback"]("error!")
            return

        if is_market:
            response = self._send_market_order(is_buy, request["amount"])
        else:
            response = self._send_limit_order(
                is_buy, request["price"], request["amount"])

        if response is None or response["status"] != "0000":
            self.logger.error(f"Order error {response}")
            task["callback"]("error!")
            return

        result = self._create_success_result(request)
        self.order_map[request["id"]] = {
            "order_id": response["order_id"],
            "callback": task["callback"],
            "result": result,
        }
        task["callback"](result)
        self.logger.debug(f"request inserted {self.order_map[request['id']]}")
        self._start_timer()
```

`_send_limit_order` 바로 위 또는 아래에 신규 메서드 추가:
```python
    def _send_market_order(self, is_buy, volume):
        """시장가 주문 전송 (Bithumb market_buy / market_sell, units 기준)"""
        final_volume = "{0:.4f}".format(round(float(volume), 4))
        endpoint = "/trade/market_buy" if is_buy else "/trade/market_sell"
        self.logger.info(f"MARKET ORDER ##### {'BUY' if is_buy else 'SELL'}")
        self.logger.info(f"{self.market}, units: {final_volume}")
        query = {
            "order_currency": self.market,
            "payment_currency": self.market_currency,
            "units": final_volume,
        }
        return self.bithumb_api_call(endpoint, query)
```

- [ ] **Step 4: 통과 확인**

Run: `python -m pytest tests/unit_tests/bithumb_trader_test.py -v`
Expected: PASS (기존 + 신규 3개)

- [ ] **Step 5: 커밋**

```bash
git add smtm/trader/bithumb_trader.py tests/unit_tests/bithumb_trader_test.py
git commit -m "[feat] BithumbTrader adds market order support behind ord_type"
```

---

## 최종 검증

- [ ] **전체 단위 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/ -q`
Expected: 전부 PASS (신규 테스트 포함, 기존 회귀 없음)

- [ ] **하위호환 회귀 스모크**

Run: `python -m pytest tests/e2e_tests/ -q`
Expected: 기존 E2E 전부 PASS — 신규 필드 없는 기존 흐름이 동일하게 동작함을 확인.

---

## Self-Review 결과 (작성자 체크)

- **Spec 커버리지**: 스키마 additive(`ord_type`/`trigger`)=Task1·2·3·4·5·6, 역량 모델=Task1(기본값)+3/5/6(선언), SafetyGuard 조건부 금액=Task2, Simulation 시장가=Task3, Simulation 조건부=Task4, Upbit/Bithumb 시장가=Task5/6. ✅
- **범위 밖 명시**: OCO 에뮬레이션 / 세션 손절·익절 정책 / BinanceTrader / ConditionalOrderManager는 ②·③으로 이관(문서 상단 명시). ✅
- **Placeholder 스캔**: 모든 코드 스텝에 완전한 코드 포함. TBD/TODO 없음. ✅
- **타입 일관성**: `get_ord_type`/`is_conditional`/`make_rejected_result`/`SUPPORTED_ORD_TYPES` 이름이 전 태스크에서 동일. ✅
- **주의(구현자 확인 필요)**: Bithumb 시장가 엔드포인트(`/trade/market_buy|market_sell`, `units`)는 통합 테스트(실 API)로 최종 확인 필요 — 단위 테스트는 mock 기반. Task6 커밋 후 `tests/integration_tests/`에서 검증 권장.
