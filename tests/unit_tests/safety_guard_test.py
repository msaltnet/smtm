import unittest
from unittest.mock import *
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig, SafetyResult


class SafetyGuardTests(unittest.TestCase):
    def setUp(self):
        self.config = SafetyConfig(
            max_trade_amount=100000,
            max_daily_trades=10,
            max_loss_ratio=-0.20,
            initial_budget=500000,
        )
        self.guard = SafetyGuard(self.config)

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


class SafetyGuardCheckRequestTests(unittest.TestCase):
    def setUp(self):
        from smtm.llm.safety_guard import SafetyGuard, SafetyConfig
        self.guard = SafetyGuard(SafetyConfig(
            max_trade_amount=100000, max_daily_trades=2,
            max_loss_ratio=-0.2, initial_budget=500000,
        ))

    def _request(self, type="buy", price=50000, amount=1.0):
        return {"id": "test-id", "type": type, "price": price,
                "amount": amount, "date_time": "2026-07-03T12:00:00"}

    def test_allows_request_within_limits(self):
        result = self.guard.check_request(self._request())
        self.assertTrue(result.allowed)

    def test_blocks_request_exceeding_max_trade_amount(self):
        result = self.guard.check_request(self._request(price=200000, amount=1.0))
        self.assertFalse(result.allowed)
        self.assertIn("최대 거래금액", result.reason)

    def test_cancel_request_bypasses_all_checks(self):
        # 모든 한도를 동시에 위반한 상태에서도 cancel은 무조건 허용된다
        self.guard.record_trade({})
        self.guard.record_trade({})              # 일일 거래횟수 한도 도달
        self.guard.update_portfolio_value(350000)  # -30% < -20% 손실 한도 위반
        result = self.guard.check_request(
            self._request(type="cancel", price=999999999, amount=999))
        self.assertTrue(result.allowed)
        # 동일 상태에서 buy는 차단된다
        result = self.guard.check_request(self._request())
        self.assertFalse(result.allowed)

    def test_blocks_after_daily_trade_limit(self):
        self.guard.record_trade({})
        self.guard.record_trade({})
        result = self.guard.check_request(self._request())
        self.assertFalse(result.allowed)
        self.assertIn("일일 거래횟수", result.reason)

    def test_blocks_when_loss_limit_exceeded(self):
        self.guard.update_portfolio_value(350000)  # -30% < -20%
        result = self.guard.check_request(self._request())
        self.assertFalse(result.allowed)
        self.assertIn("손실 한도", result.reason)
