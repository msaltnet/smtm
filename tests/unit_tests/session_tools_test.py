import unittest
import tempfile
from unittest.mock import patch
from smtm import ProfileStore, AccountStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


class StubDataProvider:
    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-06T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


class SessionToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = patch(
            "smtm.data.data_provider_factory.DataProviderFactory.create",
            side_effect=lambda *a, **k: StubDataProvider())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.profile_store = ProfileStore(dir_path=self.tmp.name + "/profiles")
        self.operator = SystemOperator(StubLlmClient(), {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "virtual": True, "strategy": "BNH",
        }, profile_store=self.profile_store,
           account_store=AccountStore(dir_path=self.tmp.name + "/accounts"))
        self.operator.setup()
        self.tools = self.operator.tool_router.tools
        self.profile_store.save({
            "name": "rsi-v", "exchange": "UPB", "currency": "BTC",
            "budget": 200000, "virtual": True, "strategy": "RSI"})

    def tearDown(self):
        self.operator.shutdown()
        self.tmp.cleanup()

    def test_session_tools_registered(self):
        for name in ("create_session", "start_session", "stop_session",
                     "remove_session", "list_sessions", "compare_performance"):
            self.assertIn(name, self.tools)

    def test_create_start_stop_remove_flow(self):
        result = self.tools["create_session"].execute({"profile": "rsi-v"})
        self.assertTrue(result.success)
        self.assertTrue(self.tools["start_session"].execute(
            {"session": "rsi-v"}).success)
        self.assertTrue(self.tools["stop_session"].execute(
            {"session": "rsi-v"}).success)
        self.assertTrue(self.tools["remove_session"].execute(
            {"session": "rsi-v"}).success)

    def test_create_with_custom_session_name(self):
        result = self.tools["create_session"].execute(
            {"profile": "rsi-v", "session": "exp-1"})
        self.assertTrue(result.success)
        names = [s["name"] for s in
                 self.operator.session_manager.list_sessions()]
        self.assertIn("exp-1", names)

    def test_create_with_missing_profile_fails(self):
        result = self.tools["create_session"].execute({"profile": "nope"})
        self.assertFalse(result.success)

    def test_list_sessions_and_compare(self):
        self.tools["create_session"].execute({"profile": "rsi-v"})
        listing = self.tools["list_sessions"].execute({})
        self.assertEqual(len(listing.data["sessions"]), 2)  # default + rsi-v
        compare = self.tools["compare_performance"].execute({})
        self.assertEqual(len(compare.data["performance"]), 2)

    def test_get_status_supports_session_argument(self):
        status = self.tools["get_status"].execute({"session": "default"})
        self.assertTrue(status.success)
        self.assertEqual(status.data["name"], "default")
        overview = self.tools["get_status"].execute({})
        self.assertIn("sessions", overview.data)

    def test_remove_default_session_is_allowed_but_reported(self):
        result = self.tools["remove_session"].execute({"session": "default"})
        self.assertTrue(result.success)
