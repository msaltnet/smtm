import unittest
from unittest.mock import *
from smtm.llm.tools.portfolio_tool import PortfolioTool


class PortfolioToolTests(unittest.TestCase):
    def setUp(self):
        self.manager = MagicMock()
        self.session = MagicMock()
        self.session.trader.get_account_info.return_value = {
            "balance": 400000, "asset": {}, "quote": {},
        }
        self.manager.get_session.return_value = self.session
        self.tool = PortfolioTool(self.manager)

    def test_default_session_used_when_omitted(self):
        result = self.tool.execute({})
        self.manager.get_session.assert_called_with("default")
        self.assertTrue(result.success)
        self.assertEqual(result.data["balance"], 400000)

    def test_explicit_session_routed(self):
        self.tool.execute({"session": "s2"})
        self.manager.get_session.assert_called_with("s2")

    def test_unknown_session_returns_error(self):
        self.manager.get_session.side_effect = ValueError("세션을 찾을 수 없습니다: x")
        result = self.tool.execute({"session": "x"})
        self.assertFalse(result.success)

    def test_execute_returns_error_on_exception(self):
        self.session.trader.get_account_info.side_effect = Exception("auth error")
        result = self.tool.execute({})
        self.assertFalse(result.success)
