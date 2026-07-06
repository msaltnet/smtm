import unittest
from unittest.mock import patch
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse


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
    # start_trading 경로에서 실 거래소로 네트워크 틱이 나가지 않도록
    # DataProviderFactory.create를 패치한다.
    global _data_provider_patcher
    _data_provider_patcher = patch(
        "smtm.data.data_provider_factory.DataProviderFactory.create",
        return_value=StubDataProvider(),
    )
    _data_provider_patcher.start()


def tearDownModule():
    _data_provider_patcher.stop()


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
        self.assertEqual(self.operator.default_strategy(), "SMA")

    def test_start_stop_get_status_flow(self):
        result = self.tools["start_trading"].execute({})
        self.assertTrue(result.success)
        status = self.tools["get_status"].execute({})
        default = [s for s in status.data["sessions"] if s["name"] == "default"][0]
        self.assertEqual(default["state"], "running")
        result = self.tools["stop_trading"].execute({})
        self.assertTrue(result.success)
