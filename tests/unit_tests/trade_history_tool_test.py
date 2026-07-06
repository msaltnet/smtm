import unittest
from unittest.mock import *
from smtm.llm.tools.trade_history_tool import TradeHistoryTool


class TradeHistoryToolTests(unittest.TestCase):
    def test_execute_returns_trade_log(self):
        monitor_mock = MagicMock()
        monitor_mock.get_trade_log.return_value = [
            {"result": {"type": "buy", "price": 50000}},
            {"result": {"type": "sell", "price": 51000}},
        ]
        tool = TradeHistoryTool(monitor_mock)
        result = tool.execute({"count": 10})
        self.assertTrue(result.success)
        self.assertEqual(len(result.data), 2)
