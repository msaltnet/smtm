# SimulationTrader Virtual Order Book Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `JptController` and turn `SimulationTrader` into a strategy-independent in-memory exchange with correct market, limit, sell stop-loss, sell take-profit, reservation, and cancellation behavior.

**Architecture:** Keep all virtual order lifecycle state inside `SimulationTrader`; do not add a shared conditional-order module or modify real exchange Trader implementations. `TradingOperator` continues to inject the latest `primary_candle` close, while strategies emit the existing request schema and consume the actual `fee` reported by the Trader.

**Tech Stack:** Python 3.12, standard library (`copy`, `datetime`, `math`), `unittest` tests executed by pytest, existing SMTM `Trader`/`Strategy`/`TradingOperator` abstractions.

**Approved design:** `docs/superpowers/specs/2026-08-12-simulation-trader-order-book-design.md`

---

## File structure and responsibilities

### Runtime files

- Modify `smtm/trader/simulation_trader.py`: own validation, quotes, total account state, reservations, pending orders, fills, cancellation, and account snapshots.
- Modify `smtm/trading_operator.py`: distinguish a successful fill from cancellation when updating daily trade count.
- Modify `smtm/strategy/strategy.py`: provide one fee-resolution helper shared by all strategies.
- Modify `smtm/strategy/strategy_bnh.py`: use the reported fee when updating internal balance.
- Modify `smtm/strategy/strategy_rsi.py`: use the reported fee when updating internal balance.
- Modify `smtm/strategy/strategy_sma.py`: use the reported fee when updating internal balance.
- Modify `smtm/strategy/strategy_llm.py`: use the reported fee when updating internal balance.
- Delete `smtm/controller/jpt_controller.py`: remove the unsafe, real-trading-by-default Jupyter controller.
- Modify `smtm/__init__.py`: remove the deleted controller from public imports and exports.

### Tests

- Modify `tests/unit_tests/simulation_trader_test.py`: make order type explicit where needed and cover the complete virtual order book contract.
- Modify `tests/unit_tests/trading_operator_test.py`: cover pending-order quote evaluation, cancellation, monitoring, and daily-count semantics.
- Modify `tests/unit_tests/strategy_bnh_test.py`: cover reported zero-fee accounting.
- Modify `tests/unit_tests/strategy_rsi_test.py`: cover reported zero-fee accounting.
- Modify `tests/unit_tests/strategy_sma_test.py`: cover reported zero-fee accounting.
- Modify `tests/unit_tests/strategy_llm_test.py`: cover reported zero-fee accounting.
- Modify `tests/unit_tests/main_args_test.py`: verify `JptController` is no longer exported.
- Modify `tests/unit_tests/session_manager_test.py`: prove virtual sessions select `SimulationTrader` without account credentials.
- Modify `tests/e2e_tests/e2e_chat_trading_test.py`: preserve the Telegram virtual-session happy path and verify exposed account state.

### User documentation

- Modify `README.md`: document virtual order behavior and the real/virtual support matrix.
- Modify `README-ko-kr.md`: Korean equivalent of the same contract and limitations.
- Modify `docs/exchanges-and-trading-ko.md`: make actual real Trader limitations explicit.
- Delete `jupyter_notebook.md`: remove the obsolete full-system `JptController` guide.
- Modify `docs/public/overview.md`, `docs/public/user-guide.md`, `docs/public/architecture.md`, `docs/public/requirements.md`: remove active `JptController` claims.
- Modify `docs/wiki/SMTM_프로젝트_소개.md`, `docs/wiki/architecture.md`, `docs/wiki/how-to-setup-and-run.md`: remove active `JptController` instructions while retaining references to standalone experiment notebooks.
- Modify `docs/smtm_class.puml`, `docs/smtm_component.puml`, and `docs/TODO.md`: remove active diagram and maintenance-note references.
- Delete `docs/smtm_class.png`: remove the stale generated diagram that still depicts `JptController`; retain the updated PlantUML source as the canonical diagram.

Historical documents under `docs/superpowers/`, `docs/claw-branch-review.md`, old version entries in release notes, and the `notebook/` experiment directory remain unchanged.

---

### Task 1: Establish strict request and result primitives

**Files:**
- Modify: `tests/unit_tests/simulation_trader_test.py`
- Modify: `smtm/trader/simulation_trader.py`

- [ ] **Step 1: Convert tests that mean “market order” to explicit market orders**

The existing tests that use an intentionally wrong request price currently rely on the simulator treating every order as a market order. Add `"ord_type": "market"` to those requests, including `test_buy_uses_injected_quote_and_ignores_request_price` and `test_sell_adds_balance_and_reduces_asset`:

```python
{
    "id": "1",
    "type": "buy",
    "ord_type": "market",
    "price": 1,
    "amount": 0.01,
    "date_time": "2026-04-26T12:00:00",
}
```

Leave legacy requests without `ord_type` only where their request price equals the quote and they intentionally test the backward-compatible default of `limit`.

- [ ] **Step 2: Write failing validation and terminal-result tests**

Append a focused validation class:

```python
class SimulationTraderValidationTest(unittest.TestCase):
    def setUp(self):
        self.trader = SimulationTrader(budget=100000, currency="BTC")
        self.trader.update_quote("BTC", 50000)

    def _send(self, request):
        results = []
        self.trader.send_request([request], results.append)
        return results[0]

    def test_rejects_missing_order_id(self):
        for invalid_id in (None, "", "   ", 123):
            request = {
                "type": "buy", "ord_type": "market", "amount": 0.1,
            }
            if invalid_id is not None:
                request["id"] = invalid_id
            with self.subTest(order_id=invalid_id):
                result = self._send(request)
                self.assertEqual(result["msg"], "잘못된 주문 ID")

    def test_rejects_non_finite_or_non_positive_numbers(self):
        cases = [
            ({"id": "a", "type": "buy", "ord_type": "market", "amount": 0},
             "잘못된 수량"),
            ({"id": "b", "type": "buy", "ord_type": "market", "amount": -1},
             "잘못된 수량"),
            ({"id": "c", "type": "buy", "ord_type": "market",
              "amount": float("nan")}, "잘못된 수량"),
            ({"id": "d", "type": "buy", "ord_type": "market",
              "amount": float("inf")}, "잘못된 수량"),
            ({"id": "e", "type": "buy", "ord_type": "limit", "price": 0,
              "amount": 1}, "잘못된 가격"),
            ({"id": "f", "type": "buy", "ord_type": "limit", "price": -1,
              "amount": 1}, "잘못된 가격"),
            ({"id": "g", "type": "buy", "ord_type": "limit",
              "price": float("nan"), "amount": 1}, "잘못된 가격"),
            ({"id": "h", "type": "buy", "ord_type": "limit",
              "price": float("inf"), "amount": 1}, "잘못된 가격"),
            ({"id": "i", "type": "sell", "ord_type": "stop_loss",
              "trigger": 0, "amount": 1}, "잘못된 트리거"),
            ({"id": "j", "type": "sell", "ord_type": "stop_loss",
              "trigger": -1, "amount": 1}, "잘못된 트리거"),
            ({"id": "k", "type": "sell", "ord_type": "take_profit",
              "trigger": float("nan"), "amount": 1}, "잘못된 트리거"),
            ({"id": "l", "type": "sell", "ord_type": "take_profit",
              "trigger": float("inf"), "amount": 1}, "잘못된 트리거"),
        ]
        for request, message in cases:
            with self.subTest(request=request):
                result = self._send(request)
                self.assertEqual(result["state"], "failed")
                self.assertEqual(result["msg"], message)
                self.assertEqual(result["fee"], 0)

    def test_rejects_oco_with_stable_message(self):
        result = self._send({
            "id": "oco", "type": "sell", "ord_type": "oco",
            "price": 0, "amount": 1, "trigger": 45000,
        })
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["msg"], "지원하지 않는 주문 유형: oco")

    def test_market_order_without_quote_fails_terminally(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        results = []
        trader.send_request([{
            "id": "cold-market", "type": "buy",
            "ord_type": "market", "amount": 1,
        }], results.append)
        self.assertEqual(results[-1]["state"], "failed")
        self.assertEqual(results[-1]["msg"], "시세 없음")
        self.assertEqual(trader.order_history, [results[-1]])

    def test_invalid_quote_does_not_replace_last_valid_quote(self):
        for price in (0, -1, float("nan"), float("inf")):
            self.trader.update_quote("BTC", price)
        self.assertEqual(self.trader.quotes["BTC"], 50000)
```

- [ ] **Step 3: Run the focused tests and verify they fail**

Run:

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderValidationTest \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderBuyTest::test_buy_uses_injected_quote_and_ignores_request_price
```

Expected: failures for missing IDs, invalid numeric values, missing `fee`, stable OCO error text, and invalid quote handling.

- [ ] **Step 4: Add request validation and standard result construction**

In `SimulationTrader`, import `copy` and `math` and add these helpers. Keep `pending_conditionals` during this foundation task so the existing conditional-order tests remain green; Task 2 adds the limit-order dictionary alongside it, and Task 3 completes the unified migration.

```python
import copy
import math


def __init__(self, budget=50000, currency="BTC", commission_ratio=0):
    self.logger = LogManager.get_logger(__class__.__name__)
    self.balance = float(budget)
    self.currency = currency
    self.commission_ratio = 0
    self.assets = {}
    self.quotes = {}
    self.order_history = []
    self.pending_conditionals = []

@staticmethod
def _positive_finite(value):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number

def _result(self, request, state, message, price=0, amount=0, fee=0):
    return {
        "request": copy.deepcopy(request),
        "type": request.get("type"),
        "price": float(price),
        "amount": float(amount),
        "fee": float(fee),
        "msg": message,
        "balance": self.balance,
        "state": state,
        "date_time": request.get(
            "date_time", datetime.now().strftime(self.ISO_DATEFORMAT)
        ),
    }

def _finish(self, result, callback):
    self.order_history.append(copy.deepcopy(result))
    callback(result)
    return result

def _reject(self, request, callback, message):
    return self._finish(
        self._result(request, "failed", message), callback
    )
```

Add `_validate_request(request, ord_type)` that returns the fixed Korean message or `None`:

```python
def _validate_request(self, request, ord_type):
    request_id = request.get("id")
    if not isinstance(request_id, str) or not request_id.strip():
        return "잘못된 주문 ID"
    if ord_type not in self.SUPPORTED_ORD_TYPES:
        return f"지원하지 않는 주문 유형: {ord_type}"
    if request.get("type") not in ("buy", "sell"):
        return f"지원하지 않는 매매 유형: {request.get('type')}"
    if self._positive_finite(request.get("amount")) is None:
        return "잘못된 수량"
    if ord_type == order_spec.LIMIT and \
            self._positive_finite(request.get("price")) is None:
        return "잘못된 가격"
    if ord_type in (order_spec.STOP_LOSS, order_spec.TAKE_PROFIT):
        if self._positive_finite(request.get("trigger")) is None:
            return "잘못된 트리거"
        if request.get("type") != "sell":
            return "매도 조건 주문만 지원"
    return None
```

Update `update_quote()` so an invalid quote logs a warning and returns without changing `quotes` or evaluating orders:

```python
def update_quote(self, currency: str, price: float) -> None:
    valid_price = self._positive_finite(price)
    if not currency or valid_price is None:
        self.logger.warning(f"invalid quote: {currency} {price}")
        return
    self.quotes[currency] = valid_price
    self._check_conditionals(currency, valid_price)
```

Route validation failures through `_reject()`. Use `_finish()` exactly once for every terminal fill or failure and never for a `requested` acknowledgement. Preserve the current immediate execution behavior temporarily; Task 2 separates market from limit behavior.

Replace `send_request()` with this complete transitional routing:

```python
def send_request(self, request_list, callback):
    for request in request_list:
        if request.get("type") == "cancel":
            self.cancel_request(request.get("id"))
            continue
        ord_type = order_spec.get_ord_type(request)
        message = self._validate_request(request, ord_type)
        if message:
            self._reject(request, callback, message)
            continue
        if order_spec.is_conditional(request):
            self._register_conditional(request, callback)
            continue
        self._finish(self._execute_request(request), callback)
```

Build `_execute_request()`'s initial result with `_result()`, use the already-validated numeric amount, and keep `_buy()`/`_sell()` as the mutation helpers for this task:

```python
def _execute_request(self, request):
    currency = request.get("currency", self.currency)
    fill_price = self.quotes.get(currency)
    if fill_price is None:
        return self._result(request, "failed", "시세 없음")

    amount = float(request["amount"])
    result = self._result(
        request, "done", "success", fill_price, amount, fee=0
    )
    if request["type"] == "buy":
        self._buy(currency, fill_price, amount, result)
    else:
        self._sell(currency, fill_price, amount, result)
    result["balance"] = self.balance
    return result
```

Change `_fail()` to set `fee=0` as well as zero price/amount. In `_register_conditional()` and `_fill_conditional()`, replace their result literals with `_result()` so every callback has the same keys, but leave their list storage and existing condition checks intact until Task 3.

- [ ] **Step 5: Run the focused tests and verify they pass**

Run the Step 3 command again.

Expected: all selected tests pass.

- [ ] **Step 6: Commit the validation foundation**

```bash
git add smtm/trader/simulation_trader.py tests/unit_tests/simulation_trader_test.py
git commit -m "refactor: standardize virtual order results"
```

---

### Task 2: Implement market and limit order execution with reservations

**Files:**
- Modify: `tests/unit_tests/simulation_trader_test.py`
- Modify: `smtm/trader/simulation_trader.py`

- [ ] **Step 1: Write failing limit-order and account-reservation tests**

Add these cases:

```python
class SimulationTraderLimitOrderTest(unittest.TestCase):
    def setUp(self):
        self.trader = SimulationTrader(budget=100000, currency="BTC")
        self.trader.update_quote("BTC", 50000)

    def test_marketable_limit_buy_fills_at_better_current_price(self):
        results = []
        self.trader.send_request([{
            "id": "buy-now", "type": "buy", "ord_type": "limit",
            "price": 55000, "amount": 1,
        }], results.append)
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["price"], 50000)
        self.assertEqual(self.trader.balance, 50000)

    def test_limit_buy_waits_reserves_and_fills_after_quote_change(self):
        results = []
        self.trader.send_request([{
            "id": "buy-later", "type": "buy", "ord_type": "limit",
            "price": 40000, "amount": 2,
        }], results.append)
        account = self.trader.get_account_info()
        self.assertEqual(results[-1]["state"], "requested")
        self.assertEqual(account["balance"], 100000)
        self.assertEqual(account["reserved_balance"], 80000)
        self.assertEqual(account["available_balance"], 20000)
        self.assertEqual(len(account["open_orders"]), 1)

        self.trader.update_quote("BTC", 39000)
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["price"], 39000)
        self.assertEqual(self.trader.balance, 22000)
        self.assertEqual(self.trader.get_account_info()["reserved_balance"], 0)

    def test_limit_sell_waits_and_reserves_asset(self):
        self.trader.assets["BTC"] = (50000, 2.0)
        results = []
        self.trader.send_request([{
            "id": "sell-later", "type": "sell", "ord_type": "limit",
            "price": 60000, "amount": 1.5,
        }], results.append)
        account = self.trader.get_account_info()
        self.assertEqual(account["reserved_asset"], {"BTC": 1.5})
        self.assertEqual(account["available_asset"], {"BTC": 0.5})

        self.trader.update_quote("BTC", 61000)
        self.assertEqual(results[-1]["price"], 61000)
        self.assertEqual(self.trader.assets["BTC"], (50000, 0.5))

    def test_pending_orders_prevent_double_spending(self):
        first = []
        second = []
        self.trader.send_request([{
            "id": "first", "type": "buy", "ord_type": "limit",
            "price": 40000, "amount": 2,
        }], first.append)
        self.trader.send_request([{
            "id": "second", "type": "buy", "ord_type": "limit",
            "price": 30000, "amount": 1,
        }], second.append)
        self.assertEqual(second[-1]["state"], "failed")
        self.assertEqual(second[-1]["msg"], "잔고 부족")

    def test_limit_order_can_register_before_first_quote(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        results = []
        trader.send_request([{
            "id": "cold", "type": "buy", "ord_type": "limit",
            "price": 50000, "amount": 1,
        }], results.append)
        self.assertEqual(results[-1]["state"], "requested")
        trader.update_quote("BTC", 49000)
        self.assertEqual(results[-1]["state"], "done")

    def test_rejects_duplicate_pending_order_id(self):
        request = {
            "id": "same", "type": "buy", "ord_type": "limit",
            "price": 40000, "amount": 1,
        }
        first = []
        duplicate = []
        self.trader.send_request([request], first.append)
        self.trader.send_request([request], duplicate.append)
        self.assertEqual(first[-1]["state"], "requested")
        self.assertEqual(duplicate[-1]["state"], "failed")
        self.assertEqual(duplicate[-1]["msg"], "중복 주문 ID")

    def test_virtual_commission_remains_zero(self):
        trader = SimulationTrader(
            budget=100000, currency="BTC", commission_ratio=0.25
        )
        trader.update_quote("BTC", 50000)
        results = []
        trader.send_request([{
            "id": "zero-fee", "type": "buy", "ord_type": "market",
            "amount": 1,
        }], results.append)
        self.assertEqual(results[-1]["fee"], 0)
        self.assertEqual(trader.balance, 50000)
```

Add this defensive-copy assertion to `test_limit_buy_waits_reserves_and_fills_after_quote_change()` before the fill:

```python
account["open_orders"][0]["request"]["price"] = 1
account["quote"]["BTC"] = 1
fresh_account = self.trader.get_account_info()
self.assertEqual(fresh_account["open_orders"][0]["request"]["price"], 40000)
self.assertEqual(fresh_account["quote"]["BTC"], 50000)
```

- [ ] **Step 2: Run the limit tests and verify they fail**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderLimitOrderTest
```

Expected: failures because limit orders do not wait, no reservation/account keys exist, and `pending_orders` are not evaluated.

- [ ] **Step 3: Add reservation and account snapshot helpers**

Add `self.pending_orders = {}` beside the still-existing `pending_conditionals` list, then add the following internal helpers:

```python
def _reserved_balance(self):
    return sum(entry["reserved_balance"] for entry in self.pending_orders.values())

def _reserved_assets(self):
    reserved = {}
    for entry in self.pending_orders.values():
        amount = entry["reserved_asset"]
        if amount:
            currency = entry["currency"]
            reserved[currency] = reserved.get(currency, 0.0) + amount
    return reserved

def _available_balance(self):
    return self.balance - self._reserved_balance()

def _available_asset(self, currency):
    total = self.assets.get(currency, (0, 0))[1]
    return total - self._reserved_assets().get(currency, 0.0)

def _queue(self, request, callback, reserved_balance=0, reserved_asset=0):
    currency = request.get("currency", self.currency)
    self.pending_orders[request["id"]] = {
        "request": copy.deepcopy(request),
        "callback": callback,
        "currency": currency,
        "reserved_balance": float(reserved_balance),
        "reserved_asset": float(reserved_asset),
    }
    callback(self._result(
        request, "requested", "success",
        price=request.get("price", 0), amount=request["amount"],
    ))
```

Replace `get_account_info()` with a defensive snapshot:

```python
def get_account_info(self) -> Dict[str, Any]:
    reserved_assets = self._reserved_assets()
    available_assets = {
        currency: round(amount - reserved_assets.get(currency, 0.0), 6)
        for currency, (_, amount) in self.assets.items()
    }
    open_orders = [{
        "request": copy.deepcopy(entry["request"]),
        "state": "requested",
        "reserved_balance": entry["reserved_balance"],
        "reserved_asset": entry["reserved_asset"],
    } for entry in self.pending_orders.values()]
    return {
        "balance": self.balance,
        "available_balance": self._available_balance(),
        "reserved_balance": self._reserved_balance(),
        "asset": copy.deepcopy(self.assets),
        "available_asset": available_assets,
        "reserved_asset": reserved_assets,
        "quote": dict(self.quotes),
        "open_orders": open_orders,
        "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
    }
```

- [ ] **Step 4: Implement market and limit routing**

Use explicit dispatch from `send_request()`:

```python
if request.get("type") == "cancel":
    self.cancel_request(request.get("id"))
    continue
ord_type = order_spec.get_ord_type(request)
message = self._validate_request(request, ord_type)
if message:
    self._reject(request, callback, message)
elif ord_type == order_spec.MARKET:
    self._submit_market(request, callback)
elif ord_type == order_spec.LIMIT:
    self._submit_limit(request, callback)
else:
    self._register_conditional(request, callback)
```

At the top of `_validate_request()`, after validating the non-empty ID, reject `request_id in self.pending_orders` with `"중복 주문 ID"`. Task 3 extends this naturally because all pending order types then share this dictionary.

Implement market and limit behavior:

```python
def _submit_market(self, request, callback):
    currency = request.get("currency", self.currency)
    quote = self.quotes.get(currency)
    if quote is None:
        return self._reject(request, callback, "시세 없음")
    return self._fill(request, callback, quote)

def _limit_fires(self, request, quote):
    limit = float(request["price"])
    if request["type"] == "buy":
        return quote <= limit
    return quote >= limit

def _submit_limit(self, request, callback):
    currency = request.get("currency", self.currency)
    quote = self.quotes.get(currency)
    if quote is not None and self._limit_fires(request, quote):
        return self._fill(request, callback, quote)

    amount = float(request["amount"])
    if request["type"] == "buy":
        reservation = float(request["price"]) * amount
        if reservation > self._available_balance():
            return self._reject(request, callback, "잔고 부족")
        return self._queue(request, callback, reserved_balance=reservation)
    if amount > self._available_asset(currency):
        return self._reject(request, callback, "보유 수량 부족")
    return self._queue(request, callback, reserved_asset=amount)
```

Make `_fill()` the only balance/asset mutation path. It must check **available** resources, set actual `fee`, and record the terminal result:

```python
def _fill(self, request, callback, fill_price):
    currency = request.get("currency", self.currency)
    amount = float(request["amount"])
    trade_value = fill_price * amount
    fee = trade_value * self.commission_ratio
    if request["type"] == "buy":
        if trade_value + fee > self._available_balance():
            return self._reject(request, callback, "잔고 부족")
        old_price, old_amount = self.assets.get(currency, (0, 0))
        new_amount = round(old_amount + amount, 6)
        average = round(
            (old_price * old_amount + trade_value) / new_amount, 6
        )
        self.balance -= trade_value + fee
        self.assets[currency] = (average, new_amount)
    else:
        if amount > self._available_asset(currency):
            return self._reject(request, callback, "보유 수량 부족")
        old_price, old_amount = self.assets.get(currency, (0, 0))
        new_amount = round(old_amount - amount, 6)
        self.balance += trade_value - fee
        if new_amount <= 0:
            self.assets.pop(currency, None)
        else:
            self.assets[currency] = (old_price, new_amount)
    result = self._result(
        request, "done", "success", fill_price, amount, fee
    )
    result["balance"] = self.balance
    return self._finish(result, callback)
```

When evaluating a pending order, pop it before `_fill()` so its own reservation is released while all other reservations remain enforced:

```python
def _fill_pending(self, request_id, quote):
    entry = self.pending_orders.pop(request_id)
    return self._fill(entry["request"], entry["callback"], quote)
```

For this task, add a limit-only `_check_pending_orders()` and call it before the existing `_check_conditionals()` from `update_quote()`. This keeps every commit behaviorally complete while both stores coexist:

```python
def _check_pending_orders(self, currency, quote):
    request_ids = [
        request_id for request_id, entry in self.pending_orders.items()
        if entry["currency"] == currency
    ]
    for request_id in request_ids:
        entry = self.pending_orders.get(request_id)
        if entry is not None and self._limit_fires(entry["request"], quote):
            self._fill_pending(request_id, quote)
```

- [ ] **Step 5: Run the limit and existing basic fill tests**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderLimitOrderTest \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderBuyTest \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderSellTest \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderAccountTest
```

Expected: all selected tests pass. Update old account assertions to include the new keys without changing the meanings of `balance`, `asset`, and `quote`.

Where the existing account test compares the complete key set, use this exact expectation:

```python
self.assertEqual(set(account), {
    "balance", "available_balance", "reserved_balance", "asset",
    "available_asset", "reserved_asset", "quote", "open_orders",
    "date_time",
})
```

- [ ] **Step 6: Commit market, limit, and reservation behavior**

```bash
git add smtm/trader/simulation_trader.py tests/unit_tests/simulation_trader_test.py
git commit -m "feat: add virtual limit order book"
```

---

### Task 3: Complete stop-loss, take-profit, and cancellation lifecycle

**Files:**
- Modify: `tests/unit_tests/simulation_trader_test.py`
- Modify: `smtm/trader/simulation_trader.py`

- [ ] **Step 1: Replace conditional-list tests with unified pending-order tests**

Change assertions from `pending_conditionals` to `pending_orders`, then add:

```python
class SimulationTraderConditionalLifecycleTest(unittest.TestCase):
    def setUp(self):
        self.trader = SimulationTrader(budget=1000000, currency="BTC")
        self.trader.update_quote("BTC", 50000)
        self.trader.assets["BTC"] = (50000, 2.0)

    def test_sell_stop_and_take_profit_trigger_at_boundary(self):
        stop_results = []
        self.trader.send_request([{
            "id": "sl", "type": "sell", "ord_type": "stop_loss",
            "trigger": 47000, "price": 0, "amount": 1,
        }], stop_results.append)
        self.trader.update_quote("BTC", 47000)
        self.assertEqual(stop_results[-1]["state"], "done")
        self.assertEqual(stop_results[-1]["price"], 47000)

        take_results = []
        self.trader.send_request([{
            "id": "tp", "type": "sell", "ord_type": "take_profit",
            "trigger": 55000, "price": 0, "amount": 1,
        }], take_results.append)
        self.trader.update_quote("BTC", 55000)
        self.assertEqual(take_results[-1]["state"], "done")
        self.assertEqual(take_results[-1]["price"], 55000)

    def test_buy_conditionals_are_rejected(self):
        for ord_type in ("stop_loss", "take_profit"):
            results = []
            self.trader.send_request([{
                "id": ord_type, "type": "buy", "ord_type": ord_type,
                "trigger": 45000, "amount": 1,
            }], results.append)
            self.assertEqual(results[-1]["msg"], "매도 조건 주문만 지원")

    def test_conditionals_can_register_before_first_quote(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        trader.assets["BTC"] = (50000, 2.0)
        stop_results = []
        take_results = []
        trader.send_request([{
            "id": "cold-sl", "type": "sell", "ord_type": "stop_loss",
            "trigger": 45000, "amount": 1,
        }], stop_results.append)
        trader.send_request([{
            "id": "cold-tp", "type": "sell", "ord_type": "take_profit",
            "trigger": 60000, "amount": 1,
        }], take_results.append)
        self.assertEqual(stop_results[-1]["state"], "requested")
        self.assertEqual(take_results[-1]["state"], "requested")
        trader.update_quote("BTC", 45000)
        self.assertEqual(stop_results[-1]["state"], "done")
        self.assertEqual(take_results[-1]["state"], "requested")

    def test_already_satisfied_conditional_fills_immediately(self):
        for ord_type, trigger in (("stop_loss", 50000),
                                  ("take_profit", 50000)):
            with self.subTest(ord_type=ord_type):
                trader = SimulationTrader(budget=100000, currency="BTC")
                trader.update_quote("BTC", 50000)
                trader.assets["BTC"] = (50000, 1.0)
                results = []
                trader.send_request([{
                    "id": ord_type, "type": "sell", "ord_type": ord_type,
                    "trigger": trigger, "amount": 1,
                }], results.append)
                self.assertEqual(
                    [result["state"] for result in results], ["done"]
                )
                self.assertEqual(results[-1]["price"], 50000)
                self.assertEqual(trader.pending_orders, {})

    def test_conditionals_reserve_asset_and_cannot_share_full_position(self):
        first = []
        second = []
        self.trader.send_request([{
            "id": "sl", "type": "sell", "ord_type": "stop_loss",
            "trigger": 45000, "amount": 2,
        }], first.append)
        self.trader.send_request([{
            "id": "tp", "type": "sell", "ord_type": "take_profit",
            "trigger": 60000, "amount": 2,
        }], second.append)
        self.assertEqual(first[-1]["state"], "requested")
        self.assertEqual(second[-1]["state"], "failed")
        self.assertEqual(second[-1]["msg"], "보유 수량 부족")

    def test_cancel_releases_reservation_and_calls_original_callback(self):
        results = []
        self.trader.send_request([{
            "id": "sl", "type": "sell", "ord_type": "stop_loss",
            "trigger": 45000, "amount": 1,
        }], results.append)
        self.trader.cancel_request("sl")
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["msg"], "canceled")
        self.assertEqual(results[-1]["price"], 0)
        self.assertEqual(results[-1]["amount"], 0)
        self.assertEqual(self.trader.get_account_info()["reserved_asset"], {})
        self.assertEqual(self.trader.order_history, [results[-1]])

    def test_cancel_all_clears_every_order_and_prevents_later_fill(self):
        results = []
        for request in (
            {"id": "sl", "type": "sell", "ord_type": "stop_loss",
             "trigger": 45000, "amount": 1},
            {"id": "limit", "type": "buy", "ord_type": "limit",
             "price": 40000, "amount": 1},
        ):
            self.trader.send_request([request], results.append)
        self.trader.cancel_all_requests()
        self.assertEqual(self.trader.pending_orders, {})
        self.assertEqual([r["msg"] for r in results[-2:]], ["canceled", "canceled"])
        self.trader.update_quote("BTC", 40000)
        self.assertEqual(self.trader.assets["BTC"], (50000, 2.0))

    def test_cancel_request_type_delegates_and_missing_id_is_noop(self):
        original_results = []
        self.trader.send_request([{
            "id": "limit", "type": "buy", "ord_type": "limit",
            "price": 40000, "amount": 1,
        }], original_results.append)
        self.trader.send_request(
            [{"id": "limit", "type": "cancel"}], lambda result: None
        )
        self.assertEqual(original_results[-1]["msg"], "canceled")
        history = list(self.trader.order_history)
        self.trader.cancel_request("missing")
        self.assertEqual(self.trader.order_history, history)
```

Add these deterministic processing tests:

```python
def test_triggered_orders_fill_in_registration_order(self):
    trader = SimulationTrader(budget=100000, currency="BTC")
    trader.update_quote("BTC", 50000)
    terminal_ids = []

    def callback(result):
        if result["state"] != "requested":
            terminal_ids.append(result["request"]["id"])

    for request in (
        {"id": "first", "type": "buy", "ord_type": "limit",
         "price": 40000, "amount": 1},
        {"id": "second", "type": "buy", "ord_type": "limit",
         "price": 30000, "amount": 1},
    ):
        trader.send_request([request], callback)
    trader.update_quote("BTC", 30000)
    self.assertEqual(terminal_ids, ["first", "second"])

def test_callback_can_cancel_later_order_in_quote_snapshot(self):
    trader = SimulationTrader(budget=100000, currency="BTC")
    trader.update_quote("BTC", 50000)
    first_results = []
    second_results = []

    def first_callback(result):
        first_results.append(result)
        if result["state"] == "done":
            trader.cancel_request("second")

    trader.send_request([{
        "id": "first", "type": "buy", "ord_type": "limit",
        "price": 40000, "amount": 1,
    }], first_callback)
    trader.send_request([{
        "id": "second", "type": "buy", "ord_type": "limit",
        "price": 40000, "amount": 1,
    }], second_results.append)
    trader.update_quote("BTC", 39000)

    self.assertEqual(first_results[-1]["msg"], "success")
    self.assertEqual(second_results[-1]["msg"], "canceled")
    self.assertEqual(trader.assets["BTC"][1], 1)
    self.assertEqual(trader.pending_orders, {})
```

- [ ] **Step 2: Run the conditional lifecycle tests and verify they fail**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/simulation_trader_test.py::SimulationTraderConditionalLifecycleTest
```

Expected: failures for asset reservation, buy-conditional rejection, cancellation callbacks, and `cancel_all_requests()`.

- [ ] **Step 3: Implement conditional submission and unified quote evaluation**

First remove `pending_conditionals` from `__init__()`, route the conditional branch in `send_request()` to `_submit_conditional()`, and make `update_quote()` call only `_check_pending_orders()`. Then implement:

```python
def _conditional_fires(self, request, quote):
    ord_type = order_spec.get_ord_type(request)
    trigger = float(request["trigger"])
    if ord_type == order_spec.STOP_LOSS:
        return quote <= trigger
    return quote >= trigger

def _submit_conditional(self, request, callback):
    currency = request.get("currency", self.currency)
    quote = self.quotes.get(currency)
    if quote is not None and self._conditional_fires(request, quote):
        return self._fill(request, callback, quote)
    amount = float(request["amount"])
    if amount > self._available_asset(currency):
        return self._reject(request, callback, "보유 수량 부족")
    return self._queue(request, callback, reserved_asset=amount)

def _pending_fires(self, request, quote):
    ord_type = order_spec.get_ord_type(request)
    if ord_type == order_spec.LIMIT:
        return self._limit_fires(request, quote)
    return self._conditional_fires(request, quote)

def _check_pending_orders(self, currency, quote):
    request_ids = [
        request_id for request_id, entry in self.pending_orders.items()
        if entry["currency"] == currency
    ]
    for request_id in request_ids:
        entry = self.pending_orders.get(request_id)
        if entry is None:
            continue
        if self._pending_fires(entry["request"], quote):
            self._fill_pending(request_id, quote)
```

- [ ] **Step 4: Implement individual and bulk cancellation**

```python
def cancel_request(self, request_id: str) -> None:
    entry = self.pending_orders.pop(request_id, None)
    if entry is None:
        return
    result = self._result(
        entry["request"], "done", "canceled", fee=0
    )
    self._finish(result, entry["callback"])

def cancel_all_requests(self) -> None:
    for request_id in list(self.pending_orders):
        self.cancel_request(request_id)
```

Remove `_register_conditional`, `_condition_fired`, `_check_conditionals`, `_fill_conditional`, and every `pending_conditionals` reference. At this point the validation duplicate-ID check covers limit, stop-loss, and take-profit uniformly.

- [ ] **Step 5: Run the complete SimulationTrader suite**

```bash
env PYTHONPATH=. python3 -m pytest -q tests/unit_tests/simulation_trader_test.py
```

Expected: all SimulationTrader tests pass. Confirm failures and cancellations appear once in `order_history`, while `requested` intermediate results do not.

- [ ] **Step 6: Commit the conditional and cancellation lifecycle**

```bash
git add smtm/trader/simulation_trader.py tests/unit_tests/simulation_trader_test.py
git commit -m "feat: complete virtual conditional orders"
```

---

### Task 4: Make TradingOperator account for fills, failures, and cancellations correctly

**Files:**
- Modify: `tests/unit_tests/trading_operator_test.py`
- Modify: `smtm/trading_operator.py`

- [ ] **Step 1: Write failing operator lifecycle tests**

Add tests that use a direct standard request rather than a strategy-specific branch:

```python
def test_quote_update_fills_pending_limit_order(self):
    operator, trader, _, monitor = self._make(closing_price=50000)
    operator.state = "running"
    results_before = len(monitor.trade_result_log)
    operator._send_requests([{
        "id": "pending", "type": "buy", "ord_type": "limit",
        "price": 40000, "amount": 1,
        "date_time": "2026-07-03T12:00:00",
    }])
    self.assertEqual(len(trader.pending_orders), 1)
    self.assertEqual(len(monitor.trade_result_log), results_before)

    operator._sync_trader_quote([{
        "type": "primary_candle", "market": "BTC", "closing_price": 39000,
    }])
    self.assertEqual(len(trader.pending_orders), 0)
    self.assertEqual(monitor.trade_result_log[-1]["result"]["state"], "done")

def test_cancel_result_is_logged_but_does_not_consume_daily_quota(self):
    operator, trader, _, monitor = self._make()
    operator.state = "running"
    operator._send_requests([{
        "id": "pending", "type": "buy", "ord_type": "limit",
        "price": 40000, "amount": 1,
    }])
    trader.cancel_request("pending")
    self.assertEqual(operator.safety_guard.daily_trade_count, 0)
    self.assertEqual(monitor.trade_result_log[-1]["result"]["msg"], "canceled")

def test_stop_cancels_all_pending_orders(self):
    operator, trader, _, _ = self._make()
    operator.state = "running"
    operator.worker.start()
    operator._send_requests([{
        "id": "pending", "type": "buy", "ord_type": "limit",
        "price": 40000, "amount": 1,
    }])
    operator.stop()
    self.assertEqual(trader.pending_orders, {})
    self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
```

Add this operator-level conditional loop. Retain the existing `test_failed_trade_does_not_consume_daily_quota`; together with the new cancellation test it proves neither terminal failure class consumes quota.

```python
def test_quote_update_fills_pending_sell_conditionals(self):
    cases = (
        ("stop_loss", 45000, 44000),
        ("take_profit", 55000, 56000),
    )
    for ord_type, trigger, closing_price in cases:
        with self.subTest(ord_type=ord_type):
            operator, trader, _, monitor = self._make()
            operator.state = "running"
            trader.assets["BTC"] = (50000, 1.0)
            trader.update_quote("BTC", 50000)
            operator._send_requests([{
                "id": ord_type, "type": "sell", "ord_type": ord_type,
                "trigger": trigger, "amount": 1,
                "date_time": "2026-07-03T12:00:00",
            }])
            operator._sync_trader_quote([{
                "type": "primary_candle", "market": "BTC",
                "closing_price": closing_price,
            }])
            result = monitor.trade_result_log[-1]["result"]
            self.assertEqual(result["state"], "done")
            self.assertEqual(result["msg"], "success")
```

- [ ] **Step 2: Run the new operator tests and verify the cancellation count fails**

```bash
env PYTHONPATH=. python3 -m pytest -q tests/unit_tests/trading_operator_test.py
```

Expected: the cancellation test fails because every `state="done"` buy/sell currently increments the daily count.

- [ ] **Step 3: Restrict daily count updates to actual successful fills**

Replace the callback condition with:

```python
is_fill = (
    result.get("state") == "done"
    and result.get("msg") == "success"
    and result.get("type") in ("buy", "sell")
    and float(result.get("amount", 0) or 0) > 0
)
if is_fill:
    self.safety_guard.record_trade(result)
```

Keep `strategy.update_result(result)` before the `requested` early return so strategies track pending IDs. Keep `analyzer.put_result(result)` for every terminal fill, failure, or cancellation.

- [ ] **Step 4: Run operator and monitor tests**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/trading_operator_test.py \
  tests/unit_tests/system_monitor_test.py \
  tests/unit_tests/analyzer_test.py
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit operator lifecycle semantics**

```bash
git add smtm/trading_operator.py tests/unit_tests/trading_operator_test.py
git commit -m "fix: distinguish virtual fills from cancellations"
```

---

### Task 5: Reconcile strategy balances with Trader-reported fees

**Files:**
- Modify: `smtm/strategy/strategy.py`
- Modify: `smtm/strategy/strategy_bnh.py`
- Modify: `smtm/strategy/strategy_rsi.py`
- Modify: `smtm/strategy/strategy_sma.py`
- Modify: `smtm/strategy/strategy_llm.py`
- Modify: `tests/unit_tests/strategy_bnh_test.py`
- Modify: `tests/unit_tests/strategy_rsi_test.py`
- Modify: `tests/unit_tests/strategy_sma_test.py`
- Modify: `tests/unit_tests/strategy_llm_test.py`
- Modify: `tests/unit_tests/trading_operator_test.py`

- [ ] **Step 1: Write one zero-fee accounting regression per strategy**

Add this concrete assertion to each strategy’s test module, using its existing test class or a new fee-accounting class.

BNH:

```python
def test_update_result_uses_reported_zero_fee(self):
    strategy = StrategyBuyAndHold()
    strategy.initialize(500000)
    strategy.update_result({
        "request": {"id": "b"}, "type": "buy", "state": "done",
        "msg": "success", "price": 50000, "amount": 2, "fee": 0,
    })
    self.assertEqual(strategy.balance, 400000)
```

RSI:

```python
def test_update_result_uses_reported_zero_fee(self):
    strategy = StrategyRsi()
    strategy.initialize(500000)
    strategy.update_result({
        "request": {"id": "b"}, "type": "buy", "state": "done",
        "msg": "success", "price": 50000, "amount": 2, "fee": 0,
    })
    self.assertEqual(strategy.balance, 400000)
```

SMA:

```python
def test_update_result_uses_reported_zero_fee(self):
    strategy = StrategySma()
    strategy.initialize(500000)
    strategy.update_result({
        "request": {"id": "b"}, "type": "buy", "state": "done",
        "msg": "success", "price": 50000, "amount": 2, "fee": 0,
    })
    self.assertEqual(strategy.balance, 400000)
```

LLM:

```python
def test_update_result_uses_reported_zero_fee(self):
    strategy = StrategyLlm(llm_client=None)
    strategy.initialize(500000)
    strategy.update_result({
        "request": {"id": "b"}, "type": "buy", "state": "done",
        "msg": "success", "price": 50000, "amount": 2, "fee": 0,
    })
    self.assertEqual(strategy.balance, 400000)
```

Retain one existing/no-`fee` result test in each strategy suite to prove the 0.05% legacy fallback remains unchanged.

- [ ] **Step 2: Run the four tests and verify they fail**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/strategy_bnh_test.py \
  tests/unit_tests/strategy_rsi_test.py \
  tests/unit_tests/strategy_sma_test.py \
  tests/unit_tests/strategy_llm_test.py
```

Expected: the new tests report `399950` instead of `400000` before implementation.

- [ ] **Step 3: Add the shared fee-resolution helper**

Add this concrete method to the `Strategy` base class:

```python
@staticmethod
def _result_fee(result: Dict[str, Any], commission_ratio: float) -> float:
    if "fee" in result:
        return float(result.get("fee") or 0)
    total = float(result.get("price", 0)) * float(result.get("amount", 0))
    return total * commission_ratio
```

In all four `update_result()` implementations replace:

```python
fee = total * self.COMMISSION_RATIO
```

with:

```python
fee = self._result_fee(result, self.COMMISSION_RATIO)
```

Do not change order sizing formulas in RSI/SMA; they continue protecting real-Trader orders with their existing commission assumption.

- [ ] **Step 4: Add an end-to-end account consistency assertion**

In `tests/unit_tests/trading_operator_test.py::test_tick_executes_full_pipeline_and_buys`, add:

```python
self.assertEqual(strategy.balance, trader.balance)
self.assertEqual(trader.order_history[0]["fee"], 0)
```

- [ ] **Step 5: Run strategy and operator tests**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/strategy_bnh_test.py \
  tests/unit_tests/strategy_rsi_test.py \
  tests/unit_tests/strategy_sma_test.py \
  tests/unit_tests/strategy_llm_test.py \
  tests/unit_tests/trading_operator_test.py
```

Expected: all selected tests pass; results without `fee` retain old arithmetic and `SimulationTrader` results use fee 0.

- [ ] **Step 6: Commit fee reconciliation**

```bash
git add smtm/strategy/strategy.py \
  smtm/strategy/strategy_bnh.py \
  smtm/strategy/strategy_rsi.py \
  smtm/strategy/strategy_sma.py \
  smtm/strategy/strategy_llm.py \
  tests/unit_tests/strategy_bnh_test.py \
  tests/unit_tests/strategy_rsi_test.py \
  tests/unit_tests/strategy_sma_test.py \
  tests/unit_tests/strategy_llm_test.py \
  tests/unit_tests/trading_operator_test.py
git commit -m "fix: align strategy and virtual account fees"
```

---

### Task 6: Verify virtual sessions remain exchange-independent end to end

**Files:**
- Modify: `tests/unit_tests/session_manager_test.py`
- Modify: `tests/e2e_tests/e2e_chat_trading_test.py`

- [ ] **Step 1: Add a SessionManager routing test**

In `SessionManagerVirtualTests`, add:

```python
def test_virtual_profile_uses_simulation_trader_without_account(self):
    from smtm.trader.simulation_trader import SimulationTrader

    for exchange in ("UPB", "BTH", "BNC", "OKX", "UBD"):
        with self.subTest(exchange=exchange):
            name = f"virtual-{exchange.lower()}"
            result = self.manager.create_session({
                **VIRTUAL_PROFILE, "name": name, "exchange": exchange,
            })
            self.assertTrue(result["success"], result)
            session = self.manager.get_session(name)
            self.assertIsInstance(session.trader, SimulationTrader)
            self.assertIsNone(session.account)
```

The class-level DataProvider factory patch already supplies `StubDataProvider`, so the test checks Trader routing without network access or exchange credentials.

- [ ] **Step 2: Extend the Telegram E2E portfolio assertion**

After the existing BNH virtual fill, inspect `get_account_info()`:

```python
account = trader.get_account_info()
self.assertLess(account["balance"], 500000)
self.assertEqual(account["available_balance"], account["balance"])
self.assertEqual(account["reserved_balance"], 0)
self.assertEqual(account["open_orders"], [])
```

- [ ] **Step 3: Run SessionManager and E2E tests**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/session_manager_test.py \
  tests/e2e_tests/e2e_chat_trading_test.py
```

Expected: all selected tests pass for every virtual exchange/profile code tested, with no API credentials.

- [ ] **Step 4: Commit virtual-session regression coverage**

```bash
git add tests/unit_tests/session_manager_test.py tests/e2e_tests/e2e_chat_trading_test.py
git commit -m "test: cover exchange-independent virtual sessions"
```

---

### Task 7: Remove JptController runtime and active documentation

**Files:**
- Delete: `smtm/controller/jpt_controller.py`
- Modify: `smtm/__init__.py`
- Modify: `tests/unit_tests/main_args_test.py`
- Delete: `jupyter_notebook.md`
- Modify: `docs/public/overview.md`
- Modify: `docs/public/user-guide.md`
- Modify: `docs/public/architecture.md`
- Modify: `docs/public/requirements.md`
- Modify: `docs/wiki/SMTM_프로젝트_소개.md`
- Modify: `docs/wiki/architecture.md`
- Modify: `docs/wiki/how-to-setup-and-run.md`
- Modify: `docs/smtm_class.puml`
- Modify: `docs/smtm_component.puml`
- Modify: `docs/TODO.md`
- Delete: `docs/smtm_class.png`

- [ ] **Step 1: Change the export test first**

Replace the final assertions in `ControllerExportTests` with:

```python
self.assertTrue(hasattr(smtm, "TelegramController"))
self.assertFalse(hasattr(smtm, "JptController"))
self.assertNotIn("JptController", smtm.__all__)
```

- [ ] **Step 2: Run the export test and verify it fails**

```bash
env PYTHONPATH=. python3 -m pytest -q \
  tests/unit_tests/main_args_test.py::ControllerExportTests
```

Expected: failure because `smtm.JptController` is still imported and exported.

- [ ] **Step 3: Remove runtime code and package export**

Delete `smtm/controller/jpt_controller.py`. Remove both of these lines from `smtm/__init__.py`:

```python
from .controller.jpt_controller import JptController
```

```python
"JptController",
```

- [ ] **Step 4: Remove active user guidance**

Delete `jupyter_notebook.md`. In the listed public/wiki documents:

- Remove `JptController` nodes, bullets, code samples, warnings, and requirements.
- Change interface/presentation descriptions to `TelegramController` only.
- Change “Telegram / Jupyter” user/control-channel labels to Telegram only.
- Where a paragraph says strategies can be validated through JptController, retain only the `virtual` Telegram profile/session procedure.
- Retain `notebook/` references that describe low-level exchange/data experiments without claiming full-system controller support.
- Remove the `JptController` declaration and arrow from both PlantUML sources.
- In `docs/TODO.md`, change the completed interface-layer note to `TelegramController` only and state that `docs/smtm_class.png` was removed because generated images are not reproducible in this repository.
- In `docs/public/architecture.md`, list the `.puml` sources as canonical and remove the `smtm_class.png` output claim.
- Do not rewrite historical design/plan documents or old release-note entries.

For example, `docs/public/requirements.md` must read:

```markdown
- **포함**: LLM 기반 매매 오케스트레이션, 안전장치, 시장 데이터 / 거래소 연동, 대화형 제어(Telegram), 관찰 가능성(로그).
```

and the `R-CHAT-05` Jupyter requirement must be removed rather than renumbering stable requirement IDs.

- [ ] **Step 5: Verify the controller is gone from active surfaces**

```bash
env PYTHONPATH=. python3 -m pytest -q tests/unit_tests/main_args_test.py
test ! -e jupyter_notebook.md
test ! -e docs/smtm_class.png
rg -n "JptController|jpt_controller" \
  smtm tests README.md README-ko-kr.md docs \
  --glob '!docs/superpowers/**' \
  --glob '!docs/claw-branch-review.md' \
  --glob '!docs/public/release-notes.md'
```

Expected: pytest passes and `rg` returns no matches. The non-zero exit status from match-free `rg` is expected.

- [ ] **Step 6: Commit JptController removal**

```bash
git add -A smtm/controller/jpt_controller.py smtm/__init__.py \
  tests/unit_tests/main_args_test.py jupyter_notebook.md \
  docs/public/overview.md docs/public/user-guide.md \
  docs/public/architecture.md docs/public/requirements.md \
  docs/wiki/SMTM_프로젝트_소개.md docs/wiki/architecture.md \
  docs/wiki/how-to-setup-and-run.md docs/smtm_class.puml \
  docs/smtm_component.puml docs/TODO.md docs/smtm_class.png
git commit -m "refactor: remove Jupyter controller"
```

---

### Task 8: Document real and virtual order support accurately

**Files:**
- Modify: `README.md`
- Modify: `README-ko-kr.md`
- Modify: `docs/exchanges-and-trading-ko.md`

- [ ] **Step 1: Add the same support matrix to all three documents**

Use this Korean matrix in `README-ko-kr.md` and `docs/exchanges-and-trading-ko.md`:

```markdown
| 주문 유형 | 실제 Trader (UPB/BTH/BNC/OKX) | `SimulationTrader` |
|---|:---:|:---:|
| 시장가 | ✅ | ✅ 현재가 즉시 체결 |
| 지정가 | ✅ | ✅ 조건 충족까지 대기, 유리한 현재가로 체결 |
| 매도 손절 | ❌ | ✅ 종가가 trigger 이하일 때 체결 |
| 매도 익절 | ❌ | ✅ 종가가 trigger 이상일 때 체결 |
| OCO | ❌ | ❌ |
| 트레일링 스톱 | ❌ | ❌ |
```

Use this English equivalent in `README.md`:

```markdown
| Order type | Real Traders (UPB/BTH/BNC/OKX) | `SimulationTrader` |
|---|:---:|:---:|
| Market | ✅ | ✅ immediate fill at current quote |
| Limit | ✅ | ✅ waits for the condition; fills at a better current quote |
| Sell stop-loss | ❌ | ✅ fills when candle close is at or below trigger |
| Sell take-profit | ❌ | ✅ fills when candle close is at or above trigger |
| OCO | ❌ | ❌ |
| Trailing stop | ❌ | ❌ |
```

- [ ] **Step 2: Document virtual-order limitations verbatim**

Add these points in both languages:

```markdown
- 가상 잔고·대기 주문·이력은 메모리에만 있으며 프로세스를 재시작하면 사라집니다.
- 조건 주문은 `primary_candle`의 최신 종가가 들어올 때만 평가됩니다. 봉 중간에 trigger에 닿았다가 복귀한 움직임은 감지하지 못할 수 있습니다.
- 가상 수수료는 0이며 슬리피지, 부분 체결, 호가 잔량, 거래소별 최소 주문 금액·호가 단위·수량 정밀도는 재현하지 않습니다.
- 대기 매수는 현금을, 대기 매도·손절·익절은 자산을 예약합니다. OCO가 없으므로 같은 보유 수량 전체에 손절과 익절을 동시에 걸 수 없습니다.
- 실제 Trader의 손절·익절은 이번 기능의 지원 범위가 아니며 요청 시 미지원으로 거부됩니다.
```

Ensure the English README communicates the identical five constraints rather than merely linking to the Korean guide.

- [ ] **Step 3: Remove stale claims**

Replace any statement saying limit orders simply fill at the latest quote. Replace any wording that implies real Binance/OKX stop/OCO support. Keep the separate OKX demo-trading explanation, since it describes an exchange demo environment and not `SimulationTrader`.

- [ ] **Step 4: Check documentation consistency**

```bash
rg -n "OCO|트레일링|Trailing|stop-loss|손절|익절|지정가|Limit" \
  README.md README-ko-kr.md docs/exchanges-and-trading-ko.md
git diff --check
```

Expected: every support table agrees; no trailing/OCO or real conditional order is marked supported; `git diff --check` exits 0.

- [ ] **Step 5: Commit user documentation**

```bash
git add README.md README-ko-kr.md docs/exchanges-and-trading-ko.md
git commit -m "docs: describe virtual order support"
```

---

### Task 9: Run complete regression and completion checks

**Files:**
- Verify only; modify the smallest relevant test or implementation file if a failure reveals a requirement gap.

- [ ] **Step 1: Run the complete local unit and E2E suite**

```bash
env PYTHONPATH=. python3 -m pytest -q tests/unit_tests tests/e2e_tests
```

Expected: all tests pass. Record the exact pass/warning counts in the handoff. Existing unrelated worker-thread warnings must be reported rather than hidden; any new `SimulationTrader`, `TradingOperator`, strategy, or controller warning is a failure to investigate.

- [ ] **Step 2: Verify formatting and active-reference cleanup**

```bash
git diff --check
rg -n "pending_conditionals" smtm tests
test ! -e jupyter_notebook.md
test ! -e docs/smtm_class.png
rg -n "JptController|jpt_controller" \
  smtm tests README.md README-ko-kr.md docs \
  --glob '!docs/superpowers/**' \
  --glob '!docs/claw-branch-review.md' \
  --glob '!docs/public/release-notes.md'
```

Expected: `git diff --check` exits 0; both `rg` commands return no matches. Historical specs, plans, and old release-note entries are intentionally outside this active-reference check.

- [ ] **Step 3: Verify the approved support matrix against runtime declarations**

```bash
env PYTHONPATH=. python3 - <<'PY'
from smtm.trader.simulation_trader import SimulationTrader
from smtm.trader.upbit_trader import UpbitTrader
from smtm.trader.bithumb_trader import BithumbTrader
from smtm.trader.binance_trader import BinanceTrader
from smtm.trader.okx_trader import OkxTrader

assert SimulationTrader.SUPPORTED_ORD_TYPES == {
    "limit", "market", "stop_loss", "take_profit"
}
for trader in (UpbitTrader, BithumbTrader, BinanceTrader, OkxTrader):
    assert trader.SUPPORTED_ORD_TYPES == {"limit", "market"}
print("order support matrix verified")
PY
```

Expected: `order support matrix verified` and exit 0.

- [ ] **Step 4: Inspect the final change set**

```bash
git status --short
git diff --stat e3dd63f..HEAD
git log -8 --oneline
```

Expected: only the scoped runtime, tests, and documentation changes are present; no generated files, monitor output, profile data, secrets, or notebook experiment files were added.

- [ ] **Step 5: Resolve any regression in its owning task**

If Steps 1–4 reveal a requirement gap, return to the task that owns the affected behavior, add or tighten its regression test, make the smallest fix, and repeat that task's explicit staging and commit step. Then rerun all of Task 9 from Step 1. If verification is clean, do not create an empty commit.
