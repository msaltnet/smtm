import unittest
from unittest.mock import *
from smtm.llm.tools.trade_history_tool import TradeHistoryTool


class TradeHistoryToolTests(unittest.TestCase):
    def setUp(self):
        self.monitor = MagicMock()
        self.monitor.get_trade_log.return_value = [
            {"result": {"type": "buy", "price": 50000}},
            {"result": {"type": "sell", "price": 51000}},
        ]
        self.tool = TradeHistoryTool(self.monitor)

    def test_execute_returns_trade_log(self):
        result = self.tool.execute({"count": 10})
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)

    def test_session_omitted_queries_all(self):
        self.tool.execute({})
        self.monitor.get_trade_log.assert_called_with(session=None)

    def test_explicit_session_routed(self):
        self.tool.execute({"session": "s2"})
        self.monitor.get_trade_log.assert_called_with(session="s2")

    def test_execute_returns_error_on_exception(self):
        self.monitor.get_trade_log.side_effect = Exception("db error")
        result = self.tool.execute({})
        self.assertFalse(result.success)
