import unittest
from unittest.mock import patch
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse, ToolCall


class StubDataProvider:
    """실 네트워크 호출 없이 고정 캔들을 반환하는 테스트용 DataProvider"""

    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-03T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


_data_provider_patcher = None


def setUpModule():
    # SystemOperator._build_trading_components는 DataProviderFactory를 지역
    # import하므로, 실제 Factory의 create를 패치해 어떤 유닛 테스트도 실
    # 거래소로 네트워크 틱을 보내지 않도록 한다 (apply_profile 등은
    # rebuild_infra=True로 이 경로를 다시 탄다).
    global _data_provider_patcher
    _data_provider_patcher = patch(
        "smtm.data.data_provider_factory.DataProviderFactory.create",
        return_value=StubDataProvider(),
    )
    _data_provider_patcher.start()


def tearDownModule():
    _data_provider_patcher.stop()


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

    def test_apply_profile_failure_keeps_current_config(self):
        result = self.operator.apply_profile({
            "name": "bad", "strategy": "NOPE", "budget": 999999,
        })
        self.assertFalse(result["success"])
        self.assertEqual(self.operator.strategy_code, "BNH")
        self.assertEqual(self.operator.budget, 500000)
        self.assertEqual(self.operator.config.get("strategy"), "BNH")
        # 재구성 후에도 매매 시작이 가능해야 한다 (일관 상태)
        self.assertTrue(self.operator.start_trading()["success"])

    def test_apply_profile_with_bad_safety_key_keeps_config(self):
        result = self.operator.apply_profile({
            "name": "bad-safety", "safety": {"max_trade": 5},
        })
        self.assertFalse(result["success"])
        # make_operator의 초기 config에는 "safety" 키가 없으므로 복원 후에도
        # 부재 상태가 유지되어야 한다 (반쯤 재구성된 상태가 아니라 이전
        # 스냅샷 그대로).
        self.assertIsNone(self.operator.config.get("safety"))
        # 복원 후에도 일관 상태
        self.assertTrue(self.operator.start_trading()["success"])

    def test_select_strategy_preserves_daily_trade_count(self):
        self.operator.safety_guard.record_trade({})
        self.operator.safety_guard.record_trade({})
        self.operator.select_strategy("RSI")
        self.assertEqual(self.operator.safety_guard.daily_trade_count, 2)


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

    def test_tool_loop_appends_anthropic_format_blocks(self):
        responses = [
            LlmResponse(text="확인해볼게요", tool_calls=[
                ToolCall(id="t1", name="get_portfolio", arguments={})
            ], stop_reason="tool_use"),
            LlmResponse(text="완료"),
        ]
        operator = make_operator(responses=responses)
        operator.chat("포트폴리오?")
        second_call_messages = operator.llm_client.call_log[1]["messages"]
        assistant_msg = second_call_messages[-2]
        self.assertEqual(assistant_msg["role"], "assistant")
        types = [block["type"] for block in assistant_msg["content"]]
        self.assertIn("text", types)
        self.assertIn("tool_use", types)
        tool_block = [b for b in assistant_msg["content"] if b["type"] == "tool_use"][0]
        self.assertEqual(tool_block["name"], "get_portfolio")
        self.assertEqual(tool_block["id"], "t1")

    def test_chat_trims_history(self):
        operator = make_operator(config_extra={
            "context": {"max_conversation_turns": 2}})
        for i in range(5):
            operator.llm_client.responses.append(LlmResponse(text=f"r{i}"))
            operator.chat(f"m{i}")
        self.assertLessEqual(len(operator.conversation_history), 4)
