import unittest

from smtm.trader.simulation_trader import SimulationTrader
from smtm.trader.trader_factory import TraderFactory


class SimulationTraderBuyTest(unittest.TestCase):
    def test_buy_uses_injected_quote_and_ignores_request_price(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        results = []

        trader.send_request([
            {
                "id": "1",
                "type": "buy",
                "price": 1,
                "amount": 0.01,
                "date_time": "2026-04-26T12:00:00",
            }
        ], results.append)

        self.assertEqual(results[0]["state"], "done")
        self.assertEqual(results[0]["price"], 50000)
        self.assertEqual(trader.balance, 499500)
        self.assertEqual(trader.assets["BTC"], (50000, 0.01))

    def test_buy_fails_when_quote_missing(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        results = []

        trader.send_request([
            {"id": "1", "type": "buy", "price": 50000, "amount": 0.01}
        ], results.append)

        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["msg"], "시세 없음")
        self.assertEqual(trader.balance, 500000)

    def test_buy_fails_when_balance_is_not_enough(self):
        trader = SimulationTrader(budget=100, currency="BTC")
        trader.update_quote("BTC", 50000)
        results = []

        trader.send_request([
            {"id": "1", "type": "buy", "price": 50000, "amount": 1}
        ], results.append)

        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["msg"], "잔고 부족")
        self.assertEqual(trader.balance, 100)

    def test_buy_updates_average_cost(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        trader.send_request([
            {"id": "1", "type": "buy", "price": 50000, "amount": 0.01}
        ], lambda result: None)

        trader.update_quote("BTC", 70000)
        trader.send_request([
            {"id": "2", "type": "buy", "price": 70000, "amount": 0.01}
        ], lambda result: None)

        self.assertEqual(trader.assets["BTC"], (60000, 0.02))


class SimulationTraderSellTest(unittest.TestCase):
    def test_sell_adds_balance_and_reduces_asset(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        trader.send_request([
            {"id": "1", "type": "buy", "price": 50000, "amount": 0.02}
        ], lambda result: None)

        trader.update_quote("BTC", 60000)
        results = []
        trader.send_request([
            {"id": "2", "type": "sell", "price": 1, "amount": 0.01}
        ], results.append)

        self.assertEqual(results[0]["state"], "done")
        self.assertEqual(results[0]["price"], 60000)
        self.assertEqual(trader.balance, 499600)
        self.assertEqual(trader.assets["BTC"], (50000, 0.01))

    def test_sell_removes_asset_when_amount_goes_to_zero(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        trader.send_request([
            {"id": "1", "type": "buy", "price": 50000, "amount": 0.01}
        ], lambda result: None)

        trader.send_request([
            {"id": "2", "type": "sell", "price": 50000, "amount": 0.01}
        ], lambda result: None)

        self.assertNotIn("BTC", trader.assets)

    def test_sell_fails_when_asset_is_not_enough(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        results = []

        trader.send_request([
            {"id": "1", "type": "sell", "price": 50000, "amount": 0.01}
        ], results.append)

        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["msg"], "보유 수량 부족")


class SimulationTraderAccountTest(unittest.TestCase):
    def test_get_account_info_returns_balance_assets_and_quotes(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)

        info = trader.get_account_info()

        self.assertEqual(info["balance"], 500000)
        self.assertEqual(info["asset"], {})
        self.assertEqual(info["quote"], {"BTC": 50000})
        self.assertIn("date_time", info)

    def test_cancel_methods_are_noops(self):
        trader = SimulationTrader()
        trader.cancel_request("unknown")
        trader.cancel_all_requests()

        self.assertEqual(trader.order_history, [])


class TraderFactoryPaperFlagTest(unittest.TestCase):
    def test_paper_flag_returns_simulation_trader(self):
        trader = TraderFactory.create("UPB", budget=500000, currency="BTC", paper=True)

        self.assertIsInstance(trader, SimulationTrader)
        self.assertEqual(trader.balance, 500000)

    def test_paper_flag_overrides_exchange_code(self):
        trader = TraderFactory.create("BTH", budget=300000, currency="ETH", paper=True)

        self.assertIsInstance(trader, SimulationTrader)
        self.assertEqual(trader.currency, "ETH")


if __name__ == "__main__":
    unittest.main()
