# Paper Trading Mode (`SimulationTrader`) — Design

**Status:** Approved
**Date:** 2026-04-26
**Branch:** `claw`
**Author:** msaltnet (with brainstorming via Claude)

## 1. Goal

Add a **paper trading mode** to smtm that lets users exercise the entire LLM-driven trading pipeline against **real-time market quotes** but with **simulated orders** — no real exchange API calls, no real funds at risk.

The core value proposition: every DataProvider in the catalog (`UPB`, `UMN`, `USC`, `UFC`, ...) becomes usable for safe end-to-end runs without an Upbit/Bithumb account, and the LLM's decisions can be observed against live market dynamics.

## 2. Architecture

Two orthogonal axes:

- **Data source — where** — controlled by `--exchange CODE`. Picks the DataProvider only.
- **Trading destination — what** — controlled by `--paper` flag. When set, the Trader is replaced by `SimulationTrader` regardless of `--exchange`.

```
DataProvider (UPB / UMN / UFC ...) ──┬──> LlmOperator ──> LLM ──> Tool ──> SimulationTrader.send_request()
                                     │                                            ▲
                                     └──> LlmOperator._on_timer ──update_quote────┘
```

Every tick, `LlmOperator._on_timer` already pulls market data via `data_provider.get_info()`. We piggyback on that call: extract the last `primary_candle.closing_price` and push it to the trader via `update_quote(currency, price)` if the trader supports it (duck-typed). Real exchange traders (`UpbitTrader`, `BithumbTrader`) have no such method, so this is a no-op for them — no branching needed.

The simulator ignores the `price` argument the LLM passes to `execute_trade` and uses the injected quote as the fill price. This guarantees fills reflect the actual market the LLM was reasoning about, not whatever number the LLM happened to type.

## 3. Components

### 3.1 New: `smtm/trader/simulation_trader.py`

A production-quality `Trader` ABC implementation. Implements all four abstract methods (`send_request`, `cancel_request`, `cancel_all_requests`, `get_account_info`) and exposes mutable state attributes (`balance`, `assets`, `order_history`, `quotes`) that tests can assert against directly.

```python
class SimulationTrader(Trader):
    NAME = "Simulation"
    CODE = "SIM"

    def __init__(self, budget: int = 500000, currency: str = "BTC",
                 commission_ratio: float = 0.0):
        self.balance: float = budget
        self.currency = currency
        self.commission_ratio = commission_ratio   # accepted but applied as 0 by default
        self.assets: dict[str, tuple[float, float]] = {}
        self.quotes: dict[str, float] = {}
        self.order_history: list[dict] = []

    def send_request(self, request_list, callback): ...
    def cancel_request(self, request_id): ...           # no-op
    def cancel_all_requests(self): ...                  # no-op
    def get_account_info(self): ...

    def update_quote(self, currency: str, price: float) -> None:
        self.quotes[currency] = price
```

**Fill rules:**

- **Buy** — fill price is `quotes[currency]` (LLM's `price` argument is ignored). If `quotes[currency]` is missing, fail with `msg="시세 없음"`. If `fill_price * amount > balance`, fail with `msg="잔고 부족"`. On success, decrement balance, update average cost in `assets[currency]`.
- **Sell** — fill price is `quotes[currency]`. If `quotes[currency]` is missing, fail. If holding < amount, fail with `msg="보유 수량 부족"`. On success, increment balance, decrement holdings (delete the asset entry when holdings reach 0).
- **Failure semantics** — every failure is reported via the callback as `state="failed"` with a Korean `msg`. Failures are also appended to `order_history` for parity with successes. **No exceptions are raised** — this matches `UpbitTrader`/`BithumbTrader` callback semantics.
- **Cancel** — orders are filled instantly in simulation, so there is nothing to cancel. `cancel_request` and `cancel_all_requests` are no-ops; unknown ids pass silently.

Commission is wired in (`commission_ratio` parameter) but defaults to **0** — applied as 0 throughout this PR. This keeps test assertion arithmetic identical to the existing `FakeTrader` and defers the commission model to a follow-up.

### 3.2 Modified: `smtm/trader/trader_factory.py`

```python
@staticmethod
def create(code, budget=50000, currency="BTC",
           commission_ratio=0.0005, paper=False):
    if paper:
        return SimulationTrader(budget=budget, currency=currency,
                                commission_ratio=commission_ratio)
    # existing branch unchanged
```

`SimulationTrader` is **not** added to `TRADER_LIST` — it is selected by the `paper` flag, not by a code. This avoids polluting the exchange-code namespace and prevents accidental selection. The factory still passes `commission_ratio` through, but `SimulationTrader` applies it as 0 in this PR (see Section 9).

### 3.3 Modified: `smtm/__main__.py`

```python
parser.add_argument("--paper", action="store_true",
                    help="paper trading mode (simulation trader, real-time quotes)")
```

Passed through to `Controller(..., paper=args.paper)`.

### 3.4 Modified: `smtm/controller/controller.py`

- `__init__` gains `paper: bool = False`.
- `TraderFactory.create(...)` is called with `paper=self.paper`.
- After the existing initialization banner, when `paper` is true, print a single conspicuous warning line: `!! PAPER TRADING MODE — no real orders will be placed`.

### 3.5 Modified: `smtm/llm/llm_operator.py`

Three small additions:

1. `setup_tools(trader=...)` stores `self.trader = trader` (currently the trader is passed only into tools).
2. `self.last_market_data` cache field, populated at the end of every `_on_timer`.
3. New helper `_sync_trader_quote(market_data)` that:
   - Returns early if `self.trader` is None or lacks `update_quote` (duck-typed).
   - Iterates `market_data` (a list of typed dicts) for the first item with `type == "primary_candle"` and calls `trader.update_quote(currency, item["closing_price"])`.
4. `_on_timer` calls `_sync_trader_quote(market_data)` immediately after `log_market_data`.
5. `chat()` calls `_sync_trader_quote(self.last_market_data)` on entry, so user-driven trades after at least one tick still see a fresh quote without re-hitting the data provider.

If the user issues a buy/sell via `chat()` before `start_trading()` has run a single tick, `last_market_data` is None and the simulator returns `state="failed", msg="시세 없음"`. The Controller surfaces this through the LLM's response.

## 4. Data flow — concrete example

1. User runs `python -m smtm --mode 0 --currency BTC --exchange UPB --paper --budget 500000`.
2. Controller prints `!! PAPER TRADING MODE` warning.
3. User types `start`. `LlmOperator.start_trading()` arms the timer.
4. Timer fires:
   - `data_provider.get_info()` returns `[{"type":"primary_candle", "closing_price":50000000, ...}]`.
   - `_sync_trader_quote` extracts 50000000 and calls `trader.update_quote("BTC", 50000000)`.
   - `last_market_data` is cached.
   - Periodic prompt is built and sent to the LLM.
5. LLM calls `execute_trade(action=buy, currency=BTC, price=49000000, amount=0.001)`.
6. `TradeTool` → `SimulationTrader.send_request`.
7. Trader uses `quotes["BTC"] = 50000000` (not 49000000) as fill price. `0.001 * 50000000 = 50000` ≤ 500000 → success. Balance becomes 450000, `assets["BTC"] = (50000000, 0.001)`. Callback fires with `state="done"`.
8. `SystemMonitor` records the trade. LLM sees the result, may continue or end the turn.

## 5. Error handling

| Scenario | SimulationTrader behaviour | Surfaced to user |
|---|---|---|
| Buy with insufficient balance | `state="failed"`, `msg="잔고 부족"` callback; failure recorded in `order_history` | LLM sees tool result, mentions in reply |
| Sell with insufficient holdings | `state="failed"`, `msg="보유 수량 부족"` | Same |
| Trade before any quote injected | `state="failed"`, `msg="시세 없음"` | LLM should advise running `start` first |
| Negative/zero amount, negative price | Blocked upstream by SafetyGuard / TradeTool — never reaches SimulationTrader | Existing SafetyGuard message |
| `cancel_request` for unknown id | Silent no-op | — |

No exceptions ever leave `SimulationTrader`. Trader ABC's contract is callback-based, and `UpbitTrader`/`BithumbTrader` follow the same convention.

## 6. Testing

### 6.1 New: `tests/unit_tests/simulation_trader_test.py`

1. Buy success — balance debited, asset added, callback `state="done"`, one entry in `order_history`.
2. Buy with insufficient balance — balance unchanged, `state="failed"`, failure recorded in `order_history`.
3. Sell success — balance credited, asset decremented, asset entry removed when remaining holdings reach 0.
4. Sell with insufficient holdings — failure path.
5. Average cost — two buys of the same currency at different prices yield the volume-weighted average.
6. Trade attempted with no quote injected — `state="failed"`, `msg="시세 없음"`.
7. After `update_quote`, fill price equals the injected quote even when LLM passes a different `price` argument.
8. `cancel_request` and `cancel_all_requests` are no-ops; unknown ids pass silently.
9. `get_account_info` returns the documented shape (`balance`, `asset`, `quote` keys).

### 6.2 New: `tests/unit_tests/llm_operator_paper_test.py`

1. When the trader exposes `update_quote`, `_on_timer` calls it with the last `primary_candle` closing price.
2. When the trader does not expose `update_quote` (e.g. real `UpbitTrader`), no call is made — no exception.
3. When `market_data` contains no `primary_candle` entry, `update_quote` is not called.
4. `chat()` re-syncs from `last_market_data` if available; if `last_market_data` is None, no sync (no exception).

### 6.3 Migrated: `tests/e2e_tests/e2e_chat_trading_test.py`

- Imports `SimulationTrader` from `smtm.trader.simulation_trader`. The local `FakeTrader` import is dropped.
- Each `_make_operator` constructs `SimulationTrader(budget=budget)` and calls `update_quote("BTC", 50000)` to set the test's expected fill price.
- The `test_buy_then_sell_with_profit` test calls `update_quote("BTC", 60000)` between buy and sell to model price appreciation.
- Assertion arithmetic is unchanged because `commission_ratio` is 0 and the LLM's `price` argument matches the injected quote in every scripted scenario.
- Tests that read `self.trader.balance`, `self.trader.assets`, `self.trader.order_history` continue to work — `SimulationTrader` exposes the same attributes.

### 6.4 Modified: `tests/e2e_tests/fake_llm_client.py`

The `FakeTrader` class is removed. `FakeLlmClient` and `FakeDataProvider` remain — they replace external systems (LLM API, market data) that are out of scope for this work.

## 7. Documentation

### `README.md`

- Add `--paper` to the Options table.
- Add a `### Paper Trading` subsection under Usage with two examples (`--exchange UPB --paper`, `--exchange UFC --paper`) and three notes: quotes are pulled from the DataProvider's last candle so `start` must run at least once before manual trades; state is in-memory only; commission is 0 in simulation.
- Under "Supported Exchanges & Data Providers", a one-line note: any code in the table can be combined with `--paper`.

### `README-ko-kr.md`

Mirror of the English changes in Korean.

### Docstrings

- `SimulationTrader` class: 1–3 lines summarising real-quote-based paper trading, externally-injected quote, instant fill, no persistence.
- `LlmOperator._sync_trader_quote`: one line — pushes last candle close to the trader if it supports `update_quote`.

## 8. Definition of Done

- [ ] `python -m pytest tests/unit_tests/simulation_trader_test.py` passes (9 cases).
- [ ] `python -m pytest tests/unit_tests/llm_operator_paper_test.py` passes (4 cases).
- [ ] `python -m pytest tests/e2e_tests/` passes after migration.
- [ ] `python -m pytest tests/unit_tests/` passes — no regression elsewhere.
- [ ] `python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB --paper` prints the paper-mode warning, accepts `start`, runs at least one tick where the LLM's chosen action is recorded and `SimulationTrader` state changes accordingly.
- [ ] Both READMEs document the new mode.

## 9. Out of scope

- Persistence of balance / orders across CLI sessions.
- Partial fills.
- Commission model (parameter exists; applied as 0 throughout this PR).
- Per-exchange paper variants (e.g. `--paper` while `--exchange BTH`) — already supported transparently because `--paper` is orthogonal to `--exchange`; no extra code needed.
- Simulation-only DataProviders (e.g. historical-candle replay for backtesting). The `update_quote` mechanism is the right hook for this, but the providers themselves are a separate effort.
- `TelegramController` (`--mode 1`) wiring of `--paper`. Mechanism is identical, but Mode 0 is the focus of this PR.

## 10. Decisions log

| Decision | Choice | Why |
|---|---|---|
| Quote injection mechanism | C — Controller / LlmOperator pushes `update_quote` from DataProvider | Explicit, single-source-of-truth for price; extends naturally to backtest replay; no HTTP coupling inside trader |
| Exchange code vs flag | B — `--paper` orthogonal flag | Lets every DataProvider in the catalogue be used in paper mode; data and trade axes stay independent |
| Test FakeTrader vs new SimulationTrader | B — promote to production, retire FakeTrader | Single source of accounting logic; e2e tests now exercise real production trade path |
| Persistence | A — none | YAGNI for first PR; SystemMonitor already records the in-session activity |
| Insufficient funds / holdings | A — `state="failed"` callback | Matches real exchange traders; tests already assume this |
| Commission | Parameter present, applied as 0 | Keeps test arithmetic stable; commission model deferred |
