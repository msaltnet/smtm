import os
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from smtm import AccountStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


class StubDataProvider:
    def get_info(self):
        return []


class AccountToolsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = patch(
            "smtm.data.data_provider_factory.DataProviderFactory.create",
            side_effect=lambda *a, **k: StubDataProvider())
        patcher.start()
        self.addCleanup(patcher.stop)
        self.operator = SystemOperator(StubLlmClient(), {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "virtual": True, "strategy": "BNH",
        }, account_store=AccountStore(dir_path=self.tmp.name))
        self.operator.setup()
        self.tools = self.operator.tool_router.tools

    def tearDown(self):
        self.operator.shutdown()
        self.tmp.cleanup()

    def test_account_tools_registered(self):
        for name in ("register_account", "list_accounts", "delete_account"):
            self.assertIn(name, self.tools)

    def test_register_and_list(self):
        with patch.dict(os.environ, {"SMTM_K1": "a", "SMTM_S1": "b"}):
            result = self.tools["register_account"].execute({
                "name": "main", "exchange": "UPB",
                "access_key_env": "SMTM_K1", "secret_key_env": "SMTM_S1"})
            self.assertTrue(result.success)
            self.assertTrue(result.data["env_ready"])
            listing = self.tools["list_accounts"].execute({})
        self.assertEqual(listing.data["accounts"][0]["name"], "main")

    def test_register_with_unset_env_warns(self):
        result = self.tools["register_account"].execute({
            "name": "sub", "exchange": "UPB",
            "access_key_env": "SMTM_UNSET_K", "secret_key_env": "SMTM_UNSET_S"})
        self.assertTrue(result.success)
        self.assertFalse(result.data["env_ready"])
        self.assertIn("환경변수", result.data["warning"])

    def test_register_never_returns_key_values(self):
        with patch.dict(os.environ, {"SMTM_K1": "SECRET-VALUE", "SMTM_S1": "b"}):
            result = self.tools["register_account"].execute({
                "name": "main", "exchange": "UPB",
                "access_key_env": "SMTM_K1", "secret_key_env": "SMTM_S1"})
        self.assertNotIn("SECRET-VALUE", str(result.data))

    def test_delete_account(self):
        self.tools["register_account"].execute({
            "name": "gone", "exchange": "UPB",
            "access_key_env": "K", "secret_key_env": "S"})
        result = self.tools["delete_account"].execute({"name": "gone"})
        self.assertTrue(result.success)
        result = self.tools["delete_account"].execute({"name": "gone"})
        self.assertFalse(result.success)

    def test_delete_account_in_use_rejected(self):
        with patch.dict(os.environ, {"SMTM_K1": "a", "SMTM_S1": "b"}):
            self.tools["register_account"].execute({
                "name": "busy", "exchange": "UPB",
                "access_key_env": "SMTM_K1", "secret_key_env": "SMTM_S1"})
            fake_trader = MagicMock()
            fake_trader.get_account_info.return_value = {"balance": 10000000}
            with patch("smtm.trader.trader_factory.TraderFactory.create",
                       return_value=fake_trader):
                self.operator.session_manager.create_session({
                    "name": "r1", "exchange": "UPB", "currency": "BTC",
                    "budget": 100000, "virtual": False, "strategy": "BNH",
                    "account": "busy"})
        result = self.tools["delete_account"].execute({"name": "busy"})
        self.assertFalse(result.success)
        self.assertIn("사용 중", result.error)
