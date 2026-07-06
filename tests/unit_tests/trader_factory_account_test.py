import os
import unittest
from unittest.mock import patch
from smtm.trader.trader_factory import TraderFactory
from smtm.trader.simulation_trader import SimulationTrader


class TraderFactoryAccountTests(unittest.TestCase):
    def test_create_with_account_uses_custom_env_names(self):
        with patch.dict(os.environ, {
            "SMTM_KEY_9": "custom-access",
            "SMTM_SECRET_9": "custom-secret",
            "UPBIT_OPEN_API_SERVER_URL": "https://api.upbit.com",
        }):
            trader = TraderFactory.create(
                "UPB", budget=100000, currency="BTC",
                account={"access_key_env": "SMTM_KEY_9",
                         "secret_key_env": "SMTM_SECRET_9"})
        self.assertEqual(trader.ACCESS_KEY, "custom-access")
        self.assertEqual(trader.SECRET_KEY, "custom-secret")
        trader.worker.stop()

    def test_create_without_account_uses_legacy_env_names(self):
        with patch.dict(os.environ, {
            "UPBIT_OPEN_API_ACCESS_KEY": "legacy-access",
            "UPBIT_OPEN_API_SECRET_KEY": "legacy-secret",
            "UPBIT_OPEN_API_SERVER_URL": "https://api.upbit.com",
        }):
            trader = TraderFactory.create("UPB", budget=100000, currency="BTC")
        self.assertEqual(trader.ACCESS_KEY, "legacy-access")
        trader.worker.stop()

    def test_paper_ignores_account(self):
        trader = TraderFactory.create(
            "UPB", budget=100000, currency="BTC", paper=True,
            account={"access_key_env": "X", "secret_key_env": "Y"})
        self.assertIsInstance(trader, SimulationTrader)

    def test_cancel_all_requests_only_touches_own_order_map(self):
        # 자기 order_map의 주문만 취소 요청한다 (계좌 전체 취소 금지 보장)
        with patch.dict(os.environ, {
            "UPBIT_OPEN_API_ACCESS_KEY": "a", "UPBIT_OPEN_API_SECRET_KEY": "b",
            "UPBIT_OPEN_API_SERVER_URL": "https://api.upbit.com",
        }):
            trader = TraderFactory.create("UPB", budget=100000, currency="BTC")
        cancelled = []
        trader.cancel_request = lambda request_id: cancelled.append(request_id)
        trader.order_map = {"r1": {"uuid": "u1"}, "r2": {"uuid": "u2"}}
        trader.cancel_all_requests()
        self.assertEqual(sorted(cancelled), ["r1", "r2"])
        trader.worker.stop()
