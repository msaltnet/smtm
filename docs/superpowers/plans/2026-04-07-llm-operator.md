# LLM Operator 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** smtm에 LLM 기반 자율 트레이딩 에이전트(LlmOperator)를 추가한다.

**Architecture:** LlmOperator는 기존 Operator+Strategy를 통합한 LLM 에이전트로, 단일 chat() 인터페이스를 제공한다. Trader/Analyzer/DataProvider는 Tool로 래핑되어 LLM이 자율 호출한다. SafetyGuard가 Tool 레벨에서 거래를 검증하고, SystemMonitor가 모든 활동을 독립적으로 로깅한다.

**Tech Stack:** Python 3.9+, anthropic SDK, openai SDK (선택), pytest, unittest.mock

**Spec:** `docs/superpowers/specs/2026-04-06-llm-operator-design.md`

---

## 파일 구조

```
smtm/
├── llm/                          # 신규 패키지
│   ├── __init__.py
│   ├── llm_client.py             # LlmClient ABC + LlmResponse, ToolCall
│   ├── claude_llm_client.py      # Claude API 구현체
│   ├── tool.py                   # Tool ABC + ToolResult
│   ├── tool_router.py            # ToolRouter
│   ├── safety_guard.py           # SafetyGuard
│   ├── system_monitor.py         # SystemMonitor
│   ├── llm_operator.py           # LlmOperator
│   └── tools/                    # Tool 구현체 패키지
│       ├── __init__.py
│       ├── market_data_tool.py   # DataProvider 래핑
│       ├── trade_tool.py         # Trader 래핑
│       ├── portfolio_tool.py     # Trader.get_account_info 래핑
│       ├── performance_tool.py   # Analyzer 분석 기능 래핑
│       └── trade_history_tool.py # SystemMonitor 거래 기록 조회
├── strategies/                   # 전략 지식 문서
│   ├── sma_crossover.md
│   ├── rsi_strategy.md
│   └── buy_and_hold.md
tests/unit_tests/
├── llm_client_test.py
├── claude_llm_client_test.py
├── tool_router_test.py
├── safety_guard_test.py
├── system_monitor_test.py
├── llm_operator_test.py
├── market_data_tool_test.py
├── trade_tool_test.py
├── portfolio_tool_test.py
├── performance_tool_test.py
└── trade_history_tool_test.py
```

---

## Task 1: LlmClient ABC + 데이터 클래스

**Files:**
- Create: `smtm/llm/__init__.py`
- Create: `smtm/llm/llm_client.py`
- Test: `tests/unit_tests/llm_client_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/llm_client_test.py
import unittest
from unittest.mock import *
from smtm.llm.llm_client import LlmClient, LlmResponse, ToolCall


class LlmResponseTests(unittest.TestCase):
    def test_LlmResponse_should_store_attributes(self):
        tool_call = ToolCall(id="tc_1", name="get_market_data", arguments={"currency": "BTC"})
        response = LlmResponse(
            text="BTC 매수를 추천합니다",
            tool_calls=[tool_call],
            stop_reason="end_turn",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        self.assertEqual(response.text, "BTC 매수를 추천합니다")
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "get_market_data")
        self.assertEqual(response.stop_reason, "end_turn")
        self.assertEqual(response.usage["input_tokens"], 100)

    def test_ToolCall_should_store_attributes(self):
        tc = ToolCall(id="tc_1", name="execute_trade", arguments={"action": "buy"})
        self.assertEqual(tc.id, "tc_1")
        self.assertEqual(tc.name, "execute_trade")
        self.assertEqual(tc.arguments["action"], "buy")

    def test_LlmResponse_has_tool_calls_returns_true_when_tool_calls_exist(self):
        tc = ToolCall(id="tc_1", name="test", arguments={})
        response = LlmResponse(text="", tool_calls=[tc], stop_reason="tool_use", usage={})
        self.assertTrue(response.has_tool_calls)

    def test_LlmResponse_has_tool_calls_returns_false_when_empty(self):
        response = LlmResponse(text="hello", tool_calls=[], stop_reason="end_turn", usage={})
        self.assertFalse(response.has_tool_calls)

    def test_LlmClient_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            LlmClient()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/llm_client_test.py -v`
Expected: FAIL (모듈 import 에러)

- [ ] **Step 3: 구현**

```python
# smtm/llm/__init__.py
# (empty)

# smtm/llm/llm_client.py
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolCall:
    """Tool 호출 정보"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LlmResponse:
    """LLM 응답 정규화 객체"""
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: Dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LlmClient(metaclass=ABCMeta):
    """LLM 벤더 추상화 클라이언트"""

    @abstractmethod
    def create_message(
        self,
        system_prompt: str,
        messages: list,
        tools: list,
    ) -> LlmResponse:
        """LLM에 메시지를 전송하고 응답을 받는다"""
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/llm_client_test.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/__init__.py smtm/llm/llm_client.py tests/unit_tests/llm_client_test.py
git commit -m "feat: add LlmClient ABC with LlmResponse and ToolCall data classes"
```

---

## Task 2: ClaudeLlmClient 구현

**Files:**
- Create: `smtm/llm/claude_llm_client.py`
- Test: `tests/unit_tests/claude_llm_client_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/claude_llm_client_test.py
import unittest
from unittest.mock import *
from smtm.llm.claude_llm_client import ClaudeLlmClient
from smtm.llm.llm_client import LlmResponse, ToolCall


class ClaudeLlmClientTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("smtm.llm.claude_llm_client.anthropic")
        self.mock_anthropic = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_anthropic.Anthropic.return_value = self.mock_client

    def tearDown(self):
        self.patcher.stop()

    def test_create_message_returns_LlmResponse_with_text(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="분석 결과입니다")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        response = client.create_message(
            system_prompt="You are a trader",
            messages=[{"role": "user", "content": "분석해줘"}],
            tools=[],
        )

        self.assertIsInstance(response, LlmResponse)
        self.assertEqual(response.text, "분석 결과입니다")
        self.assertEqual(response.stop_reason, "end_turn")
        self.assertFalse(response.has_tool_calls)

    def test_create_message_returns_LlmResponse_with_tool_calls(self):
        mock_tool_use = MagicMock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "toolu_123"
        mock_tool_use.name = "execute_trade"
        mock_tool_use.input = {"action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_use]
        mock_response.stop_reason = "tool_use"
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 30
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        response = client.create_message(
            system_prompt="You are a trader",
            messages=[{"role": "user", "content": "BTC 매수해"}],
            tools=[{"name": "execute_trade", "description": "trade", "input_schema": {}}],
        )

        self.assertTrue(response.has_tool_calls)
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "execute_trade")
        self.assertEqual(response.tool_calls[0].arguments["action"], "buy")

    def test_create_message_passes_correct_params_to_api(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="ok")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        tools = [{"name": "t1", "description": "d1", "input_schema": {"type": "object"}}]
        client.create_message(
            system_prompt="system",
            messages=[{"role": "user", "content": "hi"}],
            tools=tools,
        )

        self.mock_client.messages.create.assert_called_once()
        call_kwargs = self.mock_client.messages.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "claude-sonnet-4-20250514")
        self.assertEqual(call_kwargs["system"], "system")
        self.assertEqual(call_kwargs["messages"], [{"role": "user", "content": "hi"}])

    def test_create_message_handles_mixed_content(self):
        mock_text = MagicMock(type="text", text="먼저 시장을 확인하겠습니다")
        mock_tool = MagicMock()
        mock_tool.type = "tool_use"
        mock_tool.id = "toolu_456"
        mock_tool.name = "get_market_data"
        mock_tool.input = {"currency": "BTC"}

        mock_response = MagicMock()
        mock_response.content = [mock_text, mock_tool]
        mock_response.stop_reason = "tool_use"
        mock_response.usage.input_tokens = 150
        mock_response.usage.output_tokens = 40
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        response = client.create_message("sys", [{"role": "user", "content": "hi"}], [])

        self.assertEqual(response.text, "먼저 시장을 확인하겠습니다")
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "get_market_data")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/claude_llm_client_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/claude_llm_client.py
import anthropic
from .llm_client import LlmClient, LlmResponse, ToolCall
from ..log_manager import LogManager


class ClaudeLlmClient(LlmClient):
    """Anthropic Claude API 클라이언트"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", max_tokens: int = 4096):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def create_message(self, system_prompt, messages, tools):
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self.client.messages.create(**kwargs)

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )

        return LlmResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/claude_llm_client_test.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/claude_llm_client.py tests/unit_tests/claude_llm_client_test.py
git commit -m "feat: add ClaudeLlmClient implementing LlmClient for Anthropic API"
```

---

## Task 3: Tool ABC + ToolResult

**Files:**
- Create: `smtm/llm/tool.py`
- Create: `smtm/llm/tools/__init__.py`
- Test: `tests/unit_tests/tool_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/tool_test.py
import unittest
from smtm.llm.tool import Tool, ToolResult


class ToolResultTests(unittest.TestCase):
    def test_success_result_stores_data(self):
        result = ToolResult(success=True, data={"balance": 50000})
        self.assertTrue(result.success)
        self.assertEqual(result.data["balance"], 50000)
        self.assertIsNone(result.error)

    def test_failure_result_stores_error(self):
        result = ToolResult(success=False, data=None, error="거래 실패")
        self.assertFalse(result.success)
        self.assertIsNone(result.data)
        self.assertEqual(result.error, "거래 실패")

    def test_to_dict_returns_data_on_success(self):
        result = ToolResult(success=True, data={"price": 50000})
        d = result.to_dict()
        self.assertEqual(d["price"], 50000)

    def test_to_dict_returns_error_on_failure(self):
        result = ToolResult(success=False, data=None, error="에러 발생")
        d = result.to_dict()
        self.assertEqual(d["error"], "에러 발생")

    def test_Tool_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            Tool()
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/tool_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/tool.py
from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolResult:
    """Tool 실행 결과"""
    success: bool
    data: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        if self.success:
            return self.data if isinstance(self.data, dict) else {"result": self.data}
        return {"error": self.error}


class Tool(metaclass=ABCMeta):
    """Tool 기본 추상 클래스"""

    name: str = ""
    description: str = ""
    input_schema: dict = {}

    @abstractmethod
    def execute(self, arguments: dict) -> ToolResult:
        """Tool 실행"""

    def get_schema(self) -> dict:
        """LLM에 전달할 Tool 스키마 반환"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
```

```python
# smtm/llm/tools/__init__.py
# (empty)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/tool_test.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/tool.py smtm/llm/tools/__init__.py tests/unit_tests/tool_test.py
git commit -m "feat: add Tool ABC and ToolResult data class"
```

---

## Task 4: SafetyGuard

**Files:**
- Create: `smtm/llm/safety_guard.py`
- Test: `tests/unit_tests/safety_guard_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/safety_guard_test.py
import unittest
from unittest.mock import *
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig, SafetyResult
from smtm.llm.llm_client import ToolCall


class SafetyGuardTests(unittest.TestCase):
    def setUp(self):
        self.config = SafetyConfig(
            max_trade_amount=100000,
            max_daily_trades=10,
            max_loss_ratio=-0.20,
            initial_budget=500000,
        )
        self.guard = SafetyGuard(self.config)

    def test_check_allows_valid_trade(self):
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 50000, "amount": 1.0},
        )
        result = self.guard.check(tool_call)
        self.assertTrue(result.allowed)

    def test_check_blocks_trade_exceeding_max_amount(self):
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 200000, "amount": 1.0},
        )
        result = self.guard.check(tool_call)
        self.assertFalse(result.allowed)
        self.assertIn("최대 거래금액", result.reason)

    def test_check_blocks_trade_exceeding_daily_limit(self):
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 10000, "amount": 0.1},
        )
        for _ in range(10):
            self.guard.record_trade({"type": "buy", "price": 10000, "amount": 0.1})

        result = self.guard.check(tool_call)
        self.assertFalse(result.allowed)
        self.assertIn("일일 거래횟수", result.reason)

    def test_check_blocks_trade_when_loss_exceeds_limit(self):
        self.guard.current_value = 350000  # -30% loss from 500000
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 10000, "amount": 0.1},
        )
        result = self.guard.check(tool_call)
        self.assertFalse(result.allowed)
        self.assertIn("손실 한도", result.reason)

    def test_check_allows_non_trade_tools(self):
        tool_call = ToolCall(
            id="tc_1", name="get_market_data",
            arguments={"currency": "BTC"},
        )
        result = self.guard.check(tool_call)
        self.assertTrue(result.allowed)

    def test_record_trade_increments_daily_count(self):
        self.assertEqual(self.guard.daily_trade_count, 0)
        self.guard.record_trade({"type": "buy", "price": 10000, "amount": 0.1})
        self.assertEqual(self.guard.daily_trade_count, 1)

    def test_get_status_returns_current_state(self):
        status = self.guard.get_status()
        self.assertEqual(status["daily_trades"], 0)
        self.assertEqual(status["daily_limit"], 10)
        self.assertTrue(status["trading_allowed"])

    def test_update_portfolio_value_updates_current_value(self):
        self.guard.update_portfolio_value(450000)
        self.assertEqual(self.guard.current_value, 450000)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/safety_guard_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/safety_guard.py
from dataclasses import dataclass
from datetime import datetime, date
from typing import Optional
from ..log_manager import LogManager


@dataclass
class SafetyConfig:
    """안전장치 설정"""
    max_trade_amount: float = 100000
    max_daily_trades: int = 20
    max_loss_ratio: float = -0.20
    initial_budget: float = 500000


@dataclass
class SafetyResult:
    """안전장치 검증 결과"""
    allowed: bool
    reason: Optional[str] = None


class SafetyGuard:
    """규칙 기반 안전장치 — Tool 실행 전 검증, LLM 우회 불가"""

    TRADE_TOOLS = ("execute_trade",)

    def __init__(self, config: SafetyConfig):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.config = config
        self.daily_trade_count = 0
        self.daily_date = date.today()
        self.current_value = config.initial_budget

    def check(self, tool_call) -> SafetyResult:
        """Tool 호출 사전 검증. 거래 Tool만 검증, 나머지는 통과."""
        if tool_call.name not in self.TRADE_TOOLS:
            return SafetyResult(allowed=True)

        self._reset_daily_if_needed()

        # 1회 최대 거래금액 검증
        trade_amount = tool_call.arguments.get("price", 0) * tool_call.arguments.get("amount", 0)
        if trade_amount > self.config.max_trade_amount:
            reason = f"1회 최대 거래금액 초과 ({trade_amount:,.0f} > {self.config.max_trade_amount:,.0f})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        # 일일 거래횟수 제한
        if self.daily_trade_count >= self.config.max_daily_trades:
            reason = f"일일 거래횟수 초과 ({self.daily_trade_count}/{self.config.max_daily_trades})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        # 누적 손실 한도
        loss_ratio = (self.current_value - self.config.initial_budget) / self.config.initial_budget
        if loss_ratio < self.config.max_loss_ratio:
            reason = f"손실 한도 초과 ({loss_ratio:.1%} < {self.config.max_loss_ratio:.1%})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        return SafetyResult(allowed=True)

    def record_trade(self, result: dict):
        """거래 완료 후 카운터 업데이트"""
        self._reset_daily_if_needed()
        self.daily_trade_count += 1

    def update_portfolio_value(self, value: float):
        """포트폴리오 가치 업데이트"""
        self.current_value = value

    def get_status(self) -> dict:
        self._reset_daily_if_needed()
        loss_ratio = (self.current_value - self.config.initial_budget) / self.config.initial_budget
        return {
            "daily_trades": self.daily_trade_count,
            "daily_limit": self.config.max_daily_trades,
            "current_loss_ratio": round(loss_ratio, 4),
            "max_loss_ratio": self.config.max_loss_ratio,
            "trading_allowed": self.check(
                type("FakeCall", (), {"name": "execute_trade", "arguments": {"price": 1, "amount": 1}})()
            ).allowed,
        }

    def _reset_daily_if_needed(self):
        today = date.today()
        if self.daily_date != today:
            self.daily_trade_count = 0
            self.daily_date = today
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/safety_guard_test.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/safety_guard.py tests/unit_tests/safety_guard_test.py
git commit -m "feat: add SafetyGuard with trade amount, daily limit, and loss ratio checks"
```

---

## Task 5: SystemMonitor

**Files:**
- Create: `smtm/llm/system_monitor.py`
- Test: `tests/unit_tests/system_monitor_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/system_monitor_test.py
import unittest
import json
import os
import tempfile
from smtm.llm.system_monitor import SystemMonitor


class SystemMonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.monitor = SystemMonitor(storage_path=self.temp_dir)

    def test_log_market_data_stores_data(self):
        data = [{"type": "primary_candle", "market": "BTC", "closing_price": 50000}]
        self.monitor.log_market_data(data)
        self.assertEqual(len(self.monitor.market_data_log), 1)

    def test_log_trade_request_stores_request(self):
        request = {"id": "req_1", "type": "buy", "price": 50000, "amount": 0.01}
        self.monitor.log_trade_request(request)
        self.assertEqual(len(self.monitor.trade_request_log), 1)

    def test_log_trade_result_stores_result(self):
        result = {"type": "buy", "price": 50000, "amount": 0.01, "state": "done"}
        self.monitor.log_trade_result(result)
        self.assertEqual(len(self.monitor.trade_result_log), 1)

    def test_log_tool_call_stores_call_and_result(self):
        self.monitor.log_tool_call("execute_trade", {"action": "buy"}, {"success": True})
        self.assertEqual(len(self.monitor.tool_call_log), 1)
        self.assertEqual(self.monitor.tool_call_log[0]["tool_name"], "execute_trade")

    def test_log_llm_interaction_stores_usage(self):
        self.monitor.log_llm_interaction(
            request={"messages": [{"role": "user", "content": "hi"}]},
            response_text="hello",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        self.assertEqual(len(self.monitor.llm_interaction_log), 1)

    def test_log_safety_event_stores_event(self):
        self.monitor.log_safety_event({"type": "blocked", "reason": "손실 한도 초과"})
        self.assertEqual(len(self.monitor.safety_event_log), 1)

    def test_take_snapshot_stores_portfolio(self):
        portfolio = {"balance": 400000, "asset": {"BTC": (50000, 0.01)}}
        self.monitor.take_snapshot(portfolio)
        self.assertEqual(len(self.monitor.snapshots), 1)

    def test_get_trade_log_returns_all_results(self):
        self.monitor.log_trade_result({"type": "buy", "price": 50000})
        self.monitor.log_trade_result({"type": "sell", "price": 51000})
        log = self.monitor.get_trade_log()
        self.assertEqual(len(log), 2)

    def test_get_llm_usage_returns_token_totals(self):
        self.monitor.log_llm_interaction({}, "r1", {"input_tokens": 100, "output_tokens": 50})
        self.monitor.log_llm_interaction({}, "r2", {"input_tokens": 200, "output_tokens": 80})
        usage = self.monitor.get_llm_usage()
        self.assertEqual(usage["total_input_tokens"], 300)
        self.assertEqual(usage["total_output_tokens"], 130)
        self.assertEqual(usage["call_count"], 2)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/system_monitor_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/system_monitor.py
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..log_manager import LogManager


class SystemMonitor:
    """독립 시스템 모니터 — LLM 바깥에서 모든 활동을 기록"""

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self, storage_path: str = "output/monitor/"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.storage_path = storage_path
        self.market_data_log: List[dict] = []
        self.trade_request_log: List[dict] = []
        self.trade_result_log: List[dict] = []
        self.tool_call_log: List[dict] = []
        self.llm_interaction_log: List[dict] = []
        self.safety_event_log: List[dict] = []
        self.snapshots: List[dict] = []

    def _timestamp(self) -> str:
        return datetime.now().strftime(self.ISO_DATEFORMAT)

    def log_market_data(self, data: list):
        self.market_data_log.append({
            "timestamp": self._timestamp(),
            "data": data,
        })

    def log_trade_request(self, request: dict):
        self.trade_request_log.append({
            "timestamp": self._timestamp(),
            "request": request,
        })

    def log_trade_result(self, result: dict):
        self.trade_result_log.append({
            "timestamp": self._timestamp(),
            "result": result,
        })

    def log_tool_call(self, tool_name: str, arguments: dict, result: dict):
        self.tool_call_log.append({
            "timestamp": self._timestamp(),
            "tool_name": tool_name,
            "arguments": arguments,
            "result": result,
        })

    def log_llm_interaction(self, request: dict, response_text: str, usage: dict):
        self.llm_interaction_log.append({
            "timestamp": self._timestamp(),
            "request": request,
            "response_text": response_text,
            "usage": usage,
        })

    def log_safety_event(self, event: dict):
        self.safety_event_log.append({
            "timestamp": self._timestamp(),
            "event": event,
        })

    def take_snapshot(self, portfolio: dict):
        self.snapshots.append({
            "timestamp": self._timestamp(),
            "portfolio": portfolio,
        })

    def get_trade_log(self, start_time=None, end_time=None) -> list:
        return self.trade_result_log

    def get_snapshots(self, start_time=None, end_time=None) -> list:
        return self.snapshots

    def get_llm_usage(self) -> dict:
        total_input = sum(
            log["usage"].get("input_tokens", 0) for log in self.llm_interaction_log
        )
        total_output = sum(
            log["usage"].get("output_tokens", 0) for log in self.llm_interaction_log
        )
        return {
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
            "call_count": len(self.llm_interaction_log),
        }
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/system_monitor_test.py -v`
Expected: PASS (9 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/system_monitor.py tests/unit_tests/system_monitor_test.py
git commit -m "feat: add SystemMonitor for independent activity logging"
```

---

## Task 6: ToolRouter

**Files:**
- Create: `smtm/llm/tool_router.py`
- Test: `tests/unit_tests/tool_router_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/tool_router_test.py
import unittest
from unittest.mock import *
from smtm.llm.tool_router import ToolRouter
from smtm.llm.tool import Tool, ToolResult
from smtm.llm.llm_client import ToolCall
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig, SafetyResult
from smtm.llm.system_monitor import SystemMonitor


class DummyTool(Tool):
    name = "dummy_tool"
    description = "A dummy tool"
    input_schema = {"type": "object", "properties": {"x": {"type": "integer"}}}

    def execute(self, arguments):
        return ToolResult(success=True, data={"x": arguments["x"]})


class ToolRouterTests(unittest.TestCase):
    def setUp(self):
        config = SafetyConfig(initial_budget=500000)
        self.safety_guard = SafetyGuard(config)
        self.monitor = SystemMonitor()
        self.router = ToolRouter(self.safety_guard, self.monitor)

    def test_register_adds_tool(self):
        tool = DummyTool()
        self.router.register(tool)
        self.assertIn("dummy_tool", self.router.tools)

    def test_execute_calls_tool_and_returns_result(self):
        self.router.register(DummyTool())
        tool_call = ToolCall(id="tc_1", name="dummy_tool", arguments={"x": 42})
        result = self.router.execute(tool_call)
        self.assertTrue(result.success)
        self.assertEqual(result.data["x"], 42)

    def test_execute_returns_error_for_unknown_tool(self):
        tool_call = ToolCall(id="tc_1", name="unknown", arguments={})
        result = self.router.execute(tool_call)
        self.assertFalse(result.success)
        self.assertIn("unknown", result.error)

    def test_execute_checks_safety_guard_for_trade_tools(self):
        trade_tool = MagicMock(spec=Tool)
        trade_tool.name = "execute_trade"
        trade_tool.execute.return_value = ToolResult(success=True, data={})
        self.router.register(trade_tool)

        self.safety_guard.check = MagicMock(return_value=SafetyResult(allowed=False, reason="차단됨"))
        tool_call = ToolCall(id="tc_1", name="execute_trade", arguments={"price": 999999, "amount": 1})
        result = self.router.execute(tool_call)
        self.assertFalse(result.success)
        self.assertIn("차단됨", result.error)
        trade_tool.execute.assert_not_called()

    def test_execute_logs_to_system_monitor(self):
        self.router.register(DummyTool())
        tool_call = ToolCall(id="tc_1", name="dummy_tool", arguments={"x": 1})
        self.router.execute(tool_call)
        self.assertEqual(len(self.monitor.tool_call_log), 1)

    def test_get_tool_schemas_returns_all_schemas(self):
        self.router.register(DummyTool())
        schemas = self.router.get_tool_schemas()
        self.assertEqual(len(schemas), 1)
        self.assertEqual(schemas[0]["name"], "dummy_tool")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/tool_router_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/tool_router.py
from typing import Dict
from ..log_manager import LogManager
from .tool import Tool, ToolResult
from .llm_client import ToolCall
from .safety_guard import SafetyGuard
from .system_monitor import SystemMonitor


class ToolRouter:
    """Tool 등록, 라우팅, 실행"""

    def __init__(self, safety_guard: SafetyGuard, system_monitor: SystemMonitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.tools: Dict[str, Tool] = {}
        self.safety_guard = safety_guard
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

        # SafetyGuard 검증
        safety_result = self.safety_guard.check(tool_call)
        if not safety_result.allowed:
            self.system_monitor.log_safety_event({
                "type": "blocked",
                "tool": tool_call.name,
                "reason": safety_result.reason,
            })
            return ToolResult(success=False, error=safety_result.reason)

        # Tool 실행
        tool = self.tools[tool_call.name]
        try:
            result = tool.execute(tool_call.arguments)
        except Exception as e:
            self.logger.error(f"Tool execution failed: {tool_call.name} - {e}")
            result = ToolResult(success=False, error=str(e))

        # SystemMonitor 기록
        self.system_monitor.log_tool_call(
            tool_name=tool_call.name,
            arguments=tool_call.arguments,
            result=result.to_dict(),
        )

        # 거래 성공 시 SafetyGuard 카운터 업데이트
        if tool_call.name == "execute_trade" and result.success:
            self.safety_guard.record_trade(tool_call.arguments)

        return result
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/tool_router_test.py -v`
Expected: PASS (6 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/tool_router.py tests/unit_tests/tool_router_test.py
git commit -m "feat: add ToolRouter with SafetyGuard integration and SystemMonitor logging"
```

---

## Task 7: MarketDataTool (DataProvider 래핑)

**Files:**
- Create: `smtm/llm/tools/market_data_tool.py`
- Test: `tests/unit_tests/market_data_tool_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/market_data_tool_test.py
import unittest
from unittest.mock import *
from smtm.llm.tools.market_data_tool import MarketDataTool


class MarketDataToolTests(unittest.TestCase):
    def test_name_and_schema_are_set(self):
        dp_mock = MagicMock()
        tool = MarketDataTool(dp_mock)
        self.assertEqual(tool.name, "get_market_data")
        self.assertIn("currency", tool.input_schema["properties"])

    def test_execute_returns_data_from_data_provider(self):
        dp_mock = MagicMock()
        dp_mock.get_info.return_value = [
            {"type": "primary_candle", "market": "BTC", "closing_price": 50000}
        ]
        tool = MarketDataTool(dp_mock)
        result = tool.execute({"currency": "BTC"})
        self.assertTrue(result.success)
        self.assertEqual(result.data[0]["closing_price"], 50000)

    def test_execute_returns_error_on_exception(self):
        dp_mock = MagicMock()
        dp_mock.get_info.side_effect = Exception("API error")
        tool = MarketDataTool(dp_mock)
        result = tool.execute({"currency": "BTC"})
        self.assertFalse(result.success)
        self.assertIn("API error", result.error)

    def test_get_schema_returns_valid_schema(self):
        dp_mock = MagicMock()
        tool = MarketDataTool(dp_mock)
        schema = tool.get_schema()
        self.assertEqual(schema["name"], "get_market_data")
        self.assertIn("description", schema)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/market_data_tool_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/tools/market_data_tool.py
from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class MarketDataTool(Tool):
    """시장 데이터 조회 Tool — DataProvider 래핑"""

    name = "get_market_data"
    description = "현재 시장의 OHLCV 캔들 데이터를 조회합니다. 시가, 고가, 저가, 종가, 거래량을 포함합니다."
    input_schema = {
        "type": "object",
        "properties": {
            "currency": {
                "type": "string",
                "enum": ["BTC", "ETH", "DOGE", "XRP"],
                "description": "조회할 암호화폐",
            },
        },
        "required": ["currency"],
    }

    def __init__(self, data_provider):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.data_provider = data_provider

    def execute(self, arguments: dict) -> ToolResult:
        try:
            data = self.data_provider.get_info()
            return ToolResult(success=True, data=data)
        except Exception as e:
            self.logger.error(f"MarketDataTool error: {e}")
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/market_data_tool_test.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/tools/market_data_tool.py tests/unit_tests/market_data_tool_test.py
git commit -m "feat: add MarketDataTool wrapping DataProvider"
```

---

## Task 8: TradeTool (Trader 래핑)

**Files:**
- Create: `smtm/llm/tools/trade_tool.py`
- Test: `tests/unit_tests/trade_tool_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/trade_tool_test.py
import unittest
from unittest.mock import *
from smtm.llm.tools.trade_tool import TradeTool


class TradeToolTests(unittest.TestCase):
    def setUp(self):
        self.trader_mock = MagicMock()
        self.monitor_mock = MagicMock()
        self.tool = TradeTool(self.trader_mock, self.monitor_mock)

    def test_name_and_schema_are_set(self):
        self.assertEqual(self.tool.name, "execute_trade")
        self.assertIn("action", self.tool.input_schema["properties"])
        self.assertIn("currency", self.tool.input_schema["properties"])

    def test_execute_buy_calls_trader_send_request(self):
        def fake_send(request_list, callback):
            callback({
                "request": request_list[0],
                "type": "buy",
                "price": 50000,
                "amount": 0.01,
                "state": "done",
                "msg": "success",
                "balance": 449500,
                "date_time": "2026-04-07T12:00:00",
            })

        self.trader_mock.send_request.side_effect = fake_send
        result = self.tool.execute({
            "action": "buy",
            "currency": "BTC",
            "price": 50000,
            "amount": 0.01,
        })
        self.assertTrue(result.success)
        self.trader_mock.send_request.assert_called_once()

    def test_execute_logs_trade_result_to_monitor(self):
        def fake_send(request_list, callback):
            callback({"state": "done", "type": "buy", "price": 50000, "amount": 0.01})

        self.trader_mock.send_request.side_effect = fake_send
        self.tool.execute({
            "action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01,
        })
        self.monitor_mock.log_trade_request.assert_called_once()
        self.monitor_mock.log_trade_result.assert_called_once()

    def test_execute_returns_error_on_exception(self):
        self.trader_mock.send_request.side_effect = Exception("connection error")
        result = self.tool.execute({
            "action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01,
        })
        self.assertFalse(result.success)
        self.assertIn("connection error", result.error)
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/trade_tool_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/tools/trade_tool.py
import time
import threading
from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class TradeTool(Tool):
    """거래 실행 Tool — Trader 래핑"""

    name = "execute_trade"
    description = "거래소에 매수 또는 매도 주문을 실행합니다"
    input_schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["buy", "sell"],
                "description": "매수(buy) 또는 매도(sell)",
            },
            "currency": {
                "type": "string",
                "enum": ["BTC", "ETH", "DOGE", "XRP"],
                "description": "거래할 암호화폐",
            },
            "price": {
                "type": "number",
                "description": "주문 가격",
            },
            "amount": {
                "type": "number",
                "description": "주문 수량",
            },
        },
        "required": ["action", "currency", "price", "amount"],
    }

    def __init__(self, trader, system_monitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.trader = trader
        self.system_monitor = system_monitor

    def execute(self, arguments: dict) -> ToolResult:
        request = {
            "id": str(time.time()),
            "type": arguments["action"],
            "price": arguments["price"],
            "amount": arguments["amount"],
            "date_time": time.strftime("%Y-%m-%dT%H:%M:%S"),
        }

        self.system_monitor.log_trade_request(request)

        result_holder = {}
        event = threading.Event()

        def callback(result):
            result_holder["result"] = result
            self.system_monitor.log_trade_result(result)
            event.set()

        try:
            self.trader.send_request([request], callback)
            event.wait(timeout=30)
            if "result" in result_holder:
                return ToolResult(success=True, data=result_holder["result"])
            return ToolResult(success=False, error="거래 요청 타임아웃")
        except Exception as e:
            self.logger.error(f"TradeTool error: {e}")
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/trade_tool_test.py -v`
Expected: PASS (4 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/tools/trade_tool.py tests/unit_tests/trade_tool_test.py
git commit -m "feat: add TradeTool wrapping Trader with SystemMonitor logging"
```

---

## Task 9: PortfolioTool + TradeHistoryTool + PerformanceTool

**Files:**
- Create: `smtm/llm/tools/portfolio_tool.py`
- Create: `smtm/llm/tools/trade_history_tool.py`
- Create: `smtm/llm/tools/performance_tool.py`
- Test: `tests/unit_tests/portfolio_tool_test.py`
- Test: `tests/unit_tests/trade_history_tool_test.py`
- Test: `tests/unit_tests/performance_tool_test.py`

- [ ] **Step 1: PortfolioTool 테스트 작성**

```python
# tests/unit_tests/portfolio_tool_test.py
import unittest
from unittest.mock import *
from smtm.llm.tools.portfolio_tool import PortfolioTool


class PortfolioToolTests(unittest.TestCase):
    def test_execute_returns_account_info(self):
        trader_mock = MagicMock()
        trader_mock.get_account_info.return_value = {
            "balance": 400000,
            "asset": {"KRW-BTC": (50000000, 0.01)},
            "quote": {"KRW-BTC": 51000000},
        }
        tool = PortfolioTool(trader_mock)
        result = tool.execute({})
        self.assertTrue(result.success)
        self.assertEqual(result.data["balance"], 400000)

    def test_execute_returns_error_on_exception(self):
        trader_mock = MagicMock()
        trader_mock.get_account_info.side_effect = Exception("auth error")
        tool = PortfolioTool(trader_mock)
        result = tool.execute({})
        self.assertFalse(result.success)
```

- [ ] **Step 2: TradeHistoryTool 테스트 작성**

```python
# tests/unit_tests/trade_history_tool_test.py
import unittest
from unittest.mock import *
from smtm.llm.tools.trade_history_tool import TradeHistoryTool


class TradeHistoryToolTests(unittest.TestCase):
    def test_execute_returns_trade_log(self):
        monitor_mock = MagicMock()
        monitor_mock.get_trade_log.return_value = [
            {"result": {"type": "buy", "price": 50000}},
            {"result": {"type": "sell", "price": 51000}},
        ]
        tool = TradeHistoryTool(monitor_mock)
        result = tool.execute({"count": 10})
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
```

- [ ] **Step 3: PerformanceTool 테스트 작성**

```python
# tests/unit_tests/performance_tool_test.py
import unittest
from unittest.mock import *
from smtm.llm.tools.performance_tool import PerformanceTool


class PerformanceToolTests(unittest.TestCase):
    def test_execute_returns_performance_summary(self):
        monitor_mock = MagicMock()
        monitor_mock.get_trade_log.return_value = [
            {"result": {"type": "buy", "price": 50000, "amount": 0.01}},
        ]
        monitor_mock.get_snapshots.return_value = [
            {"portfolio": {"balance": 400000}},
        ]
        trader_mock = MagicMock()
        trader_mock.get_account_info.return_value = {
            "balance": 450000,
            "asset": {},
            "quote": {},
        }
        tool = PerformanceTool(monitor_mock, trader_mock, initial_budget=500000)
        result = tool.execute({})
        self.assertTrue(result.success)
        self.assertIn("total_value", result.data)
```

- [ ] **Step 4: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/portfolio_tool_test.py tests/unit_tests/trade_history_tool_test.py tests/unit_tests/performance_tool_test.py -v`
Expected: FAIL

- [ ] **Step 5: PortfolioTool 구현**

```python
# smtm/llm/tools/portfolio_tool.py
from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class PortfolioTool(Tool):
    """포트폴리오 조회 Tool — Trader.get_account_info 래핑"""

    name = "get_portfolio"
    description = "현재 보유 자산, 현금 잔고, 종목별 시세를 조회합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, trader):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.trader = trader

    def execute(self, arguments: dict) -> ToolResult:
        try:
            info = self.trader.get_account_info()
            return ToolResult(success=True, data=info)
        except Exception as e:
            self.logger.error(f"PortfolioTool error: {e}")
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 6: TradeHistoryTool 구현**

```python
# smtm/llm/tools/trade_history_tool.py
from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class TradeHistoryTool(Tool):
    """거래 내역 조회 Tool — SystemMonitor 거래 기록 조회"""

    name = "get_trade_history"
    description = "과거 거래 내역(매수/매도)을 조회합니다"
    input_schema = {
        "type": "object",
        "properties": {
            "count": {
                "type": "integer",
                "description": "조회할 최근 거래 수 (기본 20)",
                "default": 20,
            },
        },
    }

    def __init__(self, system_monitor):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.system_monitor = system_monitor

    def execute(self, arguments: dict) -> ToolResult:
        try:
            count = arguments.get("count", 20)
            log = self.system_monitor.get_trade_log()
            return ToolResult(success=True, data=log[-count:])
        except Exception as e:
            self.logger.error(f"TradeHistoryTool error: {e}")
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 7: PerformanceTool 구현**

```python
# smtm/llm/tools/performance_tool.py
from ..tool import Tool, ToolResult
from ...log_manager import LogManager


class PerformanceTool(Tool):
    """수익률 분석 Tool"""

    name = "get_performance"
    description = "현재까지의 수익률, 거래 통계, 성과 분석을 조회합니다"
    input_schema = {"type": "object", "properties": {}}

    def __init__(self, system_monitor, trader, initial_budget: float):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.system_monitor = system_monitor
        self.trader = trader
        self.initial_budget = initial_budget

    def execute(self, arguments: dict) -> ToolResult:
        try:
            account = self.trader.get_account_info()
            trade_log = self.system_monitor.get_trade_log()

            total_value = account.get("balance", 0)
            for asset_key, asset_info in account.get("asset", {}).items():
                avg_price, amount = asset_info
                quote_price = account.get("quote", {}).get(asset_key, avg_price)
                total_value += quote_price * amount

            return_ratio = (total_value - self.initial_budget) / self.initial_budget if self.initial_budget > 0 else 0

            return ToolResult(success=True, data={
                "initial_budget": self.initial_budget,
                "total_value": total_value,
                "balance": account.get("balance", 0),
                "return_ratio": round(return_ratio, 4),
                "total_trades": len(trade_log),
                "asset": account.get("asset", {}),
                "quote": account.get("quote", {}),
            })
        except Exception as e:
            self.logger.error(f"PerformanceTool error: {e}")
            return ToolResult(success=False, error=str(e))
```

- [ ] **Step 8: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/portfolio_tool_test.py tests/unit_tests/trade_history_tool_test.py tests/unit_tests/performance_tool_test.py -v`
Expected: PASS

- [ ] **Step 9: 커밋**

```bash
git add smtm/llm/tools/portfolio_tool.py smtm/llm/tools/trade_history_tool.py smtm/llm/tools/performance_tool.py tests/unit_tests/portfolio_tool_test.py tests/unit_tests/trade_history_tool_test.py tests/unit_tests/performance_tool_test.py
git commit -m "feat: add PortfolioTool, TradeHistoryTool, and PerformanceTool"
```

---

## Task 10: Strategy Knowledge 문서

**Files:**
- Create: `smtm/strategies/sma_crossover.md`
- Create: `smtm/strategies/rsi_strategy.md`
- Create: `smtm/strategies/buy_and_hold.md`

- [ ] **Step 1: SMA 전략 문서 작성**

```markdown
# SMA 크로스오버 전략

## 개요
단기/중기/장기 이동평균선(Simple Moving Average)의 교차를 기반으로 매매 신호를 생성하는 전략.

## 매수 조건
- 단기 SMA(10)가 중기 SMA(40)를 상향 돌파 (골든크로스)
- 종가가 장기 SMA(60) 위에 위치
- 분할 매수 권장: 전체 예산의 일부씩 매수

## 매도 조건
- 단기 SMA(10)가 중기 SMA(40)를 하향 돌파 (데드크로스)
- 보유 수량 전량 매도

## 파라미터
- SHORT_PERIOD: 10 (단기 이동평균 기간)
- MID_PERIOD: 40 (중기 이동평균 기간)
- LONG_PERIOD: 60 (장기 이동평균 기간)
- STD_K: 25 (표준편차 계수, 변동성 판단)

## 적합한 시장
- 추세가 명확한 상승/하락장에서 효과적
- 횡보장에서는 거짓 신호가 자주 발생하므로 주의

## 주의사항
- 이동평균은 후행 지표이므로 급변 시 대응이 늦음
- 충분한 캔들 데이터(최소 60개)가 축적된 후에 신호 유효
- 거래 수수료(0.05%)를 감안한 수익 계산 필요
```

- [ ] **Step 2: RSI 전략 문서 작성**

```markdown
# RSI 전략

## 개요
RSI(Relative Strength Index, 상대강도지수)를 기반으로 과매수/과매도 구간에서 매매하는 전략.

## 매수 조건
- RSI(14) < 30 (과매도 구간 진입)

## 매도 조건
- RSI(14) > 70 (과매수 구간 진입)

## 파라미터
- RSI_PERIOD: 14 (RSI 계산 기간)
- RSI_LOW: 30 (과매도 기준)
- RSI_HIGH: 70 (과매수 기준)

## 적합한 시장
- 횡보장에서 효과적 (범위 내 반복 거래)
- 강한 추세장에서는 조기 매도 위험

## 주의사항
- 강한 상승 추세에서 RSI가 70 이상에서 오래 머물 수 있음
- 단독 사용보다 다른 지표와 병행 사용 권장
- 최소 15개 이상의 캔들 데이터 필요
```

- [ ] **Step 3: Buy and Hold 전략 문서 작성**

```markdown
# Buy and Hold 전략

## 개요
예산을 분할하여 매수한 후 보유하는 가장 단순한 전략. 벤치마크 비교 용도로 사용.

## 매수 조건
- 잔고가 남아있으면 매수 (단순 분할 매수)

## 매도 조건
- 없음 (보유 유지)

## 파라미터
- 없음

## 적합한 시장
- 장기 상승 추세에서 가장 효과적
- 다른 전략의 성과 비교 기준(벤치마크)으로 사용

## 주의사항
- 하락장에서는 손실이 그대로 반영됨
- 가장 단순하지만 벤치마크로서 중요한 의미를 가짐
```

- [ ] **Step 4: 커밋**

```bash
git add smtm/strategies/
git commit -m "feat: add strategy knowledge documents for LLM reference"
```

---

## Task 11: LlmOperator

**Files:**
- Create: `smtm/llm/llm_operator.py`
- Test: `tests/unit_tests/llm_operator_test.py`

- [ ] **Step 1: 테스트 작성**

```python
# tests/unit_tests/llm_operator_test.py
import unittest
from unittest.mock import *
from smtm.llm.llm_operator import LlmOperator, ContextConfig
from smtm.llm.llm_client import LlmResponse, ToolCall
from smtm.llm.tool import ToolResult
from smtm.llm.safety_guard import SafetyConfig


class LlmOperatorInitTests(unittest.TestCase):
    def test_init_sets_state_to_ready(self):
        llm_client = MagicMock()
        config = {
            "exchange": "UPB",
            "currency": "BTC",
            "budget": 500000,
            "interval": 60,
        }
        op = LlmOperator(llm_client, config)
        self.assertEqual(op.state, "ready")

    def test_init_creates_tool_router_and_safety_guard(self):
        llm_client = MagicMock()
        config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60}
        op = LlmOperator(llm_client, config)
        self.assertIsNotNone(op.tool_router)
        self.assertIsNotNone(op.safety_guard)
        self.assertIsNotNone(op.system_monitor)


class LlmOperatorChatTests(unittest.TestCase):
    def setUp(self):
        self.llm_client = MagicMock()
        self.config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60}
        self.op = LlmOperator(self.llm_client, self.config)

    def test_chat_returns_llm_text_response(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="BTC 시장이 안정적입니다",
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        response = self.op.chat("시장 상황 알려줘")
        self.assertEqual(response, "BTC 시장이 안정적입니다")

    def test_chat_handles_tool_use_loop(self):
        # 첫 호출: tool_use 응답
        tool_response = LlmResponse(
            text="",
            tool_calls=[ToolCall(id="tc_1", name="get_portfolio", arguments={})],
            stop_reason="tool_use",
            usage={"input_tokens": 100, "output_tokens": 30},
        )
        # 두 번째 호출: 최종 텍스트 응답
        final_response = LlmResponse(
            text="현재 잔고는 50만원입니다",
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 150, "output_tokens": 40},
        )
        self.llm_client.create_message.side_effect = [tool_response, final_response]

        # ToolRouter에 get_portfolio 등록
        portfolio_tool = MagicMock()
        portfolio_tool.name = "get_portfolio"
        portfolio_tool.execute.return_value = ToolResult(success=True, data={"balance": 500000})
        self.op.tool_router.register(portfolio_tool)

        response = self.op.chat("잔고 알려줘")
        self.assertEqual(response, "현재 잔고는 50만원입니다")
        self.assertEqual(self.llm_client.create_message.call_count, 2)

    def test_chat_stores_conversation_history(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="안녕하세요",
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.chat("안녕")
        self.assertEqual(len(self.op.conversation_history), 2)  # user + assistant

    def test_chat_logs_interaction_to_system_monitor(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.chat("test")
        self.assertEqual(len(self.op.system_monitor.llm_interaction_log), 1)

    def test_chat_trims_conversation_history_when_exceeding_max(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.context_config = ContextConfig(max_conversation_turns=3)
        for i in range(5):
            self.op.chat(f"message {i}")
        self.assertLessEqual(len(self.op.conversation_history), 6)  # 3 turns * 2


class LlmOperatorTimerTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("threading.Timer")
        self.timer_mock_cls = self.patcher.start()
        self.timer_instance = MagicMock()
        self.timer_mock_cls.return_value = self.timer_instance

        self.llm_client = MagicMock()
        self.config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 10}
        self.op = LlmOperator(self.llm_client, self.config)

    def tearDown(self):
        self.patcher.stop()

    def test_start_trading_changes_state_to_running(self):
        self.op.data_provider = MagicMock()
        self.llm_client.create_message.return_value = LlmResponse(
            text="매매를 시작합니다", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.start_trading()
        self.assertEqual(self.op.state, "running")

    def test_stop_trading_changes_state_to_stopped(self):
        self.op.data_provider = MagicMock()
        self.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.start_trading()
        self.op.stop_trading()
        self.assertEqual(self.op.state, "stopped")
```

- [ ] **Step 2: 테스트 실패 확인**

Run: `python -m pytest tests/unit_tests/llm_operator_test.py -v`
Expected: FAIL

- [ ] **Step 3: 구현**

```python
# smtm/llm/llm_operator.py
import os
import threading
from dataclasses import dataclass
from typing import Optional
from ..log_manager import LogManager
from ..worker import Worker
from .llm_client import LlmClient, LlmResponse
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


class LlmOperator:
    """LLM 기반 자율 트레이딩 오퍼레이터"""

    def __init__(self, llm_client: LlmClient, config: dict):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.llm_client = llm_client
        self.config = config
        self.state = "ready"
        self.interval = config.get("interval", 60)
        self.budget = config.get("budget", 500000)

        # 컴포넌트 초기화
        safety_config = SafetyConfig(
            initial_budget=self.budget,
            **config.get("safety", {}),
        )
        self.safety_guard = SafetyGuard(safety_config)
        self.system_monitor = SystemMonitor(
            storage_path=config.get("monitor_storage_path", "output/monitor/"),
        )
        self.tool_router = ToolRouter(self.safety_guard, self.system_monitor)
        self.context_config = ContextConfig(**config.get("context", {}))

        # 대화 관리
        self.conversation_history = []
        self.strategy_knowledge = self._load_strategy_knowledge(
            config.get("strategy_files", [])
        )

        # 타이머
        self.timer = None
        self.is_timer_running = False
        self.worker = Worker("LlmOperator-Worker")

        # DataProvider (setup_tools에서 설정)
        self.data_provider = None

    def setup_tools(self, data_provider=None, trader=None):
        """Tool 등록을 위한 설정. Controller가 호출."""
        from .tools.market_data_tool import MarketDataTool
        from .tools.trade_tool import TradeTool
        from .tools.portfolio_tool import PortfolioTool
        from .tools.trade_history_tool import TradeHistoryTool
        from .tools.performance_tool import PerformanceTool

        if data_provider:
            self.data_provider = data_provider
            self.tool_router.register(MarketDataTool(data_provider))

        if trader:
            self.tool_router.register(TradeTool(trader, self.system_monitor))
            self.tool_router.register(PortfolioTool(trader))
            self.tool_router.register(PerformanceTool(
                self.system_monitor, trader, self.budget,
            ))

        self.tool_router.register(TradeHistoryTool(self.system_monitor))

    def chat(self, message: str) -> str:
        """단일 인터페이스 — 사용자 요청 및 주기적 판단 모두 처리"""
        self.conversation_history.append({"role": "user", "content": message})
        self._trim_conversation_history()

        response_text = self._execute_llm_loop()

        self.conversation_history.append({"role": "assistant", "content": response_text})
        return response_text

    def start_trading(self):
        """매매 시작"""
        if self.state == "running":
            return
        self.state = "running"
        self.worker.start()
        self._start_timer()
        self.logger.info("===== LlmOperator Start =====")

    def stop_trading(self):
        """매매 중지"""
        if self.timer is not None:
            self.timer.cancel()
        self.is_timer_running = False
        self.state = "stopped"
        self.worker.stop()
        self.logger.info("===== LlmOperator Stop =====")

    def _execute_llm_loop(self) -> str:
        """LLM Tool Use 루프"""
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

            # Tool Use 처리
            tool_results_content = []
            for tool_call in response.tool_calls:
                result = self.tool_router.execute(tool_call)
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": str(result.to_dict()),
                })

            # 대화에 tool_use와 tool_result 추가
            messages.append({"role": "assistant", "content": response.tool_calls})
            messages.append({"role": "user", "content": tool_results_content})

    def _on_timer(self):
        """주기적 판단 요청"""
        self.is_timer_running = False
        if self.state != "running":
            return

        try:
            market_data = None
            if self.data_provider:
                market_data = self.data_provider.get_info()
                self.system_monitor.log_market_data(market_data)

            prompt = self._build_periodic_prompt(market_data)
            self.chat(prompt)
        except Exception as e:
            self.logger.error(f"Periodic trading error: {e}")

        self._start_timer()

    def _start_timer(self):
        if self.is_timer_running or self.state != "running":
            return
        self.timer = threading.Timer(self.interval, self._on_timer)
        self.timer.start()
        self.is_timer_running = True

    def _build_system_prompt(self) -> str:
        parts = [
            "당신은 암호화폐 자동 매매 에이전트입니다.",
            "제공되는 Tool을 사용하여 시장을 분석하고, 매매 판단을 내리세요.",
            "리스크 관리를 최우선으로 고려하고, 확신이 없으면 거래하지 마세요.",
            "",
        ]
        if self.strategy_knowledge:
            parts.append("## 참고 전략 지식")
            parts.append(self.strategy_knowledge)
            parts.append("")
        parts.append(f"## 현재 설정")
        parts.append(f"- 거래소: {self.config.get('exchange', 'N/A')}")
        parts.append(f"- 통화: {self.config.get('currency', 'N/A')}")
        parts.append(f"- 초기 예산: {self.budget:,.0f}")
        return "\n".join(parts)

    def _build_periodic_prompt(self, market_data) -> str:
        parts = ["[주기적 시장 판단 요청]"]
        if market_data:
            parts.append(f"현재 시장 데이터: {market_data}")
        parts.append("시장 상황을 분석하고, 필요시 매매를 실행하세요.")
        parts.append("거래가 불필요하다고 판단하면 '관망'으로 응답하세요.")
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

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest tests/unit_tests/llm_operator_test.py -v`
Expected: PASS (8 tests)

- [ ] **Step 5: 커밋**

```bash
git add smtm/llm/llm_operator.py tests/unit_tests/llm_operator_test.py
git commit -m "feat: add LlmOperator with chat interface, timer, and tool use loop"
```

---

## Task 12: 패키지 등록 및 통합

**Files:**
- Modify: `smtm/__init__.py`
- Modify: `smtm/llm/__init__.py`

- [ ] **Step 1: smtm/llm/__init__.py 작성**

```python
# smtm/llm/__init__.py
from .llm_client import LlmClient, LlmResponse, ToolCall
from .claude_llm_client import ClaudeLlmClient
from .tool import Tool, ToolResult
from .tool_router import ToolRouter
from .safety_guard import SafetyGuard, SafetyConfig, SafetyResult
from .system_monitor import SystemMonitor
from .llm_operator import LlmOperator, ContextConfig
```

- [ ] **Step 2: smtm/__init__.py에 추가**

`smtm/__init__.py` 파일 끝 `__version__` 앞에 아래 추가:

```python
from .llm.llm_operator import LlmOperator
from .llm.llm_client import LlmClient
from .llm.claude_llm_client import ClaudeLlmClient
from .llm.safety_guard import SafetyGuard, SafetyConfig
from .llm.system_monitor import SystemMonitor
```

`__all__`에 `"LlmOperator"` 추가.

- [ ] **Step 3: 전체 테스트 실행**

Run: `python -m pytest tests/unit_tests/ -v --tb=short`
Expected: 기존 테스트 + 신규 테스트 모두 PASS

- [ ] **Step 4: 커밋**

```bash
git add smtm/__init__.py smtm/llm/__init__.py
git commit -m "feat: register LLM components in package init"
```

---

## Task 13: 전체 통합 테스트

**Files:**
- Create: `tests/integration_tests/llm_operator_ITG_test.py`

- [ ] **Step 1: 통합 테스트 작성**

```python
# tests/integration_tests/llm_operator_ITG_test.py
import unittest
from unittest.mock import *
from smtm.llm.llm_operator import LlmOperator
from smtm.llm.llm_client import LlmResponse, ToolCall


class LlmOperatorIntegrationTests(unittest.TestCase):
    """LlmOperator 전체 흐름 통합 테스트 (LLM API는 mock)"""

    def test_full_trading_cycle_with_tool_use(self):
        """시장 데이터 조회 → 판단 → 매수 실행 전체 흐름"""
        llm_client = MagicMock()
        config = {
            "exchange": "UPB",
            "currency": "BTC",
            "budget": 500000,
            "interval": 60,
        }
        op = LlmOperator(llm_client, config)

        # Mock DataProvider, Trader
        dp = MagicMock()
        dp.get_info.return_value = [
            {"type": "primary_candle", "market": "BTC", "closing_price": 50000000,
             "opening_price": 49000000, "high_price": 51000000, "low_price": 48000000,
             "acc_price": 1000000, "acc_volume": 100, "date_time": "2026-04-07T12:00:00"}
        ]
        trader = MagicMock()
        trader.get_account_info.return_value = {
            "balance": 500000, "asset": {}, "quote": {},
        }
        def fake_send(req_list, cb):
            cb({"type": "buy", "price": 50000, "amount": 0.01, "state": "done",
                "request": req_list[0], "msg": "success", "balance": 449500,
                "date_time": "2026-04-07T12:00:02"})
        trader.send_request.side_effect = fake_send

        op.setup_tools(data_provider=dp, trader=trader)

        # LLM 응답 시나리오: 먼저 포트폴리오 확인 → 매수 실행 → 최종 응답
        responses = [
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="get_portfolio", arguments={})],
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_2", name="execute_trade",
                    arguments={"action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01})],
                usage={"input_tokens": 300, "output_tokens": 40},
            ),
            LlmResponse(
                text="BTC 0.01개를 50,000원에 매수했습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 400, "output_tokens": 50},
            ),
        ]
        llm_client.create_message.side_effect = responses

        result = op.chat("BTC 시장 분석 후 적절하면 매수해줘")
        self.assertIn("매수", result)
        self.assertEqual(len(op.system_monitor.trade_result_log), 1)
        self.assertEqual(llm_client.create_message.call_count, 3)

    def test_safety_guard_blocks_excessive_trade(self):
        """안전장치가 과도한 거래를 차단하는 흐름"""
        llm_client = MagicMock()
        config = {
            "exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60,
            "safety": {"max_trade_amount": 10000},
        }
        op = LlmOperator(llm_client, config)
        trader = MagicMock()
        op.setup_tools(trader=trader)

        responses = [
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="execute_trade",
                    arguments={"action": "buy", "currency": "BTC", "price": 50000, "amount": 1.0})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="거래금액이 너무 커서 차단되었습니다. 소량으로 분할 매수하겠습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 150, "output_tokens": 30},
            ),
        ]
        llm_client.create_message.side_effect = responses

        result = op.chat("BTC 전량 매수해")
        trader.send_request.assert_not_called()
        self.assertEqual(len(op.system_monitor.safety_event_log), 1)
```

- [ ] **Step 2: 통합 테스트 실행**

Run: `python -m pytest tests/integration_tests/llm_operator_ITG_test.py -v`
Expected: PASS (2 tests)

- [ ] **Step 3: 전체 테스트 최종 확인**

Run: `python -m pytest tests/ -v --tb=short`
Expected: 기존 + 신규 테스트 모두 PASS

- [ ] **Step 4: 커밋**

```bash
git add tests/integration_tests/llm_operator_ITG_test.py
git commit -m "test: add LlmOperator integration tests for full trading cycle and safety guard"
```

---

## 구현 순서 요약

```
Task 1:  LlmClient ABC + ToolCall, LlmResponse
Task 2:  ClaudeLlmClient (Anthropic API)
Task 3:  Tool ABC + ToolResult
Task 4:  SafetyGuard
Task 5:  SystemMonitor
Task 6:  ToolRouter
Task 7:  MarketDataTool
Task 8:  TradeTool
Task 9:  PortfolioTool + TradeHistoryTool + PerformanceTool
Task 10: Strategy Knowledge 문서
Task 11: LlmOperator (핵심)
Task 12: 패키지 등록
Task 13: 통합 테스트
```

의존성 그래프:
```
Task 1 (LlmClient) ──→ Task 2 (ClaudeLlmClient)
Task 3 (Tool)      ──→ Task 7, 8, 9 (Tool 구현체들)
Task 1 + 3         ──→ Task 4 (SafetyGuard)
                   ──→ Task 5 (SystemMonitor)
Task 3 + 4 + 5     ──→ Task 6 (ToolRouter)
Task 1~10 전부      ──→ Task 11 (LlmOperator)
Task 11            ──→ Task 12, 13 (통합)
```
