import unittest
import tempfile
from unittest.mock import patch
from smtm import ProfileStore
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
    # switch_profile/apply_profile은 rebuild_infra=True로 DataProvider를
    # 다시 생성하므로, 실 거래소 대신 스텁을 사용하도록 패치한다.
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
