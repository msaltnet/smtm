import unittest
from unittest.mock import *
from smtm.llm.tools.performance_tool import PerformanceTool


class PerformanceToolTests(unittest.TestCase):
    def test_execute_returns_performance_summary(self):
        monitor_mock = MagicMock()
        monitor_mock.get_trade_log.return_value = [{"result": {"type": "buy"}}]
        trader_mock = MagicMock()
        trader_mock.get_account_info.return_value = {"balance": 450000, "asset": {}, "quote": {}}
        tool = PerformanceTool(monitor_mock, trader_mock, initial_budget=500000)
        result = tool.execute({})
        self.assertTrue(result.success)
        self.assertIn("total_value", result.data)
        self.assertEqual(result.data["return_ratio"], -0.1)
