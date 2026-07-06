import os
import time
import unittest
import tempfile
from unittest.mock import patch, MagicMock
from smtm import SessionManager, AccountStore
from smtm.llm.system_monitor import SystemMonitor


class StubDataProvider:
    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-06T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


VIRTUAL_PROFILE = {
    "name": "v1", "exchange": "UPB", "currency": "BTC",
    "budget": 500000, "virtual": True, "term": 60, "strategy": "BNH",
}


def make_manager(tmp_dir):
    store = AccountStore(dir_path=tmp_dir)
    manager = SessionManager(
        account_store=store, llm_client=None,
        system_monitor=SystemMonitor())
    return manager, store


class SessionManagerVirtualTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager, self.store = make_manager(self.tmp.name)
        patcher = patch(
            "smtm.data.data_provider_factory.DataProviderFactory.create",
            side_effect=lambda *a, **k: StubDataProvider())
        patcher.start()
        self.addCleanup(patcher.stop)

    def tearDown(self):
        self.manager.stop_all()
        self.tmp.cleanup()

    def test_create_and_start_two_virtual_sessions_independently(self):
        r1 = self.manager.create_session(VIRTUAL_PROFILE)
        r2 = self.manager.create_session(
            {**VIRTUAL_PROFILE, "name": "v2", "strategy": "RSI"})
        self.assertTrue(r1["success"] and r2["success"])
        self.assertTrue(self.manager.start_session("v1")["success"])
        self.assertTrue(self.manager.start_session("v2")["success"])
        # start()가 워커에 첫 틱을 즉시 post하므로 수동 틱 대신 폴링으로
        # 첫 체결을 기다린다 (interval=60 → 두 번째 틱 없음)
        s1 = self.manager.get_session("v1")
        s2 = self.manager.get_session("v2")
        deadline = time.time() + 5
        while time.time() < deadline and len(s1.trader.order_history) == 0:
            time.sleep(0.05)
        self.assertEqual(len(s1.trader.order_history), 1)  # BnH 첫 틱 매수
        # v2(RSI)는 캔들 부족으로 주문 없음 — 서로 간섭 없음 확인이 핵심
        self.assertEqual(s2.trader.balance, 500000)
        self.manager.stop_session("v1")
        self.manager.stop_session("v2")

    def test_duplicate_name_rejected(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        result = self.manager.create_session(VIRTUAL_PROFILE)
        self.assertFalse(result["success"])
        self.assertIn("이미 존재", result["error"])

    def test_invalid_strategy_rejected_without_side_effects(self):
        result = self.manager.create_session({**VIRTUAL_PROFILE, "strategy": "NOPE"})
        self.assertFalse(result["success"])
        self.assertEqual(self.manager.list_sessions(), [])

    def test_remove_running_session_stops_first(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        self.manager.start_session("v1")
        result = self.manager.remove_session("v1")
        self.assertTrue(result["success"])
        self.assertEqual(self.manager.list_sessions(), [])

    def test_list_sessions_summary(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        summary = self.manager.list_sessions()[0]
        self.assertEqual(summary["name"], "v1")
        self.assertEqual(summary["state"], "ready")
        self.assertEqual(summary["strategy"], "BNH")
        self.assertTrue(summary["virtual"])

    def test_compare_performance_covers_all_sessions(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        self.manager.create_session({**VIRTUAL_PROFILE, "name": "v2"})
        rows = self.manager.compare_performance()
        self.assertEqual({r["session"] for r in rows}, {"v1", "v2"})
        self.assertIn("cumulative_return", rows[0])

    def test_replace_session_preserves_daily_count_and_rolls_back(self):
        self.manager.create_session(VIRTUAL_PROFILE)
        self.manager.get_session("v1").session_guard.record_trade({})
        # 교체 성공: 카운터 승계
        result = self.manager.replace_session(
            "v1", {**VIRTUAL_PROFILE, "strategy": "RSI"})
        self.assertTrue(result["success"])
        self.assertEqual(
            self.manager.get_session("v1").session_guard.daily_trade_count, 1)
        # 교체 실패: 기존 세션 유지
        result = self.manager.replace_session(
            "v1", {**VIRTUAL_PROFILE, "strategy": "NOPE"})
        self.assertFalse(result["success"])
        self.assertEqual(self.manager.get_session("v1").profile["strategy"], "RSI")

    def test_assembly_failure_returns_korean_error(self):
        result = self.manager.create_session(
            {**VIRTUAL_PROFILE, "name": "bad-safety",
             "safety": {"max_trade": 5}})  # 잘못된 키 → TypeError
        self.assertFalse(result["success"])
        self.assertIn("세션 조립 실패", result["error"])
        self.assertEqual(self.manager.list_sessions(), [])


class SessionManagerRealTradeValidationTests(unittest.TestCase):
    """실거래 검증 경로 — Trader/잔고는 전부 mock"""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.manager, self.store = make_manager(self.tmp.name)
        self.store.save({"name": "main", "exchange": "UPB",
                         "access_key_env": "SMTM_T_K1",
                         "secret_key_env": "SMTM_T_S1"})
        self.real_profile = {
            "name": "r1", "exchange": "UPB", "currency": "BTC",
            "budget": 300000, "virtual": False, "term": 60,
            "strategy": "BNH", "account": "main",
        }
        self.fake_trader = MagicMock()
        self.fake_trader.get_account_info.return_value = {
            "balance": 1000000, "asset": {}, "quote": {}}
        dp = patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: StubDataProvider())
        tf = patch("smtm.trader.trader_factory.TraderFactory.create",
                   return_value=self.fake_trader)
        env = patch.dict(os.environ, {"SMTM_T_K1": "k", "SMTM_T_S1": "s"})
        for p in (dp, tf, env):
            p.start()
            self.addCleanup(p.stop)

    def tearDown(self):
        self.manager.stop_all()
        self.tmp.cleanup()

    def test_real_session_created_with_composite_guard_and_allocation(self):
        result = self.manager.create_session(self.real_profile)
        self.assertTrue(result["success"])
        guard = self.manager.get_account_guard("main")
        self.assertEqual(guard.total_allocated(), 300000)
        from smtm.llm.account_guard import CompositeSafetyGuard
        session = self.manager.get_session("r1")
        self.assertIsInstance(session.operator.safety_guard, CompositeSafetyGuard)

    def test_missing_account_rejected(self):
        result = self.manager.create_session(
            {**self.real_profile, "name": "r2", "account": "ghost"})
        self.assertFalse(result["success"])

    def test_missing_env_rejected(self):
        os.environ.pop("SMTM_T_S1", None)
        result = self.manager.create_session({**self.real_profile, "name": "r3"})
        self.assertFalse(result["success"])
        self.assertIn("SMTM_T_S1", result["error"])

    def test_exchange_mismatch_rejected(self):
        result = self.manager.create_session(
            {**self.real_profile, "name": "r4", "exchange": "BTH"})
        self.assertFalse(result["success"])
        self.assertIn("거래소", result["error"])

    def test_account_symbol_conflict_rejected_but_other_symbol_ok(self):
        self.manager.create_session(self.real_profile)
        conflict = self.manager.create_session(
            {**self.real_profile, "name": "r5"})  # 같은 main+BTC
        self.assertFalse(conflict["success"])
        self.assertIn("이미 운영 중", conflict["error"])
        other = self.manager.create_session(
            {**self.real_profile, "name": "r6", "currency": "ETH"})
        self.assertTrue(other["success"])

    def test_budget_over_real_balance_rejected(self):
        result = self.manager.create_session(
            {**self.real_profile, "name": "r7", "budget": 2000000})
        self.assertFalse(result["success"])
        self.assertIn("잔고", result["error"])

    def test_allocation_sum_respects_balance(self):
        self.manager.create_session(self.real_profile)  # 30만 할당
        result = self.manager.create_session(
            {**self.real_profile, "name": "r8", "currency": "ETH",
             "budget": 800000})  # 30+80 > 100만
        self.assertFalse(result["success"])

    def test_balance_query_failure_rejects_creation(self):
        self.fake_trader.get_account_info.side_effect = RuntimeError("api down")
        result = self.manager.create_session(self.real_profile)
        self.assertFalse(result["success"])
        self.assertIn("잔고 조회 실패", result["error"])

    def test_remove_releases_allocation(self):
        self.manager.create_session(self.real_profile)
        self.manager.remove_session("r1")
        self.assertEqual(self.manager.get_account_guard("main").total_allocated(), 0)

    def test_non_default_real_session_requires_account(self):
        profile = dict(self.real_profile)
        del profile["account"]
        result = self.manager.create_session(profile)
        self.assertFalse(result["success"])
        self.assertIn("account", result["error"])

    def test_default_legacy_real_session_skips_balance_check(self):
        profile = dict(self.real_profile)
        del profile["account"]
        profile["name"] = "default"
        self.fake_trader.get_account_info.side_effect = RuntimeError("no api")
        result = self.manager.create_session(profile)
        self.assertTrue(result["success"])
        self.assertEqual(self.manager.get_session("default").account, "legacy")
