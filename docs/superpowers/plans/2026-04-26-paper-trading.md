# Paper Trading Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `--paper` flag that swaps the real exchange `Trader` for an in-memory `SimulationTrader` while keeping the existing `DataProvider` unchanged, so the entire LLM trading pipeline can be exercised against real-time quotes without placing real orders.

**Architecture:** Two orthogonal axes — data source picked by `--exchange`, trade destination picked by `--paper`. `SimulationTrader` implements the `Trader` ABC, exposes mutable accounting attributes for tests, and accepts an externally-injected market quote via `update_quote(currency, price)`. `LlmOperator._on_timer` extracts the last `primary_candle` close from `data_provider.get_info()` and pushes it via duck-typed `update_quote`; real exchange traders without that method are untouched. The existing test `FakeTrader` is retired so production code is the single source of paper-trading accounting.

**Tech Stack:** Python 3.9+, `unittest`, existing smtm package layout (`smtm/trader/`, `smtm/llm/`, `tests/unit_tests/`, `tests/e2e_tests/`).

**Spec:** [docs/superpowers/specs/2026-04-26-paper-trading-design.md](../specs/2026-04-26-paper-trading-design.md)

---

## File Structure

**Create:**
- `smtm/trader/simulation_trader.py` — `SimulationTrader(Trader)`. Owns balance/assets/quotes/order_history accounting and `update_quote` hook.
- `tests/unit_tests/simulation_trader_test.py` — 9 unit cases covering buy/sell happy paths, failure modes, average cost, no-quote rejection, quote-injection priority, cancel no-ops, account info shape.
- `tests/unit_tests/llm_operator_paper_test.py` — 4 unit cases covering quote sync hook (duck-typed dispatch, missing `primary_candle`, `chat()` re-sync from cache, no-op when no cache).

**Modify:**
- `smtm/trader/trader_factory.py` — add `paper=False` parameter; when true, return `SimulationTrader`.
- `smtm/__main__.py` — add `--paper` flag; pass to `Controller`.
- `smtm/controller/controller.py` — accept `paper`; pass to factory; print warning banner.
- `smtm/llm/llm_operator.py` — store `self.trader`, cache `self.last_market_data`, add `_sync_trader_quote(market_data)`; call from `_on_timer` and from `chat()`.
- `tests/e2e_tests/fake_llm_client.py` — delete the `FakeTrader` class only; keep `FakeLlmClient` and `FakeDataProvider`.
- `tests/e2e_tests/e2e_chat_trading_test.py` — switch `FakeTrader` → `SimulationTrader`; insert `update_quote` calls at fixtures and at the price-change point in `test_buy_then_sell_with_profit`.
- `README.md` — add `--paper` row to Options table; add `### Paper Trading` subsection; add one-line note under "Supported Exchanges & Data Providers".
- `README-ko-kr.md` — mirror the EN changes in Korean.

Each task below produces a self-contained, committable change.

---

### Task 1: SimulationTrader — class skeleton + buy happy path (TDD)

**Files:**
- Create: `smtm/trader/simulation_trader.py`
- Create: `tests/unit_tests/simulation_trader_test.py`

- [ ] **Step 1: Write the failing test for buy happy path**

Create `tests/unit_tests/simulation_trader_test.py`:

```python
import unittest
from smtm.trader.simulation_trader import SimulationTrader


class SimulationTraderBuyTest(unittest.TestCase):
    def test_buy_success_debits_balance_and_adds_asset(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)

        results = []
        trader.send_request(
            [{"id": "r1", "type": "buy", "price": 49000, "amount": 0.001,
              "date_time": "2026-04-26T00:00:00"}],
            results.append,
        )

        self.assertEqual(len(results), 1)
        result = results[0]
        self.assertEqual(result["state"], "done")
        # Quote-priority: fill price is the injected quote, not the request price.
        self.assertEqual(result["price"], 50000)
        self.assertEqual(result["amount"], 0.001)
        self.assertEqual(trader.balance, 500000 - (50000 * 0.001))
        self.assertEqual(trader.assets["BTC"], (50000, 0.001))
        self.assertEqual(len(trader.order_history), 1)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: `ImportError` / `ModuleNotFoundError` for `smtm.trader.simulation_trader`.

- [ ] **Step 3: Write minimal implementation**

Create `smtm/trader/simulation_trader.py`:

```python
from typing import Any, Callable, Dict, List

from ..log_manager import LogManager
from .trader import Trader


class SimulationTrader(Trader):
    """In-memory paper-trading Trader.

    Real-time fill price is injected via update_quote(currency, price).
    LLM-supplied request price is ignored. State is in-memory only.
    """

    NAME = "Simulation"
    CODE = "SIM"

    def __init__(self, budget: int = 500000, currency: str = "BTC",
                 commission_ratio: float = 0.0):
        self.logger = LogManager.get_logger("SimulationTrader")
        self.balance: float = float(budget)
        self.currency = currency
        self.commission_ratio = commission_ratio
        self.assets: Dict[str, tuple] = {}
        self.quotes: Dict[str, float] = {}
        self.order_history: List[Dict[str, Any]] = []

    def update_quote(self, currency: str, price: float) -> None:
        self.quotes[currency] = float(price)

    def send_request(self, request_list: List[Dict[str, Any]],
                     callback: Callable[[Dict[str, Any]], None]) -> None:
        for req in request_list:
            currency = self.currency
            result = dict(req)
            result["request"] = dict(req)

            quote = self.quotes.get(currency)
            if quote is None:
                result["state"] = "failed"
                result["msg"] = "시세 없음"
                result["balance"] = self.balance
                self.order_history.append(result)
                callback(result)
                continue

            fill_price = quote
            amount = req["amount"]
            trade_value = fill_price * amount
            result["price"] = fill_price

            if req["type"] == "buy":
                if trade_value > self.balance:
                    result["state"] = "failed"
                    result["msg"] = "잔고 부족"
                else:
                    self.balance -= trade_value
                    if currency in self.assets:
                        old_price, old_amount = self.assets[currency]
                        new_amount = old_amount + amount
                        new_avg = (old_price * old_amount + fill_price * amount) / new_amount
                        self.assets[currency] = (new_avg, new_amount)
                    else:
                        self.assets[currency] = (fill_price, amount)
                    result["state"] = "done"
                    result["msg"] = "success"
            elif req["type"] == "sell":
                holding = self.assets.get(currency)
                if holding is None or holding[1] < amount:
                    result["state"] = "failed"
                    result["msg"] = "보유 수량 부족"
                else:
                    self.balance += trade_value
                    old_price, old_amount = holding
                    remaining = old_amount - amount
                    if remaining <= 0:
                        del self.assets[currency]
                    else:
                        self.assets[currency] = (old_price, remaining)
                    result["state"] = "done"
                    result["msg"] = "success"
            else:
                result["state"] = "failed"
                result["msg"] = f"unknown type: {req['type']}"

            result["balance"] = self.balance
            self.order_history.append(result)
            self.logger.info(
                f"[SIM] {req['type']} {currency} @{fill_price} x {amount} "
                f"-> {result['state']}, balance={self.balance}"
            )
            callback(result)

    def cancel_request(self, request_id: str) -> None:
        return

    def cancel_all_requests(self) -> None:
        return

    def get_account_info(self) -> Dict[str, Any]:
        return {
            "balance": self.balance,
            "asset": dict(self.assets),
            "quote": dict(self.quotes),
        }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: 1 passed.

- [ ] **Step 5: Commit**

```bash
git add smtm/trader/simulation_trader.py tests/unit_tests/simulation_trader_test.py
git commit -m "[feat] add SimulationTrader with buy happy path"
```

---

### Task 2: SimulationTrader — buy failure modes

**Files:**
- Test: `tests/unit_tests/simulation_trader_test.py`

- [ ] **Step 1: Append failing tests for buy failure modes**

Append to `tests/unit_tests/simulation_trader_test.py`:

```python
class SimulationTraderBuyFailureTest(unittest.TestCase):
    def test_buy_with_insufficient_balance_fails(self):
        trader = SimulationTrader(budget=100, currency="BTC")
        trader.update_quote("BTC", 50000)

        results = []
        trader.send_request(
            [{"id": "r1", "type": "buy", "price": 50000, "amount": 1.0,
              "date_time": "2026-04-26T00:00:00"}],
            results.append,
        )

        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["msg"], "잔고 부족")
        self.assertEqual(trader.balance, 100)
        self.assertNotIn("BTC", trader.assets)
        self.assertEqual(len(trader.order_history), 1)

    def test_buy_without_quote_fails(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        # No update_quote called.

        results = []
        trader.send_request(
            [{"id": "r1", "type": "buy", "price": 50000, "amount": 0.001,
              "date_time": "2026-04-26T00:00:00"}],
            results.append,
        )

        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["msg"], "시세 없음")
        self.assertEqual(trader.balance, 500000)
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: 3 passed (the implementation already covers these paths).

- [ ] **Step 3: Commit**

```bash
git add tests/unit_tests/simulation_trader_test.py
git commit -m "[test] cover SimulationTrader buy failure modes"
```

---

### Task 3: SimulationTrader — sell paths and average cost

**Files:**
- Test: `tests/unit_tests/simulation_trader_test.py`

- [ ] **Step 1: Append failing tests for sell paths and average cost**

Append to `tests/unit_tests/simulation_trader_test.py`:

```python
class SimulationTraderSellTest(unittest.TestCase):
    def _trader_with_position(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        trader.send_request(
            [{"id": "buy", "type": "buy", "price": 50000, "amount": 0.001,
              "date_time": "t"}],
            lambda r: None,
        )
        return trader

    def test_sell_full_holding_removes_asset_entry(self):
        trader = self._trader_with_position()
        trader.update_quote("BTC", 60000)

        results = []
        trader.send_request(
            [{"id": "sell", "type": "sell", "price": 60000, "amount": 0.001,
              "date_time": "t"}],
            results.append,
        )

        self.assertEqual(results[0]["state"], "done")
        self.assertNotIn("BTC", trader.assets)
        # 500000 - 50 (buy) + 60 (sell) = 500010
        self.assertAlmostEqual(trader.balance, 500010.0, places=4)

    def test_sell_with_insufficient_holding_fails(self):
        trader = self._trader_with_position()  # holds 0.001 BTC
        trader.update_quote("BTC", 60000)

        results = []
        trader.send_request(
            [{"id": "sell", "type": "sell", "price": 60000, "amount": 0.5,
              "date_time": "t"}],
            results.append,
        )

        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["msg"], "보유 수량 부족")
        self.assertEqual(trader.assets["BTC"], (50000, 0.001))


class SimulationTraderAverageCostTest(unittest.TestCase):
    def test_two_buys_yield_volume_weighted_average(self):
        trader = SimulationTrader(budget=500000, currency="BTC")

        trader.update_quote("BTC", 40000)
        trader.send_request(
            [{"id": "b1", "type": "buy", "price": 40000, "amount": 1.0,
              "date_time": "t"}],
            lambda r: None,
        )
        trader.update_quote("BTC", 60000)
        trader.send_request(
            [{"id": "b2", "type": "buy", "price": 60000, "amount": 1.0,
              "date_time": "t"}],
            lambda r: None,
        )

        avg, qty = trader.assets["BTC"]
        self.assertAlmostEqual(avg, 50000.0, places=4)
        self.assertAlmostEqual(qty, 2.0, places=4)
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: 6 passed.

- [ ] **Step 3: Commit**

```bash
git add tests/unit_tests/simulation_trader_test.py
git commit -m "[test] cover SimulationTrader sell and average-cost paths"
```

---

### Task 4: SimulationTrader — quote priority, cancel no-ops, account info

**Files:**
- Test: `tests/unit_tests/simulation_trader_test.py`

- [ ] **Step 1: Append failing tests for the remaining cases**

Append to `tests/unit_tests/simulation_trader_test.py`:

```python
class SimulationTraderQuotePriorityTest(unittest.TestCase):
    def test_fill_price_is_injected_quote_not_request_price(self):
        """LLM may pass any number as price; trader uses the injected market quote."""
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)

        results = []
        trader.send_request(
            [{"id": "r1", "type": "buy", "price": 1, "amount": 0.001,
              "date_time": "t"}],
            results.append,
        )

        self.assertEqual(results[0]["price"], 50000)
        self.assertEqual(trader.balance, 500000 - 50)


class SimulationTraderCancelTest(unittest.TestCase):
    def test_cancel_request_unknown_id_is_silent_noop(self):
        trader = SimulationTrader()
        trader.cancel_request("does-not-exist")  # must not raise

    def test_cancel_all_is_silent_noop(self):
        trader = SimulationTrader()
        trader.cancel_all_requests()  # must not raise


class SimulationTraderAccountInfoTest(unittest.TestCase):
    def test_account_info_shape(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)

        info = trader.get_account_info()

        self.assertEqual(set(info.keys()), {"balance", "asset", "quote"})
        self.assertEqual(info["balance"], 500000)
        self.assertEqual(info["asset"], {})
        self.assertEqual(info["quote"], {"BTC": 50000})
```

- [ ] **Step 2: Run tests**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: 10 passed (cumulative — 1 + 2 + 3 + 4 = 10).

- [ ] **Step 3: Commit**

```bash
git add tests/unit_tests/simulation_trader_test.py
git commit -m "[test] cover SimulationTrader quote priority, cancel, account info"
```

---

### Task 5: TraderFactory — wire `paper=True` to SimulationTrader

**Files:**
- Modify: `smtm/trader/trader_factory.py`
- Test: `tests/unit_tests/simulation_trader_test.py`

- [ ] **Step 1: Write failing test for factory behaviour**

Append to `tests/unit_tests/simulation_trader_test.py`:

```python
from smtm.trader.trader_factory import TraderFactory


class TraderFactoryPaperFlagTest(unittest.TestCase):
    def test_paper_flag_returns_simulation_trader(self):
        trader = TraderFactory.create("UPB", budget=500000, currency="BTC", paper=True)
        self.assertIsInstance(trader, SimulationTrader)
        self.assertEqual(trader.balance, 500000)

    def test_paper_flag_overrides_any_exchange_code(self):
        trader = TraderFactory.create("BTH", budget=300000, currency="ETH", paper=True)
        self.assertIsInstance(trader, SimulationTrader)
        self.assertEqual(trader.currency, "ETH")

    def test_paper_false_uses_real_trader(self):
        trader = TraderFactory.create("UPB", budget=500000, currency="BTC", paper=False)
        self.assertNotIsInstance(trader, SimulationTrader)
        self.assertEqual(trader.NAME, "Upbit")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py::TraderFactoryPaperFlagTest -v`
Expected: FAIL — `create()` got an unexpected keyword argument `paper`.

- [ ] **Step 3: Modify the factory**

Replace [smtm/trader/trader_factory.py](smtm/trader/trader_factory.py) with:

```python
from .upbit_trader import UpbitTrader
from .bithumb_trader import BithumbTrader
from .simulation_trader import SimulationTrader


class TraderFactory:
    """
    Trader 정보 조회 및 생성을 담당하는 Factory 클래스
    Factory class responsible for retrieving and creating Trader information
    """

    TRADER_LIST = [
        UpbitTrader,
        BithumbTrader,
    ]

    @staticmethod
    def create(code, budget=50000, currency="BTC", commission_ratio=0.0005, paper=False):
        if paper:
            return SimulationTrader(
                budget=budget,
                currency=currency,
                commission_ratio=commission_ratio,
            )
        for trader in TraderFactory.TRADER_LIST:
            if trader.CODE == code:
                return trader(
                    budget=budget,
                    currency=currency,
                    commission_ratio=commission_ratio,
                )
        return None

    @staticmethod
    def get_name(code):
        for trader in TraderFactory.TRADER_LIST:
            if trader.CODE == code:
                return trader.NAME
        return None

    @staticmethod
    def get_all_trader_info():
        all_trader = []
        for trader in TraderFactory.TRADER_LIST:
            all_trader.append(
                {
                    "name": trader.NAME,
                    "code": trader.CODE,
                    "class": trader,
                }
            )
        return all_trader
```

- [ ] **Step 4: Run all simulation_trader tests**

Run: `python -m pytest tests/unit_tests/simulation_trader_test.py -v`
Expected: 13 passed.

- [ ] **Step 5: Commit**

```bash
git add smtm/trader/trader_factory.py tests/unit_tests/simulation_trader_test.py
git commit -m "[feat] add paper flag to TraderFactory.create"
```

---

### Task 6: LlmOperator — quote sync hook (TDD)

**Files:**
- Create: `tests/unit_tests/llm_operator_paper_test.py`
- Modify: `smtm/llm/llm_operator.py`

- [ ] **Step 1: Write failing tests for the quote sync hook**

Create `tests/unit_tests/llm_operator_paper_test.py`:

```python
import unittest
from unittest.mock import MagicMock

from smtm.llm.llm_operator import LlmOperator


class _StubTraderWithUpdateQuote:
    def __init__(self):
        self.calls = []

    def update_quote(self, currency, price):
        self.calls.append((currency, price))


class _StubTraderWithoutUpdateQuote:
    """Mimics UpbitTrader / BithumbTrader — no update_quote attribute."""
    pass


def _make_operator(trader):
    llm = MagicMock()
    op = LlmOperator(llm, {"exchange": "UPB", "currency": "BTC", "budget": 500000})
    # Bypass setup_tools — only need the trader handle for these tests.
    op.trader = trader
    return op


class LlmOperatorQuoteSyncTest(unittest.TestCase):
    def test_sync_calls_update_quote_with_last_primary_candle_close(self):
        trader = _StubTraderWithUpdateQuote()
        op = _make_operator(trader)

        market_data = [
            {"type": "primary_candle", "closing_price": 50500000, "market": "BTC"},
            {"type": "news", "title": "ignored"},
        ]
        op._sync_trader_quote(market_data)

        self.assertEqual(trader.calls, [("BTC", 50500000)])

    def test_sync_is_noop_when_trader_has_no_update_quote(self):
        trader = _StubTraderWithoutUpdateQuote()
        op = _make_operator(trader)

        # Must not raise.
        op._sync_trader_quote([{"type": "primary_candle", "closing_price": 1}])

    def test_sync_is_noop_when_no_primary_candle(self):
        trader = _StubTraderWithUpdateQuote()
        op = _make_operator(trader)

        op._sync_trader_quote([{"type": "news", "title": "no candle"}])

        self.assertEqual(trader.calls, [])

    def test_chat_resyncs_from_cached_market_data(self):
        trader = _StubTraderWithUpdateQuote()
        op = _make_operator(trader)
        op.last_market_data = [
            {"type": "primary_candle", "closing_price": 51000000}
        ]

        # FakeLLM returns immediately with no tool calls
        from smtm.llm.llm_client import LlmResponse
        op.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 1, "output_tokens": 1},
        )
        op.chat("hi")

        self.assertEqual(trader.calls, [("BTC", 51000000)])

    def test_chat_without_cached_data_does_not_sync_or_raise(self):
        trader = _StubTraderWithUpdateQuote()
        op = _make_operator(trader)
        op.last_market_data = None

        from smtm.llm.llm_client import LlmResponse
        op.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 1, "output_tokens": 1},
        )
        op.chat("hi")

        self.assertEqual(trader.calls, [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/unit_tests/llm_operator_paper_test.py -v`
Expected: 5 errors — `_sync_trader_quote` and `last_market_data` do not exist.

- [ ] **Step 3: Modify `smtm/llm/llm_operator.py`**

Three edits in [smtm/llm/llm_operator.py](smtm/llm/llm_operator.py):

**Edit A** — in `__init__`, after the existing `self.data_provider = None` line, add:

```python
        # Trader handle (set by setup_tools) and cached market data for quote sync
        self.trader = None
        self.last_market_data = None
```

**Edit B** — in `setup_tools`, inside the `if trader:` block, add `self.trader = trader` as the first line so it becomes:

```python
        if trader:
            self.trader = trader
            self.tool_router.register(TradeTool(trader, self.system_monitor))
            self.tool_router.register(PortfolioTool(trader))
            self.tool_router.register(PerformanceTool(
                self.system_monitor, trader, self.budget,
            ))
```

**Edit C** — inside `_on_timer`, immediately after `self.system_monitor.log_market_data(market_data)`, add the cache + sync calls so the block becomes:

```python
            market_data = None
            if self.data_provider:
                market_data = self.data_provider.get_info()
                self.system_monitor.log_market_data(market_data)
                self.last_market_data = market_data
                self._sync_trader_quote(market_data)
```

**Edit D** — at the start of `chat`, before appending to `conversation_history`, add the resync call:

```python
    def chat(self, message: str) -> str:
        """단일 인터페이스 — 사용자 요청 및 주기적 판단 모두 처리"""
        if self.last_market_data:
            self._sync_trader_quote(self.last_market_data)
        self.conversation_history.append({"role": "user", "content": message})
```

**Edit E** — add the helper method at the end of the class (before the trailing newline):

```python
    def _sync_trader_quote(self, market_data) -> None:
        """Push last primary_candle close to trader if it supports update_quote (paper mode)."""
        if self.trader is None or not hasattr(self.trader, "update_quote"):
            return
        if not market_data:
            return
        for item in market_data:
            if isinstance(item, dict) and item.get("type") == "primary_candle":
                currency = self.config.get("currency", "BTC")
                self.trader.update_quote(currency, item["closing_price"])
                return
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/unit_tests/llm_operator_paper_test.py -v`
Expected: 5 passed.

- [ ] **Step 5: Run the full unit suite to confirm no regression**

Run: `python -m pytest tests/unit_tests/ -v`
Expected: all green (existing + new tests).

- [ ] **Step 6: Commit**

```bash
git add smtm/llm/llm_operator.py tests/unit_tests/llm_operator_paper_test.py
git commit -m "[feat] add quote-sync hook in LlmOperator for paper trading"
```

---

### Task 7: Migrate e2e tests to SimulationTrader

**Files:**
- Modify: `tests/e2e_tests/fake_llm_client.py`
- Modify: `tests/e2e_tests/e2e_chat_trading_test.py`

- [ ] **Step 1: Delete the FakeTrader class**

In [tests/e2e_tests/fake_llm_client.py](tests/e2e_tests/fake_llm_client.py), remove the entire `class FakeTrader:` block (currently lines ~41–101). Keep `FakeLlmClient` and `FakeDataProvider` intact.

- [ ] **Step 2: Update e2e test imports**

In [tests/e2e_tests/e2e_chat_trading_test.py](tests/e2e_tests/e2e_chat_trading_test.py), change the import line from:

```python
from .fake_llm_client import FakeLlmClient, FakeTrader, FakeDataProvider
```

to:

```python
from smtm.trader.simulation_trader import SimulationTrader
from .fake_llm_client import FakeLlmClient, FakeDataProvider
```

- [ ] **Step 3: Update the three `_make_operator` helpers**

There are three identical helpers (one per test class). In each, replace:

```python
        self.trader = FakeTrader(balance=budget)
```

with:

```python
        self.trader = SimulationTrader(budget=budget)
        self.trader.update_quote("BTC", 50000)
```

This sets the default fill price all current tests rely on.

- [ ] **Step 4: Adjust the price-change point in `test_buy_then_sell_with_profit`**

Find the line `self.trader.quotes["BTC"] = 60000  # 가격 상승` in `test_buy_then_sell_with_profit` and replace it with:

```python
        self.trader.update_quote("BTC", 60000)  # 가격 상승
```

(Functionally equivalent — `update_quote` writes to the same `quotes` dict — but uses the public API.)

- [ ] **Step 5: Run e2e tests**

Run: `python -m pytest tests/e2e_tests/ -v`
Expected: all e2e tests pass. The arithmetic in assertions (e.g. `499500`, `500100`) is unchanged because `commission_ratio=0.0` and the injected quote matches each test's scripted `price`.

- [ ] **Step 6: Run the full test suite**

Run: `python -m pytest tests/unit_tests/ tests/e2e_tests/ -v`
Expected: all green.

- [ ] **Step 7: Commit**

```bash
git add tests/e2e_tests/fake_llm_client.py tests/e2e_tests/e2e_chat_trading_test.py
git commit -m "[refactor] migrate e2e tests to SimulationTrader, retire FakeTrader"
```

---

### Task 8: CLI flag + Controller pass-through + paper banner

**Files:**
- Modify: `smtm/__main__.py`
- Modify: `smtm/controller/controller.py`

- [ ] **Step 1: Add `--paper` flag to argparse**

In [smtm/__main__.py](smtm/__main__.py), add immediately after the existing `--exchange` argument (around line 38):

```python
    parser.add_argument(
        "--paper",
        action="store_true",
        help="paper trading mode — simulated trader, real-time quotes",
    )
```

- [ ] **Step 2: Pass `paper` into Controller**

In [smtm/__main__.py](smtm/__main__.py), inside the `if args.mode == 0:` branch, change the `Controller(...)` construction to include `paper=args.paper`:

```python
        controller = Controller(
            budget=args.budget,
            interval=args.term,
            currency=args.currency,
            exchange=args.exchange,
            paper=args.paper,
        )
```

- [ ] **Step 3: Update Controller signature, factory call, and banner**

In [smtm/controller/controller.py](smtm/controller/controller.py):

**Edit A** — change the `__init__` signature and store `paper`:

```python
    def __init__(self, interval=60, budget=500000, currency="BTC", exchange="UPB",
                 paper=False):
        self.logger = LogManager.get_logger("Controller")
        self.terminating = False
        self.interval = float(interval)
        self.budget = int(budget)
        self.currency = currency
        self.exchange = exchange
        self.paper = paper
        LogManager.set_stream_level(Config.operation_log_level)
```

**Edit B** — update the `TraderFactory.create` call:

```python
        trader = TraderFactory.create(
            self.exchange, budget=self.budget, currency=self.currency,
            paper=self.paper,
        )
```

**Edit C** — add the paper banner immediately after the existing exchange/currency/budget print line:

```python
        print(f"exchange: {self.exchange}, currency: {self.currency}, budget: {self.budget}")
        if self.paper:
            print("!! PAPER TRADING MODE — no real orders will be placed")
        print("'start'를 입력하면 자동 매매가 시작됩니다")
```

- [ ] **Step 4: Smoke test the CLI wiring**

Run a quick non-interactive invocation that exits after import — argparse should accept `--paper` without error:

```bash
python -m smtm --paper --version
```

Expected: prints version string (e.g. `smtm version: ...`) and exits 0. No argparse error.

- [ ] **Step 5: Run the full test suite to confirm no regression**

Run: `python -m pytest tests/unit_tests/ tests/e2e_tests/ -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add smtm/__main__.py smtm/controller/controller.py
git commit -m "[feat] add --paper CLI flag and Controller wiring"
```

---

### Task 9: README updates (English + Korean)

**Files:**
- Modify: `README.md`
- Modify: `README-ko-kr.md`

- [ ] **Step 1: Add `--paper` row to the English Options table**

In [README.md](README.md), inside the Options table, add a new row right after the `--log` row:

```markdown
| `--paper` | Paper trading mode — uses real-time quotes, simulated balance | False |
```

- [ ] **Step 2: Add the Paper Trading subsection (English)**

In [README.md](README.md), insert this new subsection immediately before `### Supported Exchanges & Data Providers`:

````markdown
### Paper Trading

Run any data feed against a simulated trader — real-time market prices, in-memory balance and assets, no real exchange API calls.

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB --paper
```

Combine `--paper` with any data provider:

```bash
python -m smtm --mode 0 --currency BTC --exchange UFC --paper
```

Notes:
- Quotes are pulled from the DataProvider's last candle. Issue `start` at least once so the first tick fills the trader's quote before any manual trade.
- State is in-memory only — closing the CLI resets balance and assets.
- Commission is currently 0 in simulation.

````

- [ ] **Step 3: Add the cross-axis note under the Supported Exchanges table**

In [README.md](README.md), find the line `Registered in `smtm/data/data_provider_factory.py` and `smtm/trader/trader_factory.py`.` and append immediately below it:

```markdown
Any code in this table can be combined with `--paper` to route orders through the in-memory `SimulationTrader` instead of the real exchange.
```

- [ ] **Step 4: Mirror the changes in Korean README**

In [README-ko-kr.md](README-ko-kr.md), apply the same three changes in Korean:

(a) Add a `--paper` row to the 옵션 table:

```markdown
| `--paper` | 페이퍼 트레이딩 모드 — 실시간 시세 + 가상 잔고 사용 | False |
```

(b) Insert before `### 지원 거래소 및 데이터 제공자`:

````markdown
### 페이퍼 트레이딩

어떤 데이터 피드와도 결합해 가상 트레이더로 실행할 수 있습니다 — 실시간 시세, 메모리상의 잔고와 자산, 실거래소 API 호출 없음.

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB --paper
```

`--paper`는 어떤 데이터 제공자와도 함께 사용할 수 있습니다:

```bash
python -m smtm --mode 0 --currency BTC --exchange UFC --paper
```

참고:
- 시세는 DataProvider의 마지막 캔들에서 가져옵니다. 수동 거래 전에 `start`를 한 번 이상 입력해 첫 틱이 트레이더에 시세를 주입하도록 하세요.
- 상태는 메모리에만 보존됩니다 — CLI를 종료하면 잔고와 자산이 초기화됩니다.
- 시뮬레이션의 수수료는 현재 0입니다.

````

(c) Add the cross-axis note under the Korean exchange table — find `Registered in `smtm/data/data_provider_factory.py` and `smtm/trader/trader_factory.py`.` (or its Korean equivalent if translated; otherwise the same English line is present in `README-ko-kr.md`) and append below it:

```markdown
이 표의 모든 코드는 `--paper`와 결합해 실거래소 대신 인메모리 `SimulationTrader`로 주문을 보낼 수 있습니다.
```

- [ ] **Step 5: Verify no test regression (docs only, but run anyway)**

Run: `python -m pytest tests/unit_tests/ tests/e2e_tests/ -v`
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add README.md README-ko-kr.md
git commit -m "[docs] document paper trading mode in EN and KO READMEs"
```

---

### Task 10: Final integration check

**Files:** none modified — verification only.

- [ ] **Step 1: Confirm the full test suite passes**

Run: `python -m pytest tests/unit_tests/ tests/e2e_tests/ -v`
Expected: all green (originally passing tests + 10 new SimulationTrader unit tests + 3 factory tests + 5 LlmOperator paper tests + migrated e2e tests).

- [ ] **Step 2: CLI smoke test — paper banner appears**

Without an `SMTM_LLM_API_KEY` environment variable set, run:

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB --paper
```

Expected output: the banner `##### smtm LLM trading system is initialized #####`, then `exchange: UPB, currency: BTC, budget: 500000`, then `!! PAPER TRADING MODE — no real orders will be placed`. Then either the input prompt (if API key is set) or `SMTM_LLM_API_KEY 환경변수를 설정해주세요` (if not set). If you see the prompt, type `q` to exit.

- [ ] **Step 3: Verify `--help` reflects the new flag**

Run: `python -m smtm --help`
Expected: the help output lists `--paper` with its description.

- [ ] **Step 4: Inspect git log**

Run: `git log --oneline master..HEAD`
Expected: the new commits from Tasks 1–9 in order, no extra commits.

- [ ] **Step 5: No further commit — verification only**

Nothing to commit in this task.

---

## Definition of Done (from spec, restated)

- [ ] `python -m pytest tests/unit_tests/simulation_trader_test.py` — 13 cases passing.
- [ ] `python -m pytest tests/unit_tests/llm_operator_paper_test.py` — 5 cases passing.
- [ ] `python -m pytest tests/e2e_tests/` — all green after migration.
- [ ] `python -m pytest tests/unit_tests/` — no regressions.
- [ ] `python -m smtm --mode 0 --currency BTC --exchange UPB --paper` prints the paper warning banner.
- [ ] `--paper` documented in both `README.md` and `README-ko-kr.md`.
