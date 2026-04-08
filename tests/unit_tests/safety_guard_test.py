import unittest
from unittest.mock import *
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig, SafetyResult
from smtm.llm.llm_client import ToolCall


class SafetyGuardTests(unittest.TestCase):
    def setUp(self):
        self.config = SafetyConfig(
            max_trade_amount=100000,
            max_daily_trades=10,
            max_loss_ratio=-0.20,
            initial_budget=500000,
        )
        self.guard = SafetyGuard(self.config)

    def test_check_allows_valid_trade(self):
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 50000, "amount": 1.0},
        )
        result = self.guard.check(tool_call)
        self.assertTrue(result.allowed)

    def test_check_blocks_trade_exceeding_max_amount(self):
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 200000, "amount": 1.0},
        )
        result = self.guard.check(tool_call)
        self.assertFalse(result.allowed)
        self.assertIn("최대 거래금액", result.reason)

    def test_check_blocks_trade_exceeding_daily_limit(self):
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 10000, "amount": 0.1},
        )
        for _ in range(10):
            self.guard.record_trade({"type": "buy", "price": 10000, "amount": 0.1})

        result = self.guard.check(tool_call)
        self.assertFalse(result.allowed)
        self.assertIn("일일 거래횟수", result.reason)

    def test_check_blocks_trade_when_loss_exceeds_limit(self):
        self.guard.current_value = 350000  # -30% loss from 500000
        tool_call = ToolCall(
            id="tc_1", name="execute_trade",
            arguments={"action": "buy", "price": 10000, "amount": 0.1},
        )
        result = self.guard.check(tool_call)
        self.assertFalse(result.allowed)
        self.assertIn("손실 한도", result.reason)

    def test_check_allows_non_trade_tools(self):
        tool_call = ToolCall(
            id="tc_1", name="get_market_data",
            arguments={"currency": "BTC"},
        )
        result = self.guard.check(tool_call)
        self.assertTrue(result.allowed)

    def test_record_trade_increments_daily_count(self):
        self.assertEqual(self.guard.daily_trade_count, 0)
        self.guard.record_trade({"type": "buy", "price": 10000, "amount": 0.1})
        self.assertEqual(self.guard.daily_trade_count, 1)

    def test_get_status_returns_current_state(self):
        status = self.guard.get_status()
        self.assertEqual(status["daily_trades"], 0)
        self.assertEqual(status["daily_limit"], 10)
        self.assertTrue(status["trading_allowed"])

    def test_update_portfolio_value_updates_current_value(self):
        self.guard.update_portfolio_value(450000)
        self.assertEqual(self.guard.current_value, 450000)
