import threading
import unittest
from smtm.llm.account_guard import (
    AccountGuard, AccountGuardConfig, CompositeSafetyGuard,
)
from smtm.llm.safety_guard import SafetyGuard, SafetyConfig


def _request(type="buy", price=50000, amount=1.0):
    return {"id": "t", "type": type, "price": price, "amount": amount,
            "date_time": "2026-07-06T12:00:00"}


class AccountGuardTests(unittest.TestCase):
    def setUp(self):
        self.guard = AccountGuard(AccountGuardConfig(
            max_daily_trades=3, max_total_allocation=1000000))

    def test_allows_within_daily_limit_blocks_after(self):
        for _ in range(3):
            self.assertTrue(self.guard.check_request(_request()).allowed)
            self.guard.record_trade({})
        verdict = self.guard.check_request(_request())
        self.assertFalse(verdict.allowed)
        self.assertIn("계좌 일일 거래횟수", verdict.reason)

    def test_cancel_always_allowed(self):
        for _ in range(3):
            self.guard.record_trade({})
        self.assertTrue(self.guard.check_request(_request(type="cancel")).allowed)

    def test_allocation_lifecycle(self):
        self.assertTrue(self.guard.can_allocate(600000).allowed)
        self.guard.allocate("s1", 600000)
        self.assertEqual(self.guard.total_allocated(), 600000)
        verdict = self.guard.can_allocate(500000)  # 600000+500000 > 1000000
        self.assertFalse(verdict.allowed)
        self.assertIn("할당 총액", verdict.reason)
        self.guard.release("s1")
        self.assertTrue(self.guard.can_allocate(500000).allowed)

    def test_release_unknown_session_is_noop(self):
        self.guard.release("nope")
        self.assertEqual(self.guard.total_allocated(), 0)

    def test_record_trade_is_thread_safe(self):
        guard = AccountGuard(AccountGuardConfig(max_daily_trades=100000))
        threads = [threading.Thread(
            target=lambda: [guard.record_trade({}) for _ in range(500)])
            for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(guard.daily_trade_count, 2000)

    def test_get_status_summarizes(self):
        self.guard.allocate("s1", 300000)
        self.guard.record_trade({})
        status = self.guard.get_status()
        self.assertEqual(status["daily_trades"], 1)
        self.assertEqual(status["daily_limit"], 3)
        self.assertEqual(status["total_allocated"], 300000)
        self.assertIn("s1", status["allocations"])


class CompositeSafetyGuardTests(unittest.TestCase):
    def setUp(self):
        self.session_guard = SafetyGuard(SafetyConfig(
            max_trade_amount=100000, max_daily_trades=10,
            max_loss_ratio=-0.5, initial_budget=500000))
        self.account_guard = AccountGuard(AccountGuardConfig(max_daily_trades=2))
        self.composite = CompositeSafetyGuard(self.session_guard, self.account_guard)

    def test_passes_when_both_allow(self):
        self.assertTrue(self.composite.check_request(_request()).allowed)

    def test_session_block_wins_first(self):
        verdict = self.composite.check_request(_request(price=200000, amount=1.0))
        self.assertFalse(verdict.allowed)
        self.assertIn("최대 거래금액", verdict.reason)  # 세션 사유

    def test_account_block_applies(self):
        self.account_guard.record_trade({})
        self.account_guard.record_trade({})
        verdict = self.composite.check_request(_request())
        self.assertFalse(verdict.allowed)
        self.assertIn("계좌 일일 거래횟수", verdict.reason)

    def test_record_trade_propagates_to_both(self):
        self.composite.record_trade({})
        self.assertEqual(self.session_guard.daily_trade_count, 1)
        self.assertEqual(self.account_guard.daily_trade_count, 1)

    def test_update_portfolio_value_only_session(self):
        self.composite.update_portfolio_value(400000)
        self.assertEqual(self.session_guard.current_value, 400000)

    def test_get_status_has_both(self):
        status = self.composite.get_status()
        self.assertIn("session", status)
        self.assertIn("account", status)
