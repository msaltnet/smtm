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
