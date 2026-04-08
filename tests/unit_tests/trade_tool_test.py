import unittest
from unittest.mock import *
from smtm.llm.tools.trade_tool import TradeTool
from smtm.llm.system_monitor import SystemMonitor


class TradeToolTests(unittest.TestCase):
    def setUp(self):
        self.trader_mock = MagicMock()
        self.monitor = SystemMonitor()
        self.tool = TradeTool(self.trader_mock, self.monitor)

    def test_name_and_schema_are_set(self):
        self.assertEqual(self.tool.name, "execute_trade")
        self.assertIn("action", self.tool.input_schema["properties"])

    def test_execute_buy_calls_trader_send_request(self):
        def fake_send(request_list, callback):
            callback({"request": request_list[0], "type": "buy", "price": 50000, "amount": 0.01,
                       "state": "done", "msg": "success", "balance": 449500, "date_time": "2026-04-07T12:00:00"})
        self.trader_mock.send_request.side_effect = fake_send
        result = self.tool.execute({"action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01})
        self.assertTrue(result.success)
        self.trader_mock.send_request.assert_called_once()

    def test_execute_logs_trade_to_monitor(self):
        def fake_send(request_list, callback):
            callback({"state": "done", "type": "buy", "price": 50000, "amount": 0.01})
        self.trader_mock.send_request.side_effect = fake_send
        self.tool.execute({"action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01})
        self.assertEqual(len(self.monitor.trade_request_log), 1)
        self.assertEqual(len(self.monitor.trade_result_log), 1)

    def test_execute_returns_error_on_exception(self):
        self.trader_mock.send_request.side_effect = Exception("connection error")
        result = self.tool.execute({"action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01})
        self.assertFalse(result.success)
        self.assertIn("connection error", result.error)
