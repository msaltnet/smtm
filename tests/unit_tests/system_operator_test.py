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
