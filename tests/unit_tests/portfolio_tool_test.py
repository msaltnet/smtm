import unittest
from unittest.mock import *
from smtm.llm.tools.portfolio_tool import PortfolioTool


class PortfolioToolTests(unittest.TestCase):
    def test_execute_returns_account_info(self):
        trader_mock = MagicMock()
        trader_mock.get_account_info.return_value = {"balance": 400000, "asset": {}, "quote": {}}
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
