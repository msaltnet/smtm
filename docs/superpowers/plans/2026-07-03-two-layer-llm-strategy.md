# 2계층 LLM 아키텍처 + 계좌 프로파일 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** LLM을 "시스템 운영 에이전트(SystemOperator)"와 "전략 내부 판단(StrategyLlm)"으로 분리하고, 기존 `Strategy` 인터페이스 기반 고정주기 트레이딩 루프(TradingOperator)를 복원하며, 계좌 프로파일(JSON 프리셋) CRUD를 에이전트 Tool로 제공한다.

**Architecture:** 상위 `SystemOperator`(현 `LlmOperator` 리팩터)가 채팅+Tool use로 오케스트레이션만 담당하고, 하위 `TradingOperator`가 고정 주기로 `DataProvider → Strategy → SafetyGuard → Trader → Analyzer` 파이프라인을 돌린다. 매매 경로는 `Strategy → Trader` 단일 경로. 스펙: `docs/superpowers/specs/2026-07-03-two-layer-llm-strategy-design.md`

**Tech Stack:** Python, pytest(unittest 스타일), anthropic SDK, numpy/pandas(전략 포팅용 복원)

## Global Constraints

- 테스트 실행: `python -m pytest tests/unit_tests/ -v` (통합: `tests/integration_tests/`, E2E: `tests/e2e_tests/`)
- 커밋 메시지 형식: `[feat]`, `[test]`, `[refactor]`, `[docs]`, `[cleanup]` 접두사 (저장소 관례)
- **커밋에 `Co-Authored-By: Claude ...` 트레일러를 절대 붙이지 않는다** (사용자 전역 지침)
- 사용자 노출 문자열은 한국어 (기존 코드 관례)
- 매매 경로는 `Strategy.get_request() → Trader.send_request()` 단 하나. 에이전트에 `execute_trade` 류 Tool 금지
- master 브랜치의 코드를 포팅할 때는 `git show master:<path>` 를 사용해 원본을 그대로 가져온 후 지시된 최소 수정만 한다 (전사 오류 방지)
- 알고리즘 전략 구동 시 트레이딩 루프에서 LLM 호출 0회

## 파일 구조 (전체 조망)

**Create:**

| 파일 | 책임 |
|------|------|
| `smtm/strategy/__init__.py` | 전략 패키지 export |
| `smtm/strategy/strategy.py` | `Strategy` ABC (master 포팅) |
| `smtm/strategy/strategy_bnh.py` | `StrategyBuyAndHold` (master 포팅) |
| `smtm/strategy/strategy_rsi.py` | `StrategyRsi` (master 포팅) |
| `smtm/strategy/strategy_sma.py` | `StrategySma` (master `strategy_sma_0` 포팅+개명) |
| `smtm/strategy/strategy_llm.py` | `StrategyLlm` — 틱당 단일 구조화 판단 |
| `smtm/strategy/strategy_factory.py` | 코드→클래스 레지스트리 (BNH/RSI/SMA/LLM) |
| `smtm/analyzer.py` | 경량 `Analyzer` (SystemMonitor 위임) |
| `smtm/trading_operator.py` | `TradingOperator` — 고정주기 틱 루프 |
| `smtm/profile_store.py` | `ProfileStore` — 프로파일 JSON CRUD |
| `smtm/llm/system_operator.py` | `SystemOperator` — 오케스트레이션 에이전트 |
| `smtm/llm/tools/orchestration_tools.py` | 전략 지휘 Tool 6종 |
| `smtm/llm/tools/profile_tools.py` | 프로파일 CRUD Tool 6종 |

**Modify:** `smtm/llm/safety_guard.py`(check_request 추가), `smtm/llm/llm_client.py`·`claude_llm_client.py`(tool_choice), `smtm/llm/tool_router.py`(safety 제거), `smtm/llm/__init__.py`, `smtm/__init__.py`, `smtm/controller/controller.py`, `smtm/controller/jpt_controller.py`, `smtm/controller/telegram/telegram_controller.py`, `smtm/__main__.py`, `requirements.txt`, `tests/e2e_tests/fake_llm_client.py`

**Delete:** `smtm/llm/llm_operator.py`, `smtm/llm/tools/trade_tool.py`, `tests/unit_tests/llm_operator_test.py`, `tests/unit_tests/llm_operator_paper_test.py`, `tests/unit_tests/trade_tool_test.py`, `tests/integration_tests/llm_operator_ITG_test.py`

---

### Task 1: Strategy 패키지 복원 + StrategyBuyAndHold 포팅

**Files:**
- Create: `smtm/strategy/__init__.py`, `smtm/strategy/strategy.py`, `smtm/strategy/strategy_bnh.py`
- Modify: `smtm/__init__.py`
- Test: `tests/unit_tests/strategy_bnh_test.py`

**Interfaces:**
- Consumes: `smtm.log_manager.LogManager`, `smtm.date_converter.DateConverter` (기존)
- Produces: `Strategy` ABC — `initialize(budget, min_price=100, add_spot_callback=None, add_line_callback=None, alert_callback=None)`, `update_trading_info(info: list)`, `get_request() -> list|None`, `update_result(result: dict)`; `StrategyBuyAndHold` (CODE `"BNH"`)

- [ ] **Step 1: master에서 테스트 포팅 (실패하는 테스트)**

```bash
git show master:tests/unit_tests/strategy_bnh_test.py > tests/unit_tests/strategy_bnh_test.py
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/strategy_bnh_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'StrategyBuyAndHold' from 'smtm'`

- [ ] **Step 3: master에서 구현 포팅**

```bash
git show master:smtm/strategy/strategy.py > smtm/strategy/strategy.py
git show master:smtm/strategy/strategy_bnh.py > smtm/strategy/strategy_bnh.py
```

`smtm/strategy/__init__.py` 생성:

```python
from .strategy import Strategy
from .strategy_bnh import StrategyBuyAndHold
```

`smtm/__init__.py` 끝부분(마지막 import 뒤)에 추가:

```python
from .strategy.strategy import Strategy
from .strategy.strategy_bnh import StrategyBuyAndHold
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/strategy_bnh_test.py -q`
Expected: PASS (전체 green). 실패 시 master 테스트가 참조하는 미포팅 의존성을 확인하고 최소 수정.

- [ ] **Step 5: 전체 단위 테스트 회귀 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/ -q`
Expected: PASS

```bash
git add smtm/strategy/ smtm/__init__.py tests/unit_tests/strategy_bnh_test.py
git commit -m "[feat] restore Strategy interface and port StrategyBuyAndHold from master"
```

---

### Task 2: StrategyRsi 포팅

**Files:**
- Create: `smtm/strategy/strategy_rsi.py`
- Modify: `smtm/strategy/__init__.py`, `smtm/__init__.py`, `requirements.txt`
- Test: `tests/unit_tests/strategy_rsi_test.py`

**Interfaces:**
- Consumes: `Strategy` ABC (Task 1)
- Produces: `StrategyRsi` (CODE `"RSI"`, numpy 사용)

- [ ] **Step 1: numpy 의존성 추가 및 설치**

`requirements.txt`에 `numpy` 한 줄 추가 후:

```bash
pip install numpy
```

- [ ] **Step 2: master에서 테스트 포팅, 실패 확인**

```bash
git show master:tests/unit_tests/strategy_rsi_test.py > tests/unit_tests/strategy_rsi_test.py
python -m pytest tests/unit_tests/strategy_rsi_test.py -x -q
```

Expected: FAIL — `ImportError: cannot import name 'StrategyRsi'`

- [ ] **Step 3: master에서 구현 포팅 + export**

```bash
git show master:smtm/strategy/strategy_rsi.py > smtm/strategy/strategy_rsi.py
```

`smtm/strategy/__init__.py`에 `from .strategy_rsi import StrategyRsi` 추가.
`smtm/__init__.py`에 `from .strategy.strategy_rsi import StrategyRsi` 추가.

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/strategy_rsi_test.py -q`
Expected: PASS

- [ ] **Step 5: 커밋**

```bash
git add smtm/strategy/ smtm/__init__.py requirements.txt tests/unit_tests/strategy_rsi_test.py
git commit -m "[feat] port StrategyRsi from master"
```

---

### Task 3: StrategySma 포팅 (strategy_sma_0 → strategy_sma 개명)

**Files:**
- Create: `smtm/strategy/strategy_sma.py`
- Modify: `smtm/strategy/__init__.py`, `smtm/__init__.py`, `requirements.txt`
- Test: `tests/unit_tests/strategy_sma_test.py`

**Interfaces:**
- Consumes: `Strategy` ABC (Task 1)
- Produces: `StrategySma` (CODE `"SMA"`, NAME `"SMA"`, pandas/numpy 사용)

- [ ] **Step 1: pandas 의존성 추가 및 설치**

`requirements.txt`에 `pandas` 추가 후 `pip install pandas`

- [ ] **Step 2: master에서 테스트 포팅 + 클래스명 개명, 실패 확인**

```bash
git show master:tests/unit_tests/strategy_sma_0_test.py > tests/unit_tests/strategy_sma_test.py
sed -i 's/StrategySma0/StrategySma/g' tests/unit_tests/strategy_sma_test.py
python -m pytest tests/unit_tests/strategy_sma_test.py -x -q
```

Expected: FAIL — `ImportError: cannot import name 'StrategySma'`

- [ ] **Step 3: master에서 구현 포팅 + 개명 + export**

```bash
git show master:smtm/strategy/strategy_sma_0.py > smtm/strategy/strategy_sma.py
sed -i 's/StrategySma0/StrategySma/g; s/NAME = "SMA0-I"/NAME = "SMA"/' smtm/strategy/strategy_sma.py
```

주의: sed 후 파일을 열어 `CODE = "SMA"`가 유지되는지, 클래스 docstring이 깨지지 않았는지 확인.

`smtm/strategy/__init__.py`에 `from .strategy_sma import StrategySma` 추가.
`smtm/__init__.py`에 `from .strategy.strategy_sma import StrategySma` 추가.

- [ ] **Step 4: 테스트 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/strategy_sma_test.py tests/unit_tests/ -q`
Expected: PASS

```bash
git add smtm/strategy/ smtm/__init__.py requirements.txt tests/unit_tests/strategy_sma_test.py
git commit -m "[feat] port StrategySma (formerly StrategySma0) from master"
```

---

### Task 4: StrategyFactory

**Files:**
- Create: `smtm/strategy/strategy_factory.py`
- Modify: `smtm/strategy/__init__.py`, `smtm/__init__.py`
- Test: `tests/unit_tests/strategy_factory_test.py`

**Interfaces:**
- Consumes: `StrategyBuyAndHold`, `StrategyRsi`, `StrategySma`
- Produces: `StrategyFactory.create(code, llm_client=None) -> Strategy|None`, `StrategyFactory.get_name(code) -> str|None`, `StrategyFactory.get_all_strategy_info() -> list[dict]` (각 dict: `name`/`code`/`class`). `llm_client` 인자는 Task 9에서 사용되며 지금은 무시된다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/strategy_factory_test.py`:

```python
import unittest
from smtm import StrategyFactory, StrategyBuyAndHold, StrategyRsi, StrategySma


class StrategyFactoryTests(unittest.TestCase):
    def test_create_returns_correct_strategy_for_each_code(self):
        self.assertIsInstance(StrategyFactory.create("BNH"), StrategyBuyAndHold)
        self.assertIsInstance(StrategyFactory.create("RSI"), StrategyRsi)
        self.assertIsInstance(StrategyFactory.create("SMA"), StrategySma)

    def test_create_returns_none_for_unknown_code(self):
        self.assertIsNone(StrategyFactory.create("NOPE"))

    def test_get_name_returns_name_or_none(self):
        self.assertEqual(StrategyFactory.get_name("BNH"), "Buy and Hold")
        self.assertIsNone(StrategyFactory.get_name("NOPE"))

    def test_get_all_strategy_info_contains_all_codes(self):
        codes = [info["code"] for info in StrategyFactory.get_all_strategy_info()]
        self.assertIn("BNH", codes)
        self.assertIn("RSI", codes)
        self.assertIn("SMA", codes)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/strategy_factory_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'StrategyFactory'`

- [ ] **Step 3: 구현**

`smtm/strategy/strategy_factory.py`:

```python
from .strategy_bnh import StrategyBuyAndHold
from .strategy_rsi import StrategyRsi
from .strategy_sma import StrategySma


class StrategyFactory:
    """Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

    STRATEGY_LIST = [
        StrategyBuyAndHold,
        StrategyRsi,
        StrategySma,
    ]

    @staticmethod
    def create(code, llm_client=None):
        """code에 해당하는 Strategy 객체를 생성하여 반환. llm_client는 LLM 전략에서만 사용"""
        del llm_client  # LLM 전략 등록 시(Task 9) 사용
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy()
        return None

    @staticmethod
    def get_name(code):
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy.NAME
        return None

    @staticmethod
    def get_all_strategy_info():
        return [
            {"name": s.NAME, "code": s.CODE, "class": s}
            for s in StrategyFactory.STRATEGY_LIST
        ]
```

`smtm/strategy/__init__.py`에 `from .strategy_factory import StrategyFactory` 추가.
`smtm/__init__.py`에 `from .strategy.strategy_factory import StrategyFactory` 추가.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/strategy_factory_test.py -q` → PASS

```bash
git add smtm/strategy/ smtm/__init__.py tests/unit_tests/strategy_factory_test.py
git commit -m "[feat] add StrategyFactory with BNH/RSI/SMA registry"
```

---

### Task 5: SafetyGuard.check_request — 거래 요청 기반 검증

**Files:**
- Modify: `smtm/llm/safety_guard.py`
- Test: `tests/unit_tests/safety_guard_test.py` (기존 파일에 테스트 추가)

**Interfaces:**
- Consumes: 기존 `SafetyConfig`, `SafetyResult`
- Produces: `SafetyGuard.check_request(request: dict) -> SafetyResult` — request는 `{id, type, price, amount, date_time}`. `type == "cancel"`이면 무조건 허용. 기존 `check(tool_call)`은 **이번 태스크에서는 유지**(ToolRouter가 아직 사용, Task 11에서 제거).

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/unit_tests/safety_guard_test.py` 끝에 추가:

```python
class SafetyGuardCheckRequestTests(unittest.TestCase):
    def setUp(self):
        from smtm.llm.safety_guard import SafetyGuard, SafetyConfig
        self.guard = SafetyGuard(SafetyConfig(
            max_trade_amount=100000, max_daily_trades=2,
            max_loss_ratio=-0.2, initial_budget=500000,
        ))

    def _request(self, type="buy", price=50000, amount=1.0):
        return {"id": "test-id", "type": type, "price": price,
                "amount": amount, "date_time": "2026-07-03T12:00:00"}

    def test_allows_request_within_limits(self):
        result = self.guard.check_request(self._request())
        self.assertTrue(result.allowed)

    def test_blocks_request_exceeding_max_trade_amount(self):
        result = self.guard.check_request(self._request(price=200000, amount=1.0))
        self.assertFalse(result.allowed)
        self.assertIn("최대 거래금액", result.reason)

    def test_cancel_request_bypasses_amount_check(self):
        result = self.guard.check_request(self._request(type="cancel", price=0, amount=0))
        self.assertTrue(result.allowed)

    def test_blocks_after_daily_trade_limit(self):
        self.guard.record_trade({})
        self.guard.record_trade({})
        result = self.guard.check_request(self._request())
        self.assertFalse(result.allowed)
        self.assertIn("일일 거래횟수", result.reason)

    def test_blocks_when_loss_limit_exceeded(self):
        self.guard.update_portfolio_value(350000)  # -30% < -20%
        result = self.guard.check_request(self._request())
        self.assertFalse(result.allowed)
        self.assertIn("손실 한도", result.reason)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/safety_guard_test.py -x -q`
Expected: FAIL — `AttributeError: 'SafetyGuard' object has no attribute 'check_request'`

- [ ] **Step 3: 구현 — 공통 로직 추출 + check_request 추가**

`smtm/llm/safety_guard.py`의 `check` 메서드 아래에 추가하고, `check`는 공통 메서드를 재사용하도록 수정:

```python
    def check(self, tool_call) -> SafetyResult:
        """Tool 호출 사전 검증. 거래 Tool만 검증, 나머지는 통과. (Task 11에서 제거 예정)"""
        if tool_call.name not in self.TRADE_TOOLS:
            return SafetyResult(allowed=True)
        trade_amount = tool_call.arguments.get("price", 0) * tool_call.arguments.get("amount", 0)
        return self._check_limits(trade_amount)

    def check_request(self, request: dict) -> SafetyResult:
        """거래 요청(request dict) 사전 검증. cancel 요청은 검사 제외."""
        if request.get("type") == "cancel":
            return SafetyResult(allowed=True)
        trade_amount = float(request.get("price", 0)) * float(request.get("amount", 0))
        return self._check_limits(trade_amount)

    def _check_limits(self, trade_amount: float) -> SafetyResult:
        self._reset_daily_if_needed()

        if trade_amount > self.config.max_trade_amount:
            reason = f"1회 최대 거래금액 초과 ({trade_amount:,.0f} > {self.config.max_trade_amount:,.0f})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        if self.daily_trade_count >= self.config.max_daily_trades:
            reason = f"일일 거래횟수 초과 ({self.daily_trade_count}/{self.config.max_daily_trades})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        loss_ratio = (self.current_value - self.config.initial_budget) / self.config.initial_budget
        if loss_ratio < self.config.max_loss_ratio:
            reason = f"손실 한도 초과 ({loss_ratio:.1%} < {self.config.max_loss_ratio:.1%})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        return SafetyResult(allowed=True)
```

기존 `check` 내부의 중복 검증 코드(금액/횟수/손실 3블록)는 삭제하고 위처럼 `_check_limits` 호출로 대체한다.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/safety_guard_test.py tests/unit_tests/ -q` → PASS

```bash
git add smtm/llm/safety_guard.py tests/unit_tests/safety_guard_test.py
git commit -m "[feat] add SafetyGuard.check_request for request-based validation"
```

---

### Task 6: 경량 Analyzer

**Files:**
- Create: `smtm/analyzer.py`
- Modify: `smtm/__init__.py`
- Test: `tests/unit_tests/analyzer_test.py`

**Interfaces:**
- Consumes: `SystemMonitor` (기존 — `log_market_data`, `log_trade_request`, `log_trade_result`, `log_safety_event`)
- Produces: `Analyzer(system_monitor)` — `initialize(get_account_info_func)`, `make_start_point()`, `put_trading_info(info)`, `put_requests(requests: list)`, `put_result(result)`, `put_safety_event(event: dict)`, `add_drawing_spot(date_time, value)`, `add_value_for_line_graph(date_time, value)`, `current_account_value() -> float`, `get_return_report() -> dict` (키: `start_value`/`current_value`/`cumulative_return`)

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/analyzer_test.py`:

```python
import unittest
from unittest.mock import MagicMock
from smtm import Analyzer


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.monitor = MagicMock()
        self.analyzer = Analyzer(self.monitor)
        self.account = {
            "balance": 400000,
            "asset": {"BTC": (50000, 2.0)},   # (평균단가, 수량)
            "quote": {"BTC": 60000},
        }
        self.analyzer.initialize(lambda: self.account)

    def test_put_methods_delegate_to_system_monitor(self):
        self.analyzer.put_trading_info([{"type": "primary_candle"}])
        self.monitor.log_market_data.assert_called_once()

        self.analyzer.put_requests([{"id": "1"}, {"id": "2"}])
        self.assertEqual(self.monitor.log_trade_request.call_count, 2)

        self.analyzer.put_result({"state": "done"})
        self.monitor.log_trade_result.assert_called_once()

        self.analyzer.put_safety_event({"reason": "blocked"})
        self.monitor.log_safety_event.assert_called_once()

    def test_current_account_value_includes_assets_at_quote(self):
        # 400000 + 2.0 * 60000 = 520000
        self.assertEqual(self.analyzer.current_account_value(), 520000)

    def test_get_return_report_computes_cumulative_return(self):
        self.analyzer.make_start_point()          # 시작 가치 520000
        self.account["balance"] = 452000          # 현재 가치 572000 → +10%
        report = self.analyzer.get_return_report()
        self.assertEqual(report["start_value"], 520000)
        self.assertEqual(report["current_value"], 572000)
        self.assertEqual(report["cumulative_return"], 10.0)

    def test_get_return_report_without_start_point_returns_zero(self):
        report = self.analyzer.get_return_report()
        self.assertEqual(report["cumulative_return"], 0)

    def test_drawing_callbacks_accumulate(self):
        self.analyzer.add_drawing_spot("2026-07-03T12:00:00", 100)
        self.analyzer.add_value_for_line_graph("2026-07-03T12:00:00", 200)
        self.assertEqual(len(self.analyzer.spots), 1)
        self.assertEqual(len(self.analyzer.lines), 1)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/analyzer_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'Analyzer'`

- [ ] **Step 3: 구현**

`smtm/analyzer.py`:

```python
from .log_manager import LogManager


class Analyzer:
    """SystemMonitor 위에서 Strategy 콜백 계약과 최소 성과 집계를 제공하는 경량 분석 계층"""

    def __init__(self, system_monitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.system_monitor = system_monitor
        self.get_account_info_func = None
        self.start_value = None
        self.spots = []
        self.lines = []

    def initialize(self, get_account_info_func):
        self.get_account_info_func = get_account_info_func

    def make_start_point(self):
        self.start_value = self.current_account_value()

    def put_trading_info(self, info):
        self.system_monitor.log_market_data(info)

    def put_requests(self, requests):
        for request in requests:
            self.system_monitor.log_trade_request(request)

    def put_result(self, result):
        self.system_monitor.log_trade_result(result)

    def put_safety_event(self, event):
        self.system_monitor.log_safety_event(event)

    def add_drawing_spot(self, date_time, value):
        self.spots.append({"date_time": date_time, "value": value})

    def add_value_for_line_graph(self, date_time, value):
        self.lines.append({"date_time": date_time, "value": value})

    def current_account_value(self) -> float:
        if self.get_account_info_func is None:
            return 0.0
        account = self.get_account_info_func()
        value = float(account.get("balance", 0))
        quotes = account.get("quote", {}) or {}
        for currency, (avg_price, amount) in (account.get("asset", {}) or {}).items():
            price = quotes.get(currency, avg_price)
            value += float(price) * float(amount)
        return value

    def get_return_report(self) -> dict:
        current_value = self.current_account_value()
        start_value = self.start_value
        if not start_value:
            return {"start_value": current_value, "current_value": current_value,
                    "cumulative_return": 0}
        cumulative_return = round((current_value - start_value) / start_value * 100, 3)
        return {"start_value": start_value, "current_value": current_value,
                "cumulative_return": cumulative_return}
```

`smtm/__init__.py`에 `from .analyzer import Analyzer` 추가.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/analyzer_test.py -q` → PASS

```bash
git add smtm/analyzer.py smtm/__init__.py tests/unit_tests/analyzer_test.py
git commit -m "[feat] add lightweight Analyzer over SystemMonitor"
```

---

### Task 7: TradingOperator — 고정주기 틱 루프

**Files:**
- Create: `smtm/trading_operator.py`
- Modify: `smtm/__init__.py`
- Test: `tests/unit_tests/trading_operator_test.py`

**Interfaces:**
- Consumes: `Strategy`(Task 1), `Analyzer`(Task 6), `SafetyGuard.check_request`(Task 5), `Trader`/`SimulationTrader`(기존), `Worker`(기존), DataProvider `get_info()`(기존)
- Produces: `TradingOperator(interval=60, currency="BTC")` — `initialize(data_provider, strategy, trader, analyzer, safety_guard, budget=500000)`, `start() -> bool`, `stop()`, `get_score() -> dict`, `state` 속성(`None`→`"ready"`→`"running"`→`"ready"`). 내부 `_execute_trading(task)`는 테스트에서 직접 호출 가능.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/trading_operator_test.py`:

```python
import unittest
from unittest.mock import MagicMock
from smtm import TradingOperator, Analyzer, StrategyBuyAndHold
from smtm.trader.simulation_trader import SimulationTrader
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig
from smtm.llm.system_monitor import SystemMonitor


class FakeDataProvider:
    def __init__(self, closing_price=50000):
        self.closing_price = closing_price

    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-03T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": self.closing_price,
            "acc_price": 1000000000, "acc_volume": 200,
        }]


def make_operator(budget=500000, max_trade_amount=1000000, closing_price=50000):
    monitor = SystemMonitor()
    analyzer = Analyzer(monitor)
    trader = SimulationTrader(budget=budget, currency="BTC")
    strategy = StrategyBuyAndHold()
    guard = SafetyGuard(SafetyConfig(
        max_trade_amount=max_trade_amount, max_daily_trades=20,
        max_loss_ratio=-0.9, initial_budget=budget,
    ))
    operator = TradingOperator(interval=60, currency="BTC")
    operator.initialize(
        FakeDataProvider(closing_price), strategy, trader, analyzer, guard,
        budget=budget,
    )
    return operator, trader, strategy, monitor


class TradingOperatorInitTests(unittest.TestCase):
    def test_initialize_sets_state_ready_and_initializes_components(self):
        operator, _, strategy, _ = make_operator()
        self.assertEqual(operator.state, "ready")
        self.assertTrue(strategy.is_initialized)

    def test_initialize_twice_is_noop(self):
        operator, _, _, _ = make_operator()
        operator.initialize(None, None, None, None, None)  # 무시되어야 함
        self.assertEqual(operator.state, "ready")
        self.assertIsNotNone(operator.strategy)


class TradingOperatorTickTests(unittest.TestCase):
    def test_tick_executes_full_pipeline_and_buys(self):
        operator, trader, _, monitor = make_operator()
        operator.state = "running"
        operator._execute_trading(None)
        # BnH는 예산의 1/5 매수 → SimulationTrader 잔고 감소
        self.assertLess(trader.balance, 500000)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["state"], "done")
        # 기록 확인
        self.assertEqual(len(monitor.market_data_log), 1)
        self.assertEqual(len(monitor.trade_request_log), 1)
        self.assertEqual(len(monitor.trade_result_log), 1)

    def test_tick_injects_quote_into_simulation_trader(self):
        operator, trader, _, _ = make_operator(closing_price=42000)
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(trader.quotes["BTC"], 42000)
        # 체결가는 주입된 시세를 따른다
        self.assertEqual(trader.order_history[0]["price"], 42000)

    def test_tick_is_noop_for_trader_without_update_quote(self):
        operator, _, _, _ = make_operator()
        real_trader = MagicMock(spec=["send_request", "cancel_request",
                                      "cancel_all_requests", "get_account_info"])
        operator.trader = real_trader
        operator.state = "running"
        operator._execute_trading(None)  # AttributeError 없이 통과해야 함

    def test_safety_guard_blocks_oversized_request(self):
        # max_trade_amount=1000 → BnH의 10만원 매수 차단
        operator, trader, _, monitor = make_operator(max_trade_amount=1000)
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(len(trader.order_history), 0)
        self.assertEqual(trader.balance, 500000)
        self.assertEqual(len(monitor.safety_event_log), 1)

    def test_empty_data_does_not_crash(self):
        operator, trader, _, _ = make_operator()
        operator.data_provider = MagicMock(get_info=MagicMock(return_value=[]))
        operator.state = "running"
        operator._execute_trading(None)
        self.assertEqual(len(trader.order_history), 0)


class TradingOperatorLifecycleTests(unittest.TestCase):
    def test_start_stop_start_cycle(self):
        operator, _, _, _ = make_operator()
        self.assertTrue(operator.start())
        self.assertEqual(operator.state, "running")
        operator.stop()
        self.assertEqual(operator.state, "ready")
        self.assertTrue(operator.start())
        operator.stop()

    def test_start_when_not_ready_returns_false(self):
        operator, _, _, _ = make_operator()
        operator.start()
        self.assertFalse(operator.start())
        operator.stop()
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/trading_operator_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'TradingOperator'`

- [ ] **Step 3: 구현**

`smtm/trading_operator.py`:

```python
import threading
from .log_manager import LogManager
from .worker import Worker


class TradingOperator:
    """고정 주기로 DataProvider → Strategy → SafetyGuard → Trader → Analyzer
    파이프라인을 수행하는 트레이딩 오퍼레이터"""

    def __init__(self, interval=60, currency="BTC"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.interval = float(interval)
        self.currency = currency
        self.data_provider = None
        self.strategy = None
        self.trader = None
        self.analyzer = None
        self.safety_guard = None
        self.state = None
        self.timer = None
        self.is_timer_running = False
        self.worker = Worker("TradingOperator-Worker")

    def initialize(self, data_provider, strategy, trader, analyzer, safety_guard,
                   budget=500000):
        if self.state is not None:
            return
        self.data_provider = data_provider
        self.strategy = strategy
        self.trader = trader
        self.analyzer = analyzer
        self.safety_guard = safety_guard
        strategy.initialize(
            budget,
            add_spot_callback=analyzer.add_drawing_spot,
            add_line_callback=analyzer.add_value_for_line_graph,
            alert_callback=lambda msg: self.logger.warning(f"strategy alert: {msg}"),
        )
        analyzer.initialize(trader.get_account_info)
        self.state = "ready"

    def start(self) -> bool:
        if self.state != "ready" or self.is_timer_running:
            return False
        self.logger.info("===== TradingOperator Start =====")
        self.state = "running"
        self.analyzer.make_start_point()
        self.worker.start()
        self.worker.post_task({"runnable": self._execute_trading})
        return True

    def stop(self):
        if self.state != "running":
            return
        if self.timer is not None:
            self.timer.cancel()
        self.is_timer_running = False
        self.trader.cancel_all_requests()
        self.logger.info("===== TradingOperator Stop =====")
        self.state = "ready"
        self.worker.stop()

    def get_score(self) -> dict:
        return self.analyzer.get_return_report()

    def _execute_trading(self, task):
        del task
        self.is_timer_running = False
        try:
            info = self.data_provider.get_info()
            self._sync_trader_quote(info)
            self.strategy.update_trading_info(info)
            self.analyzer.put_trading_info(info)

            requests = self.strategy.get_request()
            if requests:
                self._send_requests(requests)

            self.safety_guard.update_portfolio_value(
                self.analyzer.current_account_value()
            )
        except Exception as err:
            self.logger.error(f"trading tick error: {err}")
        self._start_timer()

    def _send_requests(self, requests):
        allowed = []
        for request in requests:
            verdict = self.safety_guard.check_request(request)
            if verdict.allowed:
                allowed.append(request)
            else:
                self.analyzer.put_safety_event({
                    "type": "blocked", "request": request, "reason": verdict.reason,
                })
        if not allowed:
            return

        def callback(result):
            self.strategy.update_result(result)
            if result.get("state") != "requested":
                self.analyzer.put_result(result)
                if result.get("type") in ("buy", "sell"):
                    self.safety_guard.record_trade(result)

        self.trader.send_request(allowed, callback)
        self.analyzer.put_requests(allowed)

    def _sync_trader_quote(self, market_data):
        """가상매매 트레이더에 최신 종가 주입 (덕 타이핑 — 실거래 트레이더는 no-op)"""
        if not hasattr(self.trader, "update_quote") or not market_data:
            return
        for item in market_data:
            if isinstance(item, dict) and item.get("type") == "primary_candle":
                currency = item.get("market", self.currency)
                price = item.get("closing_price")
                if currency and price is not None:
                    self.trader.update_quote(currency, price)
                return

    def _start_timer(self):
        if self.is_timer_running or self.state != "running":
            return

        def on_timer_expired():
            self.worker.post_task({"runnable": self._execute_trading})

        self.timer = threading.Timer(self.interval, on_timer_expired)
        self.timer.start()
        self.is_timer_running = True
```

`smtm/__init__.py`에 `from .trading_operator import TradingOperator` 추가.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/trading_operator_test.py tests/unit_tests/ -q` → PASS

```bash
git add smtm/trading_operator.py smtm/__init__.py tests/unit_tests/trading_operator_test.py
git commit -m "[feat] add TradingOperator fixed-interval trading loop with SafetyGuard and quote injection"
```

---

### Task 8: LlmClient에 tool_choice(강제 Tool 호출) 지원

**Files:**
- Modify: `smtm/llm/llm_client.py`, `smtm/llm/claude_llm_client.py`, `tests/e2e_tests/fake_llm_client.py`
- Test: `tests/unit_tests/claude_llm_client_test.py` (테스트 추가)

**Interfaces:**
- Produces: `LlmClient.create_message(system_prompt, messages, tools, tool_choice=None)` — `tool_choice` 예: `{"type": "tool", "name": "submit_decision"}`. 기본값 `None`이면 기존 동작과 동일(하위 호환).

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/unit_tests/claude_llm_client_test.py` 끝에 추가 (기존 테스트의 mock 패턴을 따른다 — 파일 상단의 기존 import/mock 구성을 확인 후 동일하게):

```python
class ClaudeLlmClientToolChoiceTests(unittest.TestCase):
    @patch("smtm.llm.claude_llm_client.anthropic")
    def test_tool_choice_is_passed_to_api(self, mock_anthropic):
        from smtm.llm.claude_llm_client import ClaudeLlmClient
        mock_response = MagicMock()
        mock_response.content = []
        mock_response.stop_reason = "tool_use"
        mock_response.usage.input_tokens = 1
        mock_response.usage.output_tokens = 1
        mock_client = mock_anthropic.Anthropic.return_value
        mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key")
        client.create_message(
            "system", [{"role": "user", "content": "hi"}],
            [{"name": "submit_decision"}],
            tool_choice={"type": "tool", "name": "submit_decision"},
        )
        kwargs = mock_client.messages.create.call_args.kwargs
        self.assertEqual(kwargs["tool_choice"], {"type": "tool", "name": "submit_decision"})

    @patch("smtm.llm.claude_llm_client.anthropic")
    def test_tool_choice_none_is_not_passed(self, mock_anthropic):
        from smtm.llm.claude_llm_client import ClaudeLlmClient
        mock_response = MagicMock()
        mock_response.content = []
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 1
        mock_response.usage.output_tokens = 1
        mock_client = mock_anthropic.Anthropic.return_value
        mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key")
        client.create_message("system", [{"role": "user", "content": "hi"}], [])
        kwargs = mock_client.messages.create.call_args.kwargs
        self.assertNotIn("tool_choice", kwargs)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/claude_llm_client_test.py -x -q`
Expected: FAIL — `TypeError: create_message() got an unexpected keyword argument 'tool_choice'`

- [ ] **Step 3: 구현**

`smtm/llm/llm_client.py`의 추상 메서드 시그니처 변경:

```python
    @abstractmethod
    def create_message(
        self,
        system_prompt: str,
        messages: list,
        tools: list,
        tool_choice: dict = None,
    ) -> LlmResponse:
        """LLM에 메시지를 전송하고 응답을 받는다. tool_choice로 특정 Tool 호출을 강제할 수 있다"""
```

`smtm/llm/claude_llm_client.py`:

```python
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        response = self.client.messages.create(**kwargs)
        # (이하 기존과 동일)
```

`tests/e2e_tests/fake_llm_client.py`의 `FakeLlmClient.create_message` 시그니처도 변경:

```python
    def create_message(self, system_prompt, messages, tools, tool_choice=None) -> LlmResponse:
        self.call_log.append({
            "system_prompt": system_prompt,
            "messages": messages,
            "tools": tools,
            "tool_choice": tool_choice,
        })
        # (이하 기존과 동일)
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/claude_llm_client_test.py tests/unit_tests/llm_client_test.py tests/e2e_tests/ -q` → PASS

```bash
git add smtm/llm/llm_client.py smtm/llm/claude_llm_client.py tests/e2e_tests/fake_llm_client.py tests/unit_tests/claude_llm_client_test.py
git commit -m "[feat] support forced tool use via tool_choice in LlmClient"
```

---

### Task 9: StrategyLlm — 틱당 단일 구조화 판단

**Files:**
- Create: `smtm/strategy/strategy_llm.py`
- Modify: `smtm/strategy/strategy_factory.py`, `smtm/strategy/__init__.py`, `smtm/__init__.py`
- Test: `tests/unit_tests/strategy_llm_test.py`

**Interfaces:**
- Consumes: `Strategy` ABC, `LlmClient.create_message(..., tool_choice=)`(Task 8), `DateConverter.timestamp_id()`(기존). llm_client는 **덕 타이핑**으로 주입 — `smtm.llm`을 import하지 않는다(순환 import 방지).
- Produces: `StrategyLlm(llm_client=None, strategy_files=None)` (CODE `"LLM"`). `StrategyFactory.create("LLM", llm_client=client)`가 llm_client를 주입.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/strategy_llm_test.py`:

```python
import unittest
from smtm import StrategyLlm, StrategyFactory
from smtm.llm.llm_client import LlmResponse, ToolCall


class ScriptedLlmClient:
    """지정된 판단을 반환하는 테스트용 클라이언트"""

    def __init__(self, decision=None, raise_error=False):
        self.decision = decision
        self.raise_error = raise_error
        self.call_log = []

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        self.call_log.append({"system_prompt": system_prompt, "messages": messages,
                              "tools": tools, "tool_choice": tool_choice})
        if self.raise_error:
            raise RuntimeError("api error")
        if self.decision is None:
            return LlmResponse(text="no tool call", tool_calls=[])
        return LlmResponse(text="", tool_calls=[
            ToolCall(id="t1", name="submit_decision", arguments=self.decision)
        ])


CANDLE = {
    "type": "primary_candle", "market": "BTC", "date_time": "2026-07-03T12:00:00",
    "opening_price": 50000, "high_price": 51000, "low_price": 49000,
    "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
}


def make_strategy(decision=None, raise_error=False, budget=500000):
    client = ScriptedLlmClient(decision=decision, raise_error=raise_error)
    strategy = StrategyLlm(llm_client=client)
    strategy.initialize(budget)
    strategy.update_trading_info([CANDLE])
    return strategy, client


class StrategyLlmTests(unittest.TestCase):
    def test_buy_decision_produces_buy_request(self):
        strategy, client = make_strategy(
            {"action": "buy", "price": 50000, "amount": 0.5,
             "confidence": 0.8, "reason": "상승 추세"})
        requests = strategy.get_request()
        self.assertEqual(requests[-1]["type"], "buy")
        self.assertEqual(requests[-1]["price"], 50000)
        self.assertEqual(requests[-1]["amount"], 0.5)
        # 강제 tool use 확인
        self.assertEqual(client.call_log[0]["tool_choice"],
                         {"type": "tool", "name": "submit_decision"})

    def test_hold_decision_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "hold", "confidence": 0.5, "reason": "관망"})
        self.assertIsNone(strategy.get_request())

    def test_sell_without_position_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "sell", "price": 50000, "amount": 1.0,
             "confidence": 0.9, "reason": "하락"})
        self.assertIsNone(strategy.get_request())  # 보유 수량 0

    def test_buy_exceeding_balance_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "buy", "price": 50000, "amount": 100.0,
             "confidence": 0.9, "reason": "무리한 매수"})
        self.assertIsNone(strategy.get_request())  # 500만 > 잔고 50만

    def test_llm_error_falls_back_to_hold(self):
        strategy, _ = make_strategy(raise_error=True)
        self.assertIsNone(strategy.get_request())

    def test_no_tool_call_falls_back_to_hold(self):
        strategy, _ = make_strategy(decision=None)
        self.assertIsNone(strategy.get_request())

    def test_invalid_action_falls_back_to_hold(self):
        strategy, _ = make_strategy(
            {"action": "yolo", "reason": "?"})
        self.assertIsNone(strategy.get_request())

    def test_update_result_tracks_balance_and_asset(self):
        strategy, _ = make_strategy(
            {"action": "buy", "price": 50000, "amount": 0.5,
             "confidence": 0.8, "reason": "매수"})
        strategy.update_result({
            "request": {"id": "1"}, "type": "buy", "price": 50000, "amount": 0.5,
            "msg": "success", "state": "done", "balance": 475000,
            "date_time": "2026-07-03T12:00:01",
        })
        self.assertLess(strategy.balance, 500000)
        self.assertEqual(strategy.asset_amount, 0.5)

    def test_not_initialized_returns_none(self):
        strategy = StrategyLlm(llm_client=ScriptedLlmClient())
        self.assertIsNone(strategy.get_request())

    def test_factory_creates_llm_strategy_with_client(self):
        client = ScriptedLlmClient()
        strategy = StrategyFactory.create("LLM", llm_client=client)
        self.assertIsInstance(strategy, StrategyLlm)
        self.assertIs(strategy.llm_client, client)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/strategy_llm_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'StrategyLlm'`

- [ ] **Step 3: 구현**

`smtm/strategy/strategy_llm.py`:

```python
import copy
import os
from datetime import datetime
from .strategy import Strategy
from ..log_manager import LogManager
from ..date_converter import DateConverter


class StrategyLlm(Strategy):
    """LLM에게 매 틱 단일 구조화 판단을 요청하는 전략.

    Tool 루프 없이 forced tool use로 submit_decision 스키마를 1회 강제한다.
    판단 실패/검증 실패 시 해당 틱은 안전하게 hold(None) 처리.
    llm_client는 덕 타이핑으로 주입된다 (create_message 프로토콜).
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    COMMISSION_RATIO = 0.0005
    NAME = "LLM Single Decision"
    CODE = "LLM"
    CANDLE_WINDOW = 20
    RESULT_WINDOW = 10

    DECISION_TOOL = {
        "name": "submit_decision",
        "description": "시장 분석 결과에 따른 매매 판단을 제출합니다",
        "input_schema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["buy", "sell", "hold"],
                           "description": "매매 판단"},
                "price": {"type": ["number", "null"], "description": "주문 가격 (hold면 null)"},
                "amount": {"type": ["number", "null"], "description": "주문 수량 (hold면 null)"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1,
                               "description": "판단 확신도"},
                "reason": {"type": "string", "description": "판단 근거"},
            },
            "required": ["action", "reason"],
        },
    }

    def __init__(self, llm_client=None, strategy_files=None):
        self.llm_client = llm_client
        self.is_initialized = False
        self.is_simulation = False
        self.data = []
        self.budget = 0
        self.balance = 0.0
        self.asset_amount = 0.0
        self.min_price = 0
        self.result = []
        self.waiting_requests = {}
        self.logger = LogManager.get_logger(__class__.__name__)
        self.strategy_knowledge = self._load_strategy_knowledge(strategy_files or [])

    def initialize(self, budget, min_price=5000, add_spot_callback=None,
                   add_line_callback=None, alert_callback=None):
        if self.is_initialized:
            return
        self.is_initialized = True
        self.budget = budget
        self.balance = budget
        self.min_price = min_price

    def update_trading_info(self, info):
        if self.is_initialized is not True or info is None:
            return
        for item in info:
            if item.get("type") == "primary_candle":
                self.data.append(copy.deepcopy(item))
                break
        if len(self.data) > self.CANDLE_WINDOW:
            self.data = self.data[-self.CANDLE_WINDOW:]

    def update_result(self, result):
        if self.is_initialized is not True:
            return
        try:
            request = result["request"]
            if result["state"] == "requested":
                self.waiting_requests[request["id"]] = result
                return
            if result["state"] == "done" and request["id"] in self.waiting_requests:
                del self.waiting_requests[request["id"]]

            price = float(result["price"])
            amount = float(result["amount"])
            total = price * amount
            fee = total * self.COMMISSION_RATIO
            if result["type"] == "buy":
                self.balance -= round(total + fee)
            else:
                self.balance += round(total - fee)

            if result["msg"] == "success":
                if result["type"] == "buy":
                    self.asset_amount = round(self.asset_amount + amount, 6)
                elif result["type"] == "sell":
                    self.asset_amount = round(self.asset_amount - amount, 6)

            self.result.append(copy.deepcopy(result))
            if len(self.result) > self.RESULT_WINDOW:
                self.result = self.result[-self.RESULT_WINDOW:]
        except (AttributeError, TypeError, KeyError) as msg:
            self.logger.error(msg)

    def get_request(self):
        if self.is_initialized is not True or not self.data or self.llm_client is None:
            return None

        decision = self._request_decision()
        if decision is None or decision.get("action") == "hold":
            return None

        request = self._decision_to_request(decision)
        if request is None:
            return None

        now = datetime.now().strftime(self.ISO_DATEFORMAT)
        if self.is_simulation:
            now = self.data[-1]["date_time"]
        request["date_time"] = now

        final_requests = []
        for request_id in self.waiting_requests:
            final_requests.append({
                "id": request_id, "type": "cancel",
                "price": 0, "amount": 0, "date_time": now,
            })
        final_requests.append(request)
        return final_requests

    def _request_decision(self):
        """LLM에 단일 구조화 판단 요청. 실패 시 None(hold)"""
        try:
            response = self.llm_client.create_message(
                self._build_system_prompt(),
                [{"role": "user", "content": self._build_prompt()}],
                [self.DECISION_TOOL],
                tool_choice={"type": "tool", "name": "submit_decision"},
            )
        except Exception as err:
            self.logger.warning(f"LLM decision request failed, fallback to hold: {err}")
            return None

        if not response.tool_calls:
            self.logger.warning("LLM returned no decision tool call, fallback to hold")
            return None

        decision = response.tool_calls[0].arguments
        if decision.get("action") not in ("buy", "sell", "hold"):
            self.logger.warning(f"invalid decision action: {decision}, fallback to hold")
            return None
        self.logger.info(
            f"[LLM DECISION] {decision.get('action')} "
            f"(confidence: {decision.get('confidence')}) - {decision.get('reason')}"
        )
        return decision

    def _decision_to_request(self, decision):
        """판단을 거래 요청으로 변환 + 검증. 실패 시 None(hold)"""
        try:
            price = float(decision.get("price") or 0)
            amount = float(decision.get("amount") or 0)
        except (TypeError, ValueError):
            self.logger.warning(f"invalid price/amount: {decision}")
            return None

        if price <= 0 or amount <= 0:
            self.logger.warning(f"non-positive price/amount: {decision}")
            return None

        total_value = price * amount
        if decision["action"] == "buy":
            if total_value > self.balance or total_value < self.min_price:
                self.logger.warning(
                    f"buy validation failed: total {total_value}, balance {self.balance}")
                return None
        elif decision["action"] == "sell":
            if amount > self.asset_amount:
                self.logger.warning(
                    f"sell validation failed: amount {amount} > asset {self.asset_amount}")
                return None

        return {
            "id": DateConverter.timestamp_id(),
            "type": decision["action"],
            "price": price,
            "amount": amount,
        }

    def _build_system_prompt(self):
        parts = [
            "당신은 암호화폐 매매 판단 전략입니다.",
            "제공된 시장 데이터를 분석하여 submit_decision Tool로 판단을 제출하세요.",
            "리스크 관리를 최우선으로 고려하고, 확신이 없으면 hold를 선택하세요.",
        ]
        if self.strategy_knowledge:
            parts.append("")
            parts.append("## 참고 전략 지식")
            parts.append(self.strategy_knowledge)
        return "\n".join(parts)

    def _build_prompt(self):
        parts = ["[매매 판단 요청]"]
        parts.append(f"최근 캔들 데이터 (최신순 {len(self.data)}개):")
        for candle in self.data[-self.CANDLE_WINDOW:]:
            parts.append(str(candle))
        parts.append("")
        parts.append(f"현재 잔고: {self.balance:,.0f}")
        parts.append(f"보유 수량: {self.asset_amount}")
        if self.result:
            parts.append(f"최근 거래 결과: {self.result[-3:]}")
        parts.append("")
        parts.append("시장 상황을 분석하고 buy/sell/hold 판단을 제출하세요.")
        return "\n".join(parts)

    def _load_strategy_knowledge(self, strategy_files):
        parts = []
        base_dir = os.path.join(os.path.dirname(__file__), "..", "strategies")
        for filename in strategy_files:
            filepath = os.path.join(base_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    parts.append(f.read())
            except FileNotFoundError:
                self.logger.warning(f"Strategy file not found: {filepath}")
        return "\n\n---\n\n".join(parts)
```

`smtm/strategy/strategy_factory.py` 수정 — import 추가, 리스트 등록, create의 llm_client 주입:

```python
from .strategy_bnh import StrategyBuyAndHold
from .strategy_rsi import StrategyRsi
from .strategy_sma import StrategySma
from .strategy_llm import StrategyLlm


class StrategyFactory:
    """Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

    STRATEGY_LIST = [
        StrategyBuyAndHold,
        StrategyRsi,
        StrategySma,
        StrategyLlm,
    ]

    @staticmethod
    def create(code, llm_client=None):
        """code에 해당하는 Strategy 객체를 생성하여 반환. llm_client는 LLM 전략에만 주입"""
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                if strategy is StrategyLlm:
                    return StrategyLlm(llm_client=llm_client)
                return strategy()
        return None
```

(`get_name`/`get_all_strategy_info`는 기존 그대로)

`smtm/strategy/__init__.py`에 `from .strategy_llm import StrategyLlm` 추가 (strategy_factory import보다 위).
`smtm/__init__.py`에 `from .strategy.strategy_llm import StrategyLlm` 추가.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/strategy_llm_test.py tests/unit_tests/strategy_factory_test.py -q` → PASS

```bash
git add smtm/strategy/ smtm/__init__.py tests/unit_tests/strategy_llm_test.py
git commit -m "[feat] add StrategyLlm with single structured decision per tick"
```

---

### Task 10: ProfileStore — 프로파일 JSON CRUD

**Files:**
- Create: `smtm/profile_store.py`
- Modify: `smtm/__init__.py`
- Test: `tests/unit_tests/profile_store_test.py`

**Interfaces:**
- Produces: `ProfileStore(dir_path="config/profiles")` — `list_profiles() -> list[dict]`(요약: name/strategy/exchange/virtual), `load(name) -> dict`, `save(profile: dict) -> dict`, `delete(name) -> bool`, `validate(profile)`(ValueError). 허용 필드: `name, exchange, currency, budget, virtual, term, strategy, strategy_params, safety`. `name`은 `^[A-Za-z0-9_-]{1,64}$`.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/profile_store_test.py`:

```python
import json
import os
import unittest
import tempfile
from smtm import ProfileStore


PROFILE = {
    "name": "test-btc-virtual",
    "exchange": "UPB",
    "currency": "BTC",
    "budget": 500000,
    "virtual": True,
    "term": 60,
    "strategy": "BNH",
    "strategy_params": {},
    "safety": {"max_trade_amount": 100000},
}


class ProfileStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(dir_path=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_save_and_load_roundtrip(self):
        self.store.save(PROFILE)
        loaded = self.store.load("test-btc-virtual")
        self.assertEqual(loaded, PROFILE)
        self.assertTrue(os.path.exists(
            os.path.join(self.tmp.name, "test-btc-virtual.json")))

    def test_list_profiles_returns_summaries(self):
        self.store.save(PROFILE)
        self.store.save({**PROFILE, "name": "second", "strategy": "RSI"})
        profiles = self.store.list_profiles()
        names = {p["name"] for p in profiles}
        self.assertEqual(names, {"test-btc-virtual", "second"})
        self.assertIn("strategy", profiles[0])

    def test_delete_removes_profile(self):
        self.store.save(PROFILE)
        self.assertTrue(self.store.delete("test-btc-virtual"))
        self.assertEqual(self.store.list_profiles(), [])
        self.assertFalse(self.store.delete("test-btc-virtual"))

    def test_load_missing_profile_raises(self):
        with self.assertRaises(ValueError):
            self.store.load("nope")

    def test_save_rejects_invalid_name(self):
        with self.assertRaises(ValueError):
            self.store.save({**PROFILE, "name": "../evil"})
        with self.assertRaises(ValueError):
            self.store.save({**PROFILE, "name": ""})

    def test_save_rejects_unknown_field(self):
        with self.assertRaises(ValueError):
            self.store.save({**PROFILE, "hack": 1})

    def test_save_rejects_missing_name(self):
        profile = dict(PROFILE)
        del profile["name"]
        with self.assertRaises(ValueError):
            self.store.save(profile)

    def test_load_ignores_corrupt_json_in_list(self):
        self.store.save(PROFILE)
        with open(os.path.join(self.tmp.name, "broken.json"), "w") as f:
            f.write("{not json")
        profiles = self.store.list_profiles()
        self.assertEqual(len(profiles), 1)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/profile_store_test.py -x -q`
Expected: FAIL — `ImportError: cannot import name 'ProfileStore'`

- [ ] **Step 3: 구현**

`smtm/profile_store.py`:

```python
import json
import os
import re
from .log_manager import LogManager


class ProfileStore:
    """계좌 프로파일(실행 프리셋 번들) JSON 영속화 저장소.

    파일 1개 = 프로파일 1개, 경로: <dir_path>/<name>.json
    """

    ALLOWED_FIELDS = {
        "name", "exchange", "currency", "budget", "virtual",
        "term", "strategy", "strategy_params", "safety",
    }
    NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,64}$")

    def __init__(self, dir_path="config/profiles"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.dir_path = dir_path

    def validate(self, profile: dict):
        if not isinstance(profile, dict):
            raise ValueError("프로파일은 딕셔너리여야 합니다")
        name = profile.get("name")
        if not name or not self.NAME_PATTERN.match(str(name)):
            raise ValueError(
                "프로파일 이름은 영문/숫자/-/_ 1~64자여야 합니다")
        unknown = set(profile.keys()) - self.ALLOWED_FIELDS
        if unknown:
            raise ValueError(f"알 수 없는 프로파일 필드: {', '.join(sorted(unknown))}")

    def save(self, profile: dict) -> dict:
        self.validate(profile)
        os.makedirs(self.dir_path, exist_ok=True)
        with open(self._path(profile["name"]), "w", encoding="utf-8") as f:
            json.dump(profile, f, ensure_ascii=False, indent=2)
        return profile

    def load(self, name: str) -> dict:
        path = self._path(name)
        if not self.NAME_PATTERN.match(str(name)) or not os.path.exists(path):
            raise ValueError(f"프로파일을 찾을 수 없습니다: {name}")
        with open(path, "r", encoding="utf-8") as f:
            profile = json.load(f)
        self.validate(profile)
        return profile

    def delete(self, name: str) -> bool:
        path = self._path(name)
        if not self.NAME_PATTERN.match(str(name)) or not os.path.exists(path):
            return False
        os.remove(path)
        return True

    def list_profiles(self) -> list:
        if not os.path.isdir(self.dir_path):
            return []
        summaries = []
        for filename in sorted(os.listdir(self.dir_path)):
            if not filename.endswith(".json"):
                continue
            try:
                with open(os.path.join(self.dir_path, filename), "r",
                          encoding="utf-8") as f:
                    profile = json.load(f)
                summaries.append({
                    "name": profile.get("name"),
                    "strategy": profile.get("strategy"),
                    "exchange": profile.get("exchange"),
                    "virtual": profile.get("virtual"),
                })
            except (json.JSONDecodeError, OSError) as err:
                self.logger.warning(f"invalid profile file {filename}: {err}")
        return summaries

    def _path(self, name: str) -> str:
        return os.path.join(self.dir_path, f"{name}.json")
```

`smtm/__init__.py`에 `from .profile_store import ProfileStore` 추가.

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/profile_store_test.py -q` → PASS

```bash
git add smtm/profile_store.py smtm/__init__.py tests/unit_tests/profile_store_test.py
git commit -m "[feat] add ProfileStore for account profile JSON persistence"
```

---

### Task 11: SystemOperator — LlmOperator를 오케스트레이션 전용으로 전환

가장 큰 태스크. `LlmOperator` → `SystemOperator` 전환, 매매 Tool 제거, `TradingOperator` 소유·지휘.

**Files:**
- Create: `smtm/llm/system_operator.py`, `tests/unit_tests/system_operator_test.py`
- Modify: `smtm/llm/__init__.py`, `smtm/__init__.py`, `smtm/llm/tool_router.py`, `smtm/llm/safety_guard.py`, `smtm/controller/controller.py`(임시 최소 수정), `smtm/controller/jpt_controller.py`, `smtm/controller/telegram/telegram_controller.py`, `tests/unit_tests/tool_router_test.py`
- Delete: `smtm/llm/llm_operator.py`, `smtm/llm/tools/trade_tool.py`, `tests/unit_tests/llm_operator_test.py`, `tests/unit_tests/llm_operator_paper_test.py`, `tests/unit_tests/trade_tool_test.py`, `tests/integration_tests/llm_operator_ITG_test.py`

**Interfaces:**
- Consumes: `TradingOperator`(Task 7), `StrategyFactory`(Task 4/9), `Analyzer`(Task 6), `SafetyGuard`(Task 5), `ProfileStore`(Task 10), 기존 `DataProviderFactory`/`TraderFactory`/`SystemMonitor`/읽기 Tool 4종
- Produces: `SystemOperator(llm_client, config, profile_store=None)` — `setup()`, `chat(message) -> str`, `select_strategy(code) -> dict`, `start_trading() -> dict`, `stop_trading() -> dict`, `get_status() -> dict`, `apply_profile(profile: dict) -> dict`. config 키: `exchange, currency, budget, interval, virtual, strategy, strategy_params, safety, strategy_files, context, monitor_storage_path`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/system_operator_test.py`:

```python
import unittest
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse, ToolCall


class StubLlmClient(LlmClient):
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.call_log = []

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        self.call_log.append({"system_prompt": system_prompt, "messages": messages,
                              "tools": tools})
        if not self.responses:
            return LlmResponse(text="ok")
        return self.responses.pop(0)


def make_operator(config_extra=None, responses=None):
    config = {
        "exchange": "UPB", "currency": "BTC", "budget": 500000,
        "interval": 60, "virtual": True, "strategy": "BNH",
        **(config_extra or {}),
    }
    operator = SystemOperator(StubLlmClient(responses), config)
    operator.setup()
    return operator


class SystemOperatorSetupTests(unittest.TestCase):
    def test_setup_builds_trading_operator_with_default_strategy(self):
        operator = make_operator()
        self.assertIsNotNone(operator.trading_operator)
        self.assertEqual(operator.trading_operator.state, "ready")
        self.assertEqual(operator.strategy_code, "BNH")

    def test_setup_without_strategy_falls_back_to_bnh(self):
        operator = make_operator(config_extra={"strategy": None})
        self.assertEqual(operator.strategy_code, "BNH")

    def test_no_trade_tool_registered(self):
        operator = make_operator()
        tool_names = set(operator.tool_router.tools.keys())
        self.assertNotIn("execute_trade", tool_names)
        self.assertIn("get_market_data", tool_names)
        self.assertIn("get_portfolio", tool_names)
        self.assertIn("get_trade_history", tool_names)
        self.assertIn("get_performance", tool_names)


class SystemOperatorOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.operator = make_operator()

    def tearDown(self):
        self.operator.stop_trading()

    def test_start_and_stop_trading(self):
        result = self.operator.start_trading()
        self.assertTrue(result["success"])
        self.assertEqual(self.operator.trading_operator.state, "running")
        result = self.operator.stop_trading()
        self.assertTrue(result["success"])
        self.assertEqual(self.operator.trading_operator.state, "ready")

    def test_select_strategy_rebuilds_with_new_strategy(self):
        result = self.operator.select_strategy("RSI")
        self.assertTrue(result["success"])
        self.assertEqual(self.operator.strategy_code, "RSI")
        self.assertEqual(self.operator.trading_operator.strategy.CODE, "RSI")

    def test_select_strategy_rejected_while_running(self):
        self.operator.start_trading()
        result = self.operator.select_strategy("RSI")
        self.assertFalse(result["success"])
        self.assertEqual(self.operator.strategy_code, "BNH")

    def test_select_unknown_strategy_fails(self):
        result = self.operator.select_strategy("NOPE")
        self.assertFalse(result["success"])

    def test_get_status_contains_key_fields(self):
        status = self.operator.get_status()
        self.assertEqual(status["trading_state"], "ready")
        self.assertEqual(status["strategy"], "BNH")
        self.assertEqual(status["exchange"], "UPB")
        self.assertTrue(status["virtual"])
        self.assertIn("safety", status)

    def test_apply_profile_reconfigures(self):
        result = self.operator.apply_profile({
            "name": "aggressive", "strategy": "RSI", "budget": 300000,
            "virtual": True, "exchange": "UPB", "currency": "BTC",
        })
        self.assertTrue(result["success"])
        self.assertEqual(self.operator.strategy_code, "RSI")
        self.assertEqual(self.operator.budget, 300000)


class SystemOperatorChatTests(unittest.TestCase):
    def test_chat_returns_text(self):
        operator = make_operator(responses=[LlmResponse(text="안녕하세요")])
        self.assertEqual(operator.chat("hi"), "안녕하세요")

    def test_chat_executes_tool_loop(self):
        # get_portfolio는 이 태스크에서 등록되는 읽기 전용 Tool
        # (오케스트레이션 Tool 등록은 Task 12)
        responses = [
            LlmResponse(text="", tool_calls=[
                ToolCall(id="t1", name="get_portfolio", arguments={})
            ], stop_reason="tool_use"),
            LlmResponse(text="포트폴리오입니다"),
        ]
        operator = make_operator(responses=responses)
        result = operator.chat("포트폴리오 알려줘")
        self.assertEqual(result, "포트폴리오입니다")

    def test_chat_trims_history(self):
        operator = make_operator(config_extra={
            "context": {"max_conversation_turns": 2}})
        for i in range(5):
            operator.llm_client.responses.append(LlmResponse(text=f"r{i}"))
            operator.chat(f"m{i}")
        self.assertLessEqual(len(operator.conversation_history), 4)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/system_operator_test.py -x -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'smtm.llm.system_operator'`

- [ ] **Step 3: SystemOperator 구현**

`smtm/llm/system_operator.py` (llm_operator.py의 chat/tool loop/이력 로직을 이관하되 타이머·매매 제거):

```python
import os
from dataclasses import dataclass
from ..log_manager import LogManager
from .tool_router import ToolRouter
from .safety_guard import SafetyGuard, SafetyConfig
from .system_monitor import SystemMonitor


@dataclass
class ContextConfig:
    """LLM에 전달할 컨텍스트 범위 설정"""
    candle_count: int = 20
    include_portfolio: bool = True
    include_trade_history: bool = True
    trade_history_count: int = 10
    max_conversation_turns: int = 50


class SystemOperator:
    """시스템 운영 LLM 에이전트 — 오케스트레이션 전용.

    직접 매매하지 않는다. 매매는 TradingOperator의 Strategy → Trader 단일 경로.
    """

    DEFAULT_STRATEGY = "BNH"

    def __init__(self, llm_client, config: dict, profile_store=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.llm_client = llm_client
        self.config = config
        self.state = "ready"
        self.budget = config.get("budget", 500000)
        self.profile_store = profile_store

        self.system_monitor = SystemMonitor(
            storage_path=config.get("monitor_storage_path", "output/monitor/"),
        )
        self.tool_router = ToolRouter(self.system_monitor)
        self.context_config = ContextConfig(**config.get("context", {}))
        self.conversation_history = []
        self.strategy_knowledge = self._load_strategy_knowledge(
            config.get("strategy_files", [])
        )

        self.trading_operator = None
        self.data_provider = None
        self.trader = None
        self.safety_guard = None
        self.strategy_code = None
        self.default_strategy_used = False

    # ------------------------------------------------------------------
    # 구성
    # ------------------------------------------------------------------
    def setup(self):
        """트레이딩 컴포넌트 구성 + Tool 등록. Controller가 호출."""
        self._build_trading_components(rebuild_infra=True)

    def _build_trading_components(self, rebuild_infra=True):
        # 순환 import 방지를 위한 지역 import
        from ..data.data_provider_factory import DataProviderFactory
        from ..trader.trader_factory import TraderFactory
        from ..strategy.strategy_factory import StrategyFactory
        from ..trading_operator import TradingOperator
        from ..analyzer import Analyzer
        from ..config import Config

        cfg = self.config
        exchange = cfg.get("exchange", "UPB")
        currency = cfg.get("currency", "BTC")
        strategy_code = cfg.get("strategy") or self.DEFAULT_STRATEGY
        self.default_strategy_used = not cfg.get("strategy")

        if rebuild_infra or self.trader is None:
            self.data_provider = DataProviderFactory.create(
                exchange, currency=currency, interval=Config.candle_interval)
            self.trader = TraderFactory.create(
                exchange, budget=self.budget, currency=currency,
                paper=bool(cfg.get("virtual", False)))
            if self.data_provider is None or self.trader is None:
                raise ValueError(f"올바르지 않은 거래소 코드입니다: {exchange}")

        strategy = StrategyFactory.create(strategy_code, llm_client=self.llm_client)
        if strategy is None:
            raise ValueError(f"올바르지 않은 전략 코드입니다: {strategy_code}")

        analyzer = Analyzer(self.system_monitor)
        self.safety_guard = SafetyGuard(SafetyConfig(
            initial_budget=self.budget, **cfg.get("safety", {})))

        operator = TradingOperator(
            interval=cfg.get("interval", 60), currency=currency)
        operator.initialize(
            self.data_provider, strategy, self.trader, analyzer,
            self.safety_guard, budget=self.budget)
        self.trading_operator = operator
        self.strategy_code = strategy_code
        self._register_tools()

    def _register_tools(self):
        from .tools.market_data_tool import MarketDataTool
        from .tools.portfolio_tool import PortfolioTool
        from .tools.trade_history_tool import TradeHistoryTool
        from .tools.performance_tool import PerformanceTool

        self.tool_router.register(MarketDataTool(self.data_provider))
        self.tool_router.register(PortfolioTool(self.trader))
        self.tool_router.register(TradeHistoryTool(self.system_monitor))
        self.tool_router.register(PerformanceTool(
            self.system_monitor, self.trader, self.budget))

    # ------------------------------------------------------------------
    # 오케스트레이션 API (Tool과 Controller에서 호출)
    # ------------------------------------------------------------------
    def select_strategy(self, code: str) -> dict:
        if self._is_trading_running():
            return {"success": False,
                    "error": "매매 중에는 전략을 변경할 수 없습니다. 먼저 매매를 중지하세요."}
        previous = self.config.get("strategy")
        self.config["strategy"] = code
        try:
            self._build_trading_components(rebuild_infra=False)
        except ValueError as err:
            self.config["strategy"] = previous
            return {"success": False, "error": str(err)}
        return {"success": True, "strategy": code}

    def start_trading(self) -> dict:
        if self.trading_operator is None:
            return {"success": False, "error": "트레이딩 컴포넌트가 구성되지 않았습니다"}
        if self._is_trading_running():
            return {"success": False, "error": "이미 매매가 진행 중입니다"}
        started = self.trading_operator.start()
        if not started:
            return {"success": False, "error": "매매를 시작할 수 없습니다"}
        result = {"success": True, "strategy": self.strategy_code}
        if self.default_strategy_used:
            result["note"] = "전략이 지정되지 않아 기본 전략(BNH)으로 시작했습니다"
        return result

    def stop_trading(self) -> dict:
        if self.trading_operator is None or not self._is_trading_running():
            return {"success": True, "note": "매매가 진행 중이 아닙니다"}
        self.trading_operator.stop()
        return {"success": True}

    def get_status(self) -> dict:
        return {
            "trading_state": self.trading_operator.state if self.trading_operator else None,
            "strategy": self.strategy_code,
            "exchange": self.config.get("exchange"),
            "currency": self.config.get("currency"),
            "budget": self.budget,
            "virtual": bool(self.config.get("virtual", False)),
            "interval": self.config.get("interval", 60),
            "safety": self.safety_guard.get_status() if self.safety_guard else None,
            "llm_usage": self.system_monitor.get_llm_usage(),
        }

    def apply_profile(self, profile: dict) -> dict:
        was_running = self._is_trading_running()
        if was_running:
            self.trading_operator.stop()
        for key in ("exchange", "currency", "budget", "virtual", "term",
                    "strategy", "strategy_params", "safety"):
            if key in profile:
                config_key = "interval" if key == "term" else key
                self.config[config_key] = profile[key]
        self.budget = self.config.get("budget", self.budget)
        try:
            self._build_trading_components(rebuild_infra=True)
        except ValueError as err:
            return {"success": False, "error": str(err)}
        return {"success": True, "profile": profile.get("name"),
                "was_running": was_running,
                "note": "프로파일이 적용되었습니다. 매매를 재개하려면 start_trading을 호출하세요."}

    def _is_trading_running(self) -> bool:
        return (self.trading_operator is not None
                and self.trading_operator.state == "running")

    # ------------------------------------------------------------------
    # 대화 (LlmOperator에서 이관)
    # ------------------------------------------------------------------
    def chat(self, message: str) -> str:
        self.conversation_history.append({"role": "user", "content": message})
        response_text = self._execute_llm_loop()
        self.conversation_history.append(
            {"role": "assistant", "content": response_text})
        self._trim_conversation_history()
        return response_text

    def _execute_llm_loop(self) -> str:
        system_prompt = self._build_system_prompt()
        tools = self.tool_router.get_tool_schemas()
        messages = list(self.conversation_history)

        while True:
            response = self.llm_client.create_message(system_prompt, messages, tools)
            self.system_monitor.log_llm_interaction(
                request={"messages": messages[-1:]},
                response_text=response.text,
                usage=response.usage,
            )
            if not response.has_tool_calls:
                return response.text

            tool_results_content = []
            for tool_call in response.tool_calls:
                result = self.tool_router.execute(tool_call)
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": str(result.to_dict()),
                })
            messages.append({"role": "assistant", "content": response.tool_calls})
            messages.append({"role": "user", "content": tool_results_content})

    def _build_system_prompt(self) -> str:
        parts = [
            "당신은 암호화폐 자동매매 시스템의 운영 에이전트입니다.",
            "직접 매매하지 않습니다. 매매는 선택된 전략(Strategy)이 고정 주기로 수행합니다.",
            "제공된 Tool로 전략을 조회·선택하고, 매매를 시작/중지하고, 상태와 성과를 확인하고,",
            "프로파일(실행 프리셋)을 관리하세요.",
            "사용자의 요청을 정확히 파악하고, 위험한 변경(전략 전환, 프로파일 전환)은",
            "실행 전에 사용자에게 확인하세요.",
            "",
        ]
        if self.strategy_knowledge:
            parts.append("## 참고 전략 지식")
            parts.append(self.strategy_knowledge)
            parts.append("")
        parts.append("## 현재 설정")
        parts.append(f"- 거래소: {self.config.get('exchange', 'N/A')}")
        parts.append(f"- 통화: {self.config.get('currency', 'N/A')}")
        parts.append(f"- 초기 예산: {self.budget:,.0f}")
        parts.append(f"- 현재 전략: {self.strategy_code or 'N/A'}")
        parts.append(f"- 가상매매: {'예' if self.config.get('virtual') else '아니오'}")
        return "\n".join(parts)

    def _trim_conversation_history(self):
        max_messages = self.context_config.max_conversation_turns * 2
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    def _load_strategy_knowledge(self, strategy_files: list) -> str:
        parts = []
        base_dir = os.path.join(os.path.dirname(__file__), "..", "strategies")
        for filename in strategy_files:
            filepath = os.path.join(base_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    parts.append(f.read())
            except FileNotFoundError:
                self.logger.warning(f"Strategy file not found: {filepath}")
        return "\n\n---\n\n".join(parts)
```

- [ ] **Step 4: ToolRouter 슬림화 (safety_guard 제거)**

`smtm/llm/tool_router.py` — `__init__(self, system_monitor)`로 변경, `check`/`record_trade` 블록 제거:

```python
from typing import Dict
from ..log_manager import LogManager
from .tool import Tool, ToolResult
from .llm_client import ToolCall
from .system_monitor import SystemMonitor


class ToolRouter:
    """Tool 등록, 라우팅, 실행"""

    def __init__(self, system_monitor: SystemMonitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.tools: Dict[str, Tool] = {}
        self.system_monitor = system_monitor

    def register(self, tool: Tool):
        self.tools[tool.name] = tool
        self.logger.info(f"Tool registered: {tool.name}")

    def get_tool_schemas(self) -> list:
        return [tool.get_schema() for tool in self.tools.values()]

    def execute(self, tool_call: ToolCall) -> ToolResult:
        if tool_call.name not in self.tools:
            error = f"Tool not found: {tool_call.name}"
            self.logger.error(error)
            return ToolResult(success=False, error=error)

        tool = self.tools[tool_call.name]
        try:
            result = tool.execute(tool_call.arguments)
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_call.name} - {e}")
            result = ToolResult(success=False, error=str(e))

        self.system_monitor.log_tool_call(
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            result=result.to_dict(),
        )
        return result
```

`smtm/llm/safety_guard.py` — 이제 미사용이 된 `check(tool_call)` 메서드와 `TRADE_TOOLS` 상수 삭제. `get_status`의 `trading_allowed`를 `check_request` 기반으로 교체:

```python
            "trading_allowed": self.check_request(
                {"type": "buy", "price": 1, "amount": 1}
            ).allowed,
```

- [ ] **Step 5: 삭제 및 배선 교체**

```bash
git rm smtm/llm/llm_operator.py smtm/llm/tools/trade_tool.py
git rm tests/unit_tests/llm_operator_test.py tests/unit_tests/llm_operator_paper_test.py
git rm tests/unit_tests/trade_tool_test.py tests/integration_tests/llm_operator_ITG_test.py
```

`smtm/llm/__init__.py`:

```python
from .llm_client import LlmClient, LlmResponse, ToolCall
from .claude_llm_client import ClaudeLlmClient
from .tool import Tool, ToolResult
from .tool_router import ToolRouter
from .safety_guard import SafetyGuard, SafetyConfig, SafetyResult
from .system_monitor import SystemMonitor
from .system_operator import SystemOperator, ContextConfig
```

`smtm/controller/controller.py` 전체 교체 (`--strategy`는 Task 14에서 CLI 배선되지만 생성자 파라미터는 지금 추가):

```python
import os
import signal
from ..config import Config
from ..log_manager import LogManager
from ..llm.system_operator import SystemOperator
from ..llm.claude_llm_client import ClaudeLlmClient
from ..profile_store import ProfileStore


class Controller:
    """LLM 기반 CLI 컨트롤러 — SystemOperator를 통해 시스템을 제어"""

    MAIN_STATEMENT = "메시지를 입력하세요 (q: 종료): "

    def __init__(
        self,
        interval=60,
        budget=500000,
        currency="BTC",
        exchange="UPB",
        paper=False,
        strategy="BNH",
    ):
        self.logger = LogManager.get_logger("Controller")
        self.terminating = False
        self.interval = float(interval)
        self.budget = int(budget)
        self.currency = currency
        self.exchange = exchange
        self.paper = paper
        self.strategy = strategy
        LogManager.set_stream_level(Config.operation_log_level)

    def main(self):
        api_key = os.environ.get("SMTM_LLM_API_KEY", "")
        if not api_key:
            print("SMTM_LLM_API_KEY 환경변수를 설정해주세요")
            return

        llm_client = ClaudeLlmClient(api_key=api_key)
        config = {
            "exchange": self.exchange,
            "currency": self.currency,
            "budget": self.budget,
            "interval": self.interval,
            "virtual": self.paper,
            "strategy": self.strategy,
            "strategy_files": ["sma_crossover.md", "rsi_strategy.md", "buy_and_hold.md"],
        }
        operator = SystemOperator(llm_client, config,
                                  profile_store=ProfileStore())
        try:
            operator.setup()
        except ValueError as err:
            print(str(err))
            return

        print("##### smtm LLM trading system is initialized #####")
        print(f"exchange: {self.exchange}, currency: {self.currency}, "
              f"budget: {self.budget}, strategy: {self.strategy}")
        if self.paper:
            print("!! 가상거래 모드 - 실제 주문은 전송되지 않습니다")
        print("'start'를 입력하면 자동 매매가 시작됩니다")
        print("==============================")

        signal.signal(signal.SIGINT, lambda s, f: self._terminate(operator))
        signal.signal(signal.SIGTERM, lambda s, f: self._terminate(operator))

        while not self.terminating:
            try:
                message = input(self.MAIN_STATEMENT)
                if message.lower() in ("q", "quit", "exit", "terminate"):
                    self._terminate(operator)
                    break
                if message.lower() == "start":
                    result = operator.start_trading()
                    print("자동 매매가 시작되었습니다" if result.get("success")
                          else f"시작 실패: {result.get('error')}")
                    continue
                if message.lower() == "stop":
                    operator.stop_trading()
                    print("자동 매매가 중지되었습니다")
                    continue
                response = operator.chat(message)
                print(f"\n{response}\n")
            except EOFError:
                break

    def _terminate(self, operator):
        print("프로그램 종료 중.....")
        operator.stop_trading()
        self.terminating = True
        print("Good Bye~")
```

`smtm/controller/jpt_controller.py`와 `smtm/controller/telegram/telegram_controller.py` — 같은 패턴으로 최소 수정 (3곳):

```python
# before                                          # after
from ...llm.llm_operator import LlmOperator   →   from ...llm.system_operator import SystemOperator
self.operator = LlmOperator(llm_client, config) → self.operator = SystemOperator(llm_client, config)
self.operator.setup_tools(data_provider=..., trader=...) → self.operator.setup()
```

두 파일에서 `DataProviderFactory`/`TraderFactory`로 provider/trader를 직접 만드는 블록과 해당 import를 삭제하고(SystemOperator가 내부에서 생성), config dict에 `"virtual": <기존 paper 배선 값 또는 False>`, `"strategy": "BNH"` 키를 추가한다. `operator.start_trading()`/`stop_trading()` 호출부는 시그니처 동일(반환 dict는 기존 호출부에서 미사용)이므로 그대로 둔다.

`tests/unit_tests/tool_router_test.py` — `ToolRouter(safety_guard, monitor)` 생성 코드를 `ToolRouter(monitor)`로 바꾸고 SafetyGuard 차단/record_trade 관련 테스트 삭제 (해당 동작은 Task 7 TradingOperator 테스트로 대체됨).

- [ ] **Step 6: 통과 확인**

Run: `python -m pytest tests/unit_tests/ -q`
Expected: PASS (llm_operator 관련 테스트는 삭제됨, system_operator_test 통과)

Run: `python -c "from smtm.llm import SystemOperator; import smtm.__main__; print('ok')"` — import 회귀 확인
(주의: `smtm/__init__.py`에 SystemOperator를 추가하지 않는다 — 기존에도 LlmOperator는 root export가 아니었음. `smtm.llm.SystemOperator`로 접근)

- [ ] **Step 7: 커밋**

```bash
git add -A
git commit -m "[refactor] replace LlmOperator with orchestration-only SystemOperator owning TradingOperator"
```

---

### Task 12: 오케스트레이션 Tool 6종

**Files:**
- Create: `smtm/llm/tools/orchestration_tools.py`
- Modify: `smtm/llm/system_operator.py` (`_register_tools`에 등록)
- Test: `tests/unit_tests/orchestration_tools_test.py`

**Interfaces:**
- Consumes: `SystemOperator.select_strategy/start_trading/stop_trading/get_status`(Task 11), `StrategyFactory`(Task 4/9), `TradingOperator.get_score`(Task 7)
- Produces: Tool 6종 — `list_strategies`, `describe_strategy(code)`, `select_strategy(code)`, `start_trading`, `stop_trading`, `get_status`

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/orchestration_tools_test.py`:

```python
import unittest
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


def make_operator():
    operator = SystemOperator(StubLlmClient(), {
        "exchange": "UPB", "currency": "BTC", "budget": 500000,
        "interval": 60, "virtual": True, "strategy": "BNH",
    })
    operator.setup()
    return operator


class OrchestrationToolsTests(unittest.TestCase):
    def setUp(self):
        self.operator = make_operator()
        self.tools = self.operator.tool_router.tools

    def tearDown(self):
        self.operator.stop_trading()

    def test_all_orchestration_tools_registered(self):
        for name in ("list_strategies", "describe_strategy", "select_strategy",
                     "start_trading", "stop_trading", "get_status"):
            self.assertIn(name, self.tools)

    def test_list_strategies_returns_codes(self):
        result = self.tools["list_strategies"].execute({})
        self.assertTrue(result.success)
        codes = [s["code"] for s in result.data["strategies"]]
        self.assertEqual(set(codes), {"BNH", "RSI", "SMA", "LLM"})

    def test_describe_strategy_returns_description(self):
        result = self.tools["describe_strategy"].execute({"code": "BNH"})
        self.assertTrue(result.success)
        self.assertEqual(result.data["code"], "BNH")
        self.assertIn("description", result.data)

    def test_describe_unknown_strategy_fails(self):
        result = self.tools["describe_strategy"].execute({"code": "NOPE"})
        self.assertFalse(result.success)

    def test_select_strategy_tool_changes_strategy(self):
        result = self.tools["select_strategy"].execute({"code": "SMA"})
        self.assertTrue(result.success)
        self.assertEqual(self.operator.strategy_code, "SMA")

    def test_start_stop_get_status_flow(self):
        result = self.tools["start_trading"].execute({})
        self.assertTrue(result.success)
        status = self.tools["get_status"].execute({})
        self.assertEqual(status.data["trading_state"], "running")
        result = self.tools["stop_trading"].execute({})
        self.assertTrue(result.success)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/orchestration_tools_test.py -x -q`
Expected: FAIL — `KeyError`/`AssertionError` (Tool 미등록)

- [ ] **Step 3: 구현**

`smtm/llm/tools/orchestration_tools.py`:

```python
from ..tool import Tool, ToolResult


class ListStrategiesTool(Tool):
    name = "list_strategies"
    description = "사용 가능한 매매 전략 목록을 조회합니다 (코드/이름)"
    input_schema = {"type": "object", "properties": {}}

    def execute(self, arguments: dict) -> ToolResult:
        from ...strategy.strategy_factory import StrategyFactory
        strategies = [
            {"code": info["code"], "name": info["name"]}
            for info in StrategyFactory.get_all_strategy_info()
        ]
        return ToolResult(success=True, data={"strategies": strategies})


class DescribeStrategyTool(Tool):
    name = "describe_strategy"
    description = "특정 전략의 상세 설명을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "전략 코드"}},
        "required": ["code"],
    }

    def execute(self, arguments: dict) -> ToolResult:
        from ...strategy.strategy_factory import StrategyFactory
        for info in StrategyFactory.get_all_strategy_info():
            if info["code"] == arguments.get("code"):
                description = (info["class"].__doc__ or "").strip()
                return ToolResult(success=True, data={
                    "code": info["code"], "name": info["name"],
                    "description": description,
                })
        return ToolResult(success=False,
                          error=f"알 수 없는 전략 코드: {arguments.get('code')}")


class SelectStrategyTool(Tool):
    name = "select_strategy"
    description = ("매매 전략을 선택합니다. 매매 중에는 변경할 수 없으며 "
                   "먼저 stop_trading이 필요합니다")
    input_schema = {
        "type": "object",
        "properties": {"code": {"type": "string", "description": "전략 코드 (list_strategies로 조회)"}},
        "required": ["code"],
    }

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        result = self.operator.select_strategy(arguments.get("code"))
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))


class StartTradingTool(Tool):
    name = "start_trading"
    description = "선택된 전략으로 고정 주기 자동 매매를 시작합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        result = self.operator.start_trading()
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))


class StopTradingTool(Tool):
    name = "stop_trading"
    description = "자동 매매를 중지합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        result = self.operator.stop_trading()
        return ToolResult(success=True, data=result)


class GetStatusTool(Tool):
    name = "get_status"
    description = "시스템 상태(매매 상태/전략/설정/안전장치/토큰 사용량)를 조회합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, operator):
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(success=True, data=self.operator.get_status())
```

`smtm/llm/system_operator.py`의 `_register_tools` 끝에 추가:

```python
        from .tools.orchestration_tools import (
            ListStrategiesTool, DescribeStrategyTool, SelectStrategyTool,
            StartTradingTool, StopTradingTool, GetStatusTool,
        )
        self.tool_router.register(ListStrategiesTool())
        self.tool_router.register(DescribeStrategyTool())
        self.tool_router.register(SelectStrategyTool(self))
        self.tool_router.register(StartTradingTool(self))
        self.tool_router.register(StopTradingTool(self))
        self.tool_router.register(GetStatusTool(self))
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/orchestration_tools_test.py tests/unit_tests/system_operator_test.py -q` → PASS

```bash
git add smtm/llm/tools/orchestration_tools.py smtm/llm/system_operator.py tests/unit_tests/orchestration_tools_test.py
git commit -m "[feat] add orchestration tools for strategy control via agent"
```

---

### Task 13: 프로파일 CRUD Tool 6종

**Files:**
- Create: `smtm/llm/tools/profile_tools.py`
- Modify: `smtm/llm/system_operator.py` (`_register_tools`에 조건부 등록)
- Test: `tests/unit_tests/profile_tools_test.py`

**Interfaces:**
- Consumes: `ProfileStore`(Task 10), `SystemOperator.apply_profile`(Task 11)
- Produces: Tool 6종 — `list_profiles`, `describe_profile(name)`, `create_profile(...)`, `update_profile(name, ...)`, `delete_profile(name)`, `switch_profile(name)`. `profile_store`가 None이면 미등록.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/unit_tests/profile_tools_test.py`:

```python
import unittest
import tempfile
from smtm import ProfileStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


class ProfileToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(dir_path=self.tmp.name)
        self.operator = SystemOperator(StubLlmClient(), {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "interval": 60, "virtual": True, "strategy": "BNH",
        }, profile_store=self.store)
        self.operator.setup()
        self.tools = self.operator.tool_router.tools

    def tearDown(self):
        self.operator.stop_trading()
        self.tmp.cleanup()

    def test_profile_tools_registered(self):
        for name in ("list_profiles", "describe_profile", "create_profile",
                     "update_profile", "delete_profile", "switch_profile"):
            self.assertIn(name, self.tools)

    def test_create_and_list_profile(self):
        result = self.tools["create_profile"].execute({
            "name": "aggressive-rsi", "strategy": "RSI",
            "budget": 300000, "virtual": True,
        })
        self.assertTrue(result.success)
        listing = self.tools["list_profiles"].execute({})
        names = [p["name"] for p in listing.data["profiles"]]
        self.assertIn("aggressive-rsi", names)

    def test_describe_profile(self):
        self.tools["create_profile"].execute({"name": "p1", "strategy": "BNH"})
        result = self.tools["describe_profile"].execute({"name": "p1"})
        self.assertTrue(result.success)
        self.assertEqual(result.data["profile"]["strategy"], "BNH")

    def test_update_profile_merges_fields(self):
        self.tools["create_profile"].execute({"name": "p1", "strategy": "BNH",
                                              "budget": 100000})
        result = self.tools["update_profile"].execute({"name": "p1",
                                                       "strategy": "SMA"})
        self.assertTrue(result.success)
        loaded = self.store.load("p1")
        self.assertEqual(loaded["strategy"], "SMA")
        self.assertEqual(loaded["budget"], 100000)  # 기존 값 유지

    def test_delete_profile(self):
        self.tools["create_profile"].execute({"name": "p1"})
        result = self.tools["delete_profile"].execute({"name": "p1"})
        self.assertTrue(result.success)
        self.assertEqual(self.store.list_profiles(), [])

    def test_switch_profile_applies_config(self):
        self.tools["create_profile"].execute({
            "name": "rsi-small", "strategy": "RSI", "budget": 200000,
            "virtual": True,
        })
        result = self.tools["switch_profile"].execute({"name": "rsi-small"})
        self.assertTrue(result.success)
        self.assertEqual(self.operator.strategy_code, "RSI")
        self.assertEqual(self.operator.budget, 200000)

    def test_switch_missing_profile_fails(self):
        result = self.tools["switch_profile"].execute({"name": "nope"})
        self.assertFalse(result.success)

    def test_create_invalid_name_fails(self):
        result = self.tools["create_profile"].execute({"name": "../evil"})
        self.assertFalse(result.success)


class ProfileToolsAbsentTests(unittest.TestCase):
    def test_no_profile_tools_without_store(self):
        operator = SystemOperator(StubLlmClient(), {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "virtual": True, "strategy": "BNH",
        })
        operator.setup()
        self.assertNotIn("list_profiles", operator.tool_router.tools)
```

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/profile_tools_test.py -x -q`
Expected: FAIL

- [ ] **Step 3: 구현**

`smtm/llm/tools/profile_tools.py`:

```python
from ..tool import Tool, ToolResult

PROFILE_PROPERTIES = {
    "name": {"type": "string", "description": "프로파일 이름 (영문/숫자/-/_)"},
    "exchange": {"type": "string", "description": "거래소 코드 예: UPB"},
    "currency": {"type": "string", "description": "거래 통화 예: BTC"},
    "budget": {"type": "number", "description": "초기 예산"},
    "virtual": {"type": "boolean", "description": "가상매매 여부"},
    "term": {"type": "number", "description": "매매 주기(초)"},
    "strategy": {"type": "string", "description": "전략 코드 예: BNH/RSI/SMA/LLM"},
    "strategy_params": {"type": "object", "description": "전략 파라미터"},
    "safety": {"type": "object", "description": "안전장치 설정"},
}


class ListProfilesTool(Tool):
    name = "list_profiles"
    description = "저장된 계좌 프로파일 목록을 조회합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        return ToolResult(success=True,
                          data={"profiles": self.store.list_profiles()})


class DescribeProfileTool(Tool):
    name = "describe_profile"
    description = "특정 프로파일의 전체 내용을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {"name": PROFILE_PROPERTIES["name"]},
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.load(arguments.get("name"))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        return ToolResult(success=True, data={"profile": profile})


class CreateProfileTool(Tool):
    name = "create_profile"
    description = "새 계좌 프로파일(실행 프리셋)을 생성하여 저장합니다"
    input_schema = {
        "type": "object",
        "properties": PROFILE_PROPERTIES,
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.save(dict(arguments))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        return ToolResult(success=True, data={"profile": profile})


class UpdateProfileTool(Tool):
    name = "update_profile"
    description = "기존 프로파일의 일부 필드를 수정합니다 (미지정 필드는 유지)"
    input_schema = {
        "type": "object",
        "properties": PROFILE_PROPERTIES,
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.load(arguments.get("name"))
            profile.update(arguments)
            profile = self.store.save(profile)
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        return ToolResult(success=True, data={"profile": profile})


class DeleteProfileTool(Tool):
    name = "delete_profile"
    description = "프로파일을 삭제합니다"
    input_schema = {
        "type": "object",
        "properties": {"name": PROFILE_PROPERTIES["name"]},
        "required": ["name"],
    }

    def __init__(self, store):
        self.store = store

    def execute(self, arguments: dict) -> ToolResult:
        if self.store.delete(arguments.get("name")):
            return ToolResult(success=True, data={"deleted": arguments.get("name")})
        return ToolResult(success=False,
                          error=f"프로파일을 찾을 수 없습니다: {arguments.get('name')}")


class SwitchProfileTool(Tool):
    name = "switch_profile"
    description = ("프로파일을 로드하여 시스템 구성을 전환합니다. "
                   "매매 중이면 중지 후 적용되며, 재시작은 별도로 start_trading을 호출해야 합니다")
    input_schema = {
        "type": "object",
        "properties": {"name": PROFILE_PROPERTIES["name"]},
        "required": ["name"],
    }

    def __init__(self, store, operator):
        self.store = store
        self.operator = operator

    def execute(self, arguments: dict) -> ToolResult:
        try:
            profile = self.store.load(arguments.get("name"))
        except ValueError as err:
            return ToolResult(success=False, error=str(err))
        result = self.operator.apply_profile(profile)
        if result.get("success"):
            return ToolResult(success=True, data=result)
        return ToolResult(success=False, error=result.get("error"))
```

`smtm/llm/system_operator.py`의 `_register_tools` 끝에 추가:

```python
        if self.profile_store is not None:
            from .tools.profile_tools import (
                ListProfilesTool, DescribeProfileTool, CreateProfileTool,
                UpdateProfileTool, DeleteProfileTool, SwitchProfileTool,
            )
            self.tool_router.register(ListProfilesTool(self.profile_store))
            self.tool_router.register(DescribeProfileTool(self.profile_store))
            self.tool_router.register(CreateProfileTool(self.profile_store))
            self.tool_router.register(UpdateProfileTool(self.profile_store))
            self.tool_router.register(DeleteProfileTool(self.profile_store))
            self.tool_router.register(SwitchProfileTool(self.profile_store, self))
```

- [ ] **Step 4: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/profile_tools_test.py -q` → PASS

```bash
git add smtm/llm/tools/profile_tools.py smtm/llm/system_operator.py tests/unit_tests/profile_tools_test.py
git commit -m "[feat] add profile CRUD tools for agent-managed account profiles"
```

---

### Task 14: Controller + __main__ 배선 (--strategy / --profile)

**Files:**
- Modify: `smtm/controller/controller.py`, `smtm/__main__.py`
- Test: `tests/unit_tests/main_config_test.py` (테스트 추가/수정)

**Interfaces:**
- Consumes: `SystemOperator`(Task 11~13), `ProfileStore`(Task 10)
- Produces: CLI `--strategy CODE`(기본 `"BNH"`), `--profile NAME`; config 파일 키 `strategy` 허용. `Controller(interval, budget, currency, exchange, paper, strategy, profile)`

- [ ] **Step 1: 실패하는 테스트 추가**

`tests/unit_tests/main_config_test.py`에 추가 (기존 테스트의 패턴을 따름 — 파일 상단 import 확인):

```python
class StrategyProfileConfigTests(unittest.TestCase):
    def test_default_strategy_is_bnh(self):
        _, args = parse_args([])
        self.assertEqual(args.strategy, "BNH")

    def test_strategy_flag_overrides_default(self):
        _, args = parse_args(["--strategy", "RSI"])
        self.assertEqual(args.strategy, "RSI")

    def test_config_file_strategy_key_is_accepted(self):
        import json, tempfile
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"strategy": "SMA"}, f)
            path = f.name
        _, args = parse_args(["--config", path])
        self.assertEqual(args.strategy, "SMA")

    def test_profile_flag_parsed(self):
        _, args = parse_args(["--profile", "my-profile"])
        self.assertEqual(args.profile, "my-profile")
```

주의: 기존 `main_config_test.py`에 DEFAULT_CONFIG 전체를 비교하는 테스트가 있으면 `strategy`/`profile` 키 추가에 맞춰 기대값을 수정한다.

- [ ] **Step 2: 실패 확인**

Run: `python -m pytest tests/unit_tests/main_config_test.py -x -q`
Expected: FAIL — `AttributeError: 'Namespace' object has no attribute 'strategy'`

- [ ] **Step 3: __main__ 수정**

`smtm/__main__.py`:

- `DEFAULT_CONFIG`에 `"strategy": "BNH"` 추가 (주의: `"profile"`은 DEFAULT_CONFIG에 넣지 않는다 — config 파일 키가 아니라 CLI 전용)
- `build_parser()`에 추가:

```python
    parser.add_argument(
        "--strategy",
        help="trading strategy code (BNH, RSI, SMA, LLM)",
        default=None,
    )
    parser.add_argument(
        "--profile",
        help="account profile name in config/profiles/",
        default=None,
    )
```

- `merge_config(args)` 수정 — 프로파일 로드를 config 파일과 CLI 플래그 사이에 적용:

```python
def merge_config(args):
    config = dict(DEFAULT_CONFIG)
    if args.config:
        config.update(load_config(args.config))

    if getattr(args, "profile", None):
        from .profile_store import ProfileStore
        profile = ProfileStore().load(args.profile)
        for key, value in profile.items():
            if key == "name":
                continue
            config[CONFIG_ALIASES.get(key, key)] = value

    for key in DEFAULT_CONFIG:
        cli_value = getattr(args, key, None)
        if cli_value is not None:
            config[key] = cli_value

    return argparse.Namespace(config=args.config, profile=args.profile, **config)
```

주의: 프로파일의 `virtual` 키는 `CONFIG_ALIASES`의 `"virtual": "paper"` 매핑으로 `paper`에 반영된다. `strategy_params`/`safety` 키는 `DEFAULT_CONFIG`에 없으므로 이 단계에서는 무시된다 — MVP에서 프로파일의 해당 값은 에이전트 `switch_profile` 경로로 적용되며, CLI 부팅 시에는 5개 기본 키(exchange/currency/budget/virtual/term/strategy)만 반영한다. 이 제약을 `--profile` help 문구에 명시하지 않아도 되지만 코드 주석으로 남긴다.

- `main()`의 mode 0 분기에서 Controller에 strategy 전달:

```python
    if args.mode == 0:
        controller = Controller(
            budget=args.budget,
            interval=args.term,
            currency=args.currency,
            exchange=args.exchange,
            paper=args.paper,
            strategy=args.strategy,
        )
        controller.main()
```

- [ ] **Step 4: Controller strategy 배선 확인**

`Controller`는 Task 11에서 이미 `strategy="BNH"` 파라미터를 받도록 개편되었다. 이 태스크에서는 위 Step 3의 `main()` 수정으로 `--strategy` CLI 값이 Controller까지 전달되는 것만 확인한다 (추가 코드 변경 없음).

- [ ] **Step 5: 통과 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/main_config_test.py tests/unit_tests/ -q` → PASS
Run: `python -m smtm --version` → 버전 출력 확인 (import 회귀 스모크)

```bash
git add smtm/__main__.py smtm/controller/ tests/unit_tests/main_config_test.py
git commit -m "[feat] wire strategy and profile options through CLI and controllers"
```

---

### Task 15: E2E 테스트 재작성 + README 갱신

**Files:**
- Modify: `tests/e2e_tests/e2e_chat_trading_test.py` (전면 재작성), `README.md`, `README-ko-kr.md`
- Test: `tests/e2e_tests/e2e_chat_trading_test.py`

**Interfaces:**
- Consumes: 전체 스택 — `SystemOperator`, `TradingOperator`, `StrategyFactory`, `ProfileStore`, `FakeLlmClient`/`FakeDataProvider`(기존 e2e fake)

- [ ] **Step 1: E2E 테스트 재작성**

기존 `tests/e2e_tests/e2e_chat_trading_test.py`는 "채팅→execute_trade" 시나리오라 아키텍처와 맞지 않는다. 전면 교체:

```python
"""
E2E 테스트 — 2계층 아키텍처

시나리오: 채팅(에이전트 Tool use) → 전략 선택 → 매매 시작 → 틱 수행 → 결과 검증
외부 API 없이 FakeLlmClient / FakeDataProvider로 전 구간 검증.
"""
import tempfile
import time
import unittest

from smtm import ProfileStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmResponse, ToolCall

from .fake_llm_client import FakeLlmClient, FakeDataProvider


def make_operator(strategy="BNH", profile_store=None, responses=None,
                  budget=500000, safety=None):
    llm = FakeLlmClient(responses)
    operator = SystemOperator(llm, {
        "exchange": "UPB", "currency": "BTC", "budget": budget,
        "interval": 60, "virtual": True, "strategy": strategy,
        "safety": safety or {},
    }, profile_store=profile_store)
    operator.setup()
    # 실제 네트워크 대신 Fake 데이터 주입
    operator.data_provider = FakeDataProvider()
    operator.trading_operator.data_provider = operator.data_provider
    return operator, llm


def tick(operator):
    """타이머를 기다리지 않고 틱 1회 직접 수행"""
    operator.trading_operator._execute_trading(None)


class StrategyTradingE2ETest(unittest.TestCase):
    def test_chat_select_strategy_start_tick_buy(self):
        """채팅으로 전략 선택+시작 → 틱 → BnH 매수 체결"""
        responses = [
            # turn 1: 에이전트가 select_strategy 호출
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="select_strategy",
                         arguments={"code": "BNH"})]),
            LlmResponse(text="BNH 전략을 선택했습니다"),
            # turn 2: 에이전트가 start_trading 호출
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t2", name="start_trading", arguments={})]),
            LlmResponse(text="자동 매매를 시작했습니다"),
        ]
        operator, _ = make_operator(strategy=None, responses=responses)
        self.addCleanup(operator.stop_trading)

        reply = operator.chat("BNH 전략으로 설정해줘")
        self.assertIn("BNH", reply)
        reply = operator.chat("매매 시작해줘")
        self.assertEqual(operator.trading_operator.state, "running")

        # start()가 worker에 첫 틱을 즉시 post하므로 수동 tick() 대신
        # 첫 틱의 체결을 폴링으로 기다린다 (interval=60이라 두 번째 틱은 없음)
        trader = operator.trader
        deadline = time.time() + 5
        while time.time() < deadline and len(trader.order_history) == 0:
            time.sleep(0.05)
        # BnH: 예산 1/5 매수 (FakeDataProvider 종가 50000 주입 체결)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["type"], "buy")
        self.assertEqual(trader.order_history[0]["price"], 50000)
        self.assertLess(trader.balance, 500000)

    def test_algorithmic_tick_makes_zero_llm_calls(self):
        """알고리즘 전략 틱은 LLM을 호출하지 않는다"""
        operator, llm = make_operator(strategy="BNH")
        self.addCleanup(operator.stop_trading)
        operator.trading_operator.state = "running"
        calls_before = len(llm.call_log)
        tick(operator)
        self.assertEqual(len(llm.call_log), calls_before)

    def test_llm_strategy_tick_uses_forced_decision(self):
        """LLM 전략 틱: 강제 submit_decision 1회 호출로 매수"""
        operator, llm = make_operator(strategy="LLM")
        self.addCleanup(operator.stop_trading)
        llm.add_response(LlmResponse(text="", stop_reason="tool_use", tool_calls=[
            ToolCall(id="d1", name="submit_decision", arguments={
                "action": "buy", "price": 50000, "amount": 0.5,
                "confidence": 0.8, "reason": "테스트 매수"})]))
        operator.trading_operator.state = "running"
        tick(operator)
        trader = operator.trader
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["type"], "buy")
        # 강제 tool use 확인
        self.assertEqual(llm.call_log[-1]["tool_choice"],
                         {"type": "tool", "name": "submit_decision"})

    def test_safety_guard_blocks_oversized_trade(self):
        """SafetyGuard가 한도 초과 주문을 차단하고 이벤트를 기록"""
        operator, _ = make_operator(strategy="BNH",
                                    safety={"max_trade_amount": 1000})
        self.addCleanup(operator.stop_trading)
        operator.trading_operator.state = "running"
        tick(operator)
        self.assertEqual(len(operator.trader.order_history), 0)
        self.assertEqual(len(operator.system_monitor.safety_event_log), 1)


class ProfileE2ETest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(dir_path=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_chat_create_and_switch_profile(self):
        responses = [
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="create_profile", arguments={
                    "name": "rsi-virtual", "strategy": "RSI",
                    "budget": 200000, "virtual": True})]),
            LlmResponse(text="프로파일을 생성했습니다"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t2", name="switch_profile",
                         arguments={"name": "rsi-virtual"})]),
            LlmResponse(text="프로파일로 전환했습니다"),
        ]
        operator, _ = make_operator(profile_store=self.store,
                                    responses=responses)
        self.addCleanup(operator.stop_trading)

        operator.chat("RSI 전략으로 가상매매 프로파일 만들어줘")
        self.assertEqual(len(self.store.list_profiles()), 1)

        operator.chat("그 프로파일로 전환해줘")
        self.assertEqual(operator.strategy_code, "RSI")
        self.assertEqual(operator.budget, 200000)


class MonitoringE2ETest(unittest.TestCase):
    def test_tick_activity_is_logged(self):
        operator, _ = make_operator(strategy="BNH")
        self.addCleanup(operator.stop_trading)
        operator.trading_operator.state = "running"
        tick(operator)
        monitor = operator.system_monitor
        self.assertGreaterEqual(len(monitor.market_data_log), 1)
        self.assertGreaterEqual(len(monitor.trade_request_log), 1)
        self.assertGreaterEqual(len(monitor.trade_result_log), 1)
```

주의: `make_operator(strategy=None, ...)`일 때 SystemOperator는 기본 전략 BNH로 폴백한다(Task 11). `select_strategy` Tool 호출은 running이 아니므로 성공한다.

- [ ] **Step 2: 통과 확인**

Run: `python -m pytest tests/e2e_tests/ -q`
Expected: PASS

- [ ] **Step 3: README 갱신**

`README.md`와 `README-ko-kr.md`의 사용법 섹션에 전략/프로파일 옵션 추가 (기존 예시 근처):

```markdown
# Run with an algorithmic strategy (no LLM call in the trading loop)
python -m smtm --mode 0 --strategy RSI --virtual --budget 500000

# Run with the LLM decision strategy
python -m smtm --mode 0 --strategy LLM --virtual

# Run with a saved account profile (config/profiles/<name>.json)
python -m smtm --mode 0 --profile my-btc-virtual
```

한국어 README에는 동일 내용을 한국어 설명으로 추가.

- [ ] **Step 4: 전체 테스트 최종 확인 후 커밋**

Run: `python -m pytest tests/unit_tests/ tests/e2e_tests/ -q`
Expected: 전체 PASS

```bash
git add tests/e2e_tests/ README.md README-ko-kr.md
git commit -m "[test] rewrite E2E tests for two-layer architecture and update READMEs"
```

---

## 완료 기준 (Definition of Done)

1. `python -m pytest tests/unit_tests/ tests/e2e_tests/ -q` 전체 통과
2. `python -m smtm --version`, `python -m smtm --mode 0 --strategy BNH --virtual` 스모크 부팅(SMTM_LLM_API_KEY 필요) 정상
3. 알고리즘 전략 틱에서 LLM 호출 0회 (E2E `test_algorithmic_tick_makes_zero_llm_calls`)
4. 에이전트에 `execute_trade` Tool 부재 (unit `test_no_trade_tool_registered`)
5. 스펙(`2026-07-03-two-layer-llm-strategy-design.md`)의 In-Scope 8항목 전부 태스크로 커버:
   - Strategy ABC 복원(T1) / 알고리즘 3종(T1-3) / StrategyLlm(T9) / TradingOperator(T7) / Analyzer(T6) / SystemOperator 리팩터(T11) / 지휘+프로파일 Tool(T12-13) / ProfileStore(T10)
