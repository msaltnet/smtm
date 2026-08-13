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
                "ord_type": "market",
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
            {
                "id": "1", "type": "buy", "price": 50000, "amount": 0.01,
                "ord_type": "market",
            }
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

    def test_failed_fill_zeroes_price_and_amount(self):
        trader = SimulationTrader(budget=1000, currency="BTC")
        trader.update_quote("BTC", 50000)
        results = []
        trader.send_request([{  # 잔고 부족 → 실패
            "id": "r1", "type": "buy", "price": 50000, "amount": 1.0,
            "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["price"], 0)
        self.assertEqual(results[0]["amount"], 0)

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
            {
                "id": "2", "type": "sell", "price": 1, "amount": 0.01,
                "ord_type": "market",
            }
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


class SimulationTraderLimitOrderTest(unittest.TestCase):
    def _request(self, request_id, side, price, amount):
        return {
            "id": request_id,
            "type": side,
            "price": price,
            "amount": amount,
            "ord_type": "limit",
        }

    def test_marketable_limit_buy_fills_at_quote_with_price_improvement(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        trader.update_quote("BTC", 50000)
        results = []

        trader.send_request([
            self._request("buy-now", "buy", 55000, 1),
        ], results.append)

        self.assertEqual(results[0]["state"], "done")
        self.assertEqual(results[0]["price"], 50000)
        self.assertEqual(trader.balance, 50000)

    def test_nonmarketable_limit_buy_reserves_balance_and_snapshot_is_defensive(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        trader.update_quote("BTC", 50000)
        results = []
        trader.send_request([
            self._request("buy-later", "buy", 40000, 2),
        ], results.append)

        self.assertEqual(results[0]["state"], "requested")
        self.assertEqual(trader.balance, 100000)
        account = trader.get_account_info()
        self.assertEqual(account["reserved_balance"], 80000)
        self.assertEqual(account["available_balance"], 20000)
        self.assertEqual(len(account["open_orders"]), 1)
        account["open_orders"][0]["request"]["price"] = 1
        account["quote"]["BTC"] = 1
        fresh_account = trader.get_account_info()
        self.assertEqual(fresh_account["open_orders"][0]["request"]["price"], 40000)
        self.assertEqual(fresh_account["quote"]["BTC"], 50000)

        trader.update_quote("BTC", 39000)

        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["price"], 39000)
        self.assertEqual(trader.balance, 22000)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)

    def test_nonmarketable_limit_sell_reserves_asset_until_fill(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        trader.assets["BTC"] = (50000, 2)
        trader.update_quote("BTC", 50000)
        results = []
        trader.send_request([
            self._request("sell-later", "sell", 60000, 1.5),
        ], results.append)

        account = trader.get_account_info()
        self.assertEqual(account["reserved_asset"], {"BTC": 1.5})
        self.assertEqual(account["available_asset"], {"BTC": 0.5})

        trader.update_quote("BTC", 61000)

        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["price"], 61000)
        self.assertEqual(trader.assets["BTC"], (50000, 0.5))

    def test_limit_reservations_prevent_double_spend(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        trader.update_quote("BTC", 50000)
        first_results = []
        second_results = []
        trader.send_request([
            self._request("first", "buy", 40000, 2),
        ], first_results.append)
        trader.send_request([
            self._request("second", "buy", 30000, 1),
        ], second_results.append)

        self.assertEqual(first_results[0]["state"], "requested")
        self.assertEqual(second_results[0]["state"], "failed")
        self.assertEqual(second_results[0]["msg"], "잔고 부족")

    def test_limit_can_queue_before_first_quote_then_fill(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        results = []
        trader.send_request([
            self._request("before-quote", "buy", 50000, 1),
        ], results.append)

        self.assertEqual(results[0]["state"], "requested")
        trader.update_quote("BTC", 49000)
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["price"], 49000)

    def test_duplicate_pending_limit_id_is_rejected(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        trader.update_quote("BTC", 50000)
        results = []
        trader.send_request([
            self._request("duplicate", "buy", 40000, 1),
        ], results.append)
        trader.send_request([
            self._request("duplicate", "buy", 30000, 1),
        ], results.append)

        self.assertEqual(results[0]["state"], "requested")
        self.assertEqual(results[1]["state"], "failed")
        self.assertEqual(results[1]["msg"], "중복 주문 ID")

    def test_account_info_includes_order_book_contract_keys(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        trader.update_quote("BTC", 50000)

        account = trader.get_account_info()

        self.assertEqual(set(account), {
            "balance", "available_balance", "reserved_balance", "asset",
            "available_asset", "reserved_asset", "quote", "open_orders",
            "date_time",
        })
        self.assertEqual(account["available_balance"], 100000)
        self.assertEqual(account["reserved_balance"], 0)
        self.assertEqual(account["available_asset"], {})
        self.assertEqual(account["reserved_asset"], {})
        self.assertEqual(account["open_orders"], [])


class TraderFactoryPaperFlagTest(unittest.TestCase):
    def test_paper_flag_returns_simulation_trader(self):
        trader = TraderFactory.create("UPB", budget=500000, currency="BTC", paper=True)

        self.assertIsInstance(trader, SimulationTrader)
        self.assertEqual(trader.balance, 500000)

    def test_paper_flag_overrides_exchange_code(self):
        trader = TraderFactory.create("BTH", budget=300000, currency="ETH", paper=True)

        self.assertIsInstance(trader, SimulationTrader)
        self.assertEqual(trader.currency, "ETH")


class SimulationTraderCapabilityTest(unittest.TestCase):
    def _trader(self):
        trader = SimulationTrader(budget=500000, currency="BTC")
        trader.update_quote("BTC", 50000)
        return trader

    def test_market_buy_fills_at_current_quote(self):
        trader = self._trader()
        results = []
        trader.send_request([{
            "id": "m1", "type": "buy", "price": 0, "amount": 0.01,
            "ord_type": "market", "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "done")
        self.assertEqual(results[0]["price"], 50000)

    def test_unknown_ord_type_is_rejected(self):
        trader = self._trader()
        results = []
        trader.send_request([{
            "id": "x1", "type": "buy", "price": 50000, "amount": 0.01,
            "ord_type": "banana", "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "failed")
        self.assertIn("banana", results[0]["msg"])
        self.assertEqual(trader.balance, 500000)  # 잔고 변화 없음

    def test_legacy_buy_without_ord_type_still_fills(self):
        trader = self._trader()
        results = []
        trader.send_request([{
            "id": "b1", "type": "buy", "price": 50000, "amount": 0.01,
            "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "done")


class SimulationTraderValidationTest(unittest.TestCase):
    def setUp(self):
        self.trader = SimulationTrader(budget=100000, currency="BTC")
        self.trader.update_quote("BTC", 50000)

    def _send_one(self, request):
        results = []
        self.trader.send_request([request], results.append)
        self.assertEqual(len(results), 1)
        return results[0]

    def _assert_rejected(self, request, message):
        result = self._send_one(request)
        self.assertEqual(result["state"], "failed")
        self.assertEqual(result["msg"], message)
        self.assertEqual(result["fee"], 0)

    def test_rejects_invalid_order_ids(self):
        invalid_requests = [
            ("none", {"id": None}),
            ("missing", {}),
            ("empty", {"id": ""}),
            ("whitespace", {"id": "   "}),
            ("non_string", {"id": 123}),
        ]
        for name, request_id in invalid_requests:
            with self.subTest(name=name):
                request = {
                    "type": "buy", "price": 1, "amount": 0.01,
                    "ord_type": "market",
                }
                request.update(request_id)
                self._assert_rejected(request, "잘못된 주문 ID")

    def test_rejects_nonpositive_or_nonfinite_amount(self):
        for amount in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(amount=amount):
                self._assert_rejected({
                    "id": "amount", "type": "buy", "price": 1,
                    "amount": amount, "ord_type": "market",
                }, "잘못된 수량")

    def test_rejects_nonpositive_or_nonfinite_limit_price(self):
        for price in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(price=price):
                self._assert_rejected({
                    "id": "price", "type": "buy", "price": price,
                    "amount": 0.01, "ord_type": "limit",
                }, "잘못된 가격")

    def test_rejects_nonpositive_or_nonfinite_conditional_trigger(self):
        for trigger in (0, -1, float("nan"), float("inf"), True):
            with self.subTest(trigger=trigger):
                self._assert_rejected({
                    "id": "trigger", "type": "sell", "price": 0,
                    "amount": 0.01, "ord_type": "stop_loss", "trigger": trigger,
                }, "잘못된 트리거")

    def test_rejects_oco_before_other_request_details(self):
        self._assert_rejected({"ord_type": "oco"}, "지원하지 않는 주문 유형: oco")

    def test_market_buy_without_quote_is_recorded_as_terminal_failure(self):
        trader = SimulationTrader(budget=100000, currency="BTC")
        results = []
        trader.send_request([{
            "id": "market-no-quote", "type": "buy", "price": 0,
            "amount": 0.01, "ord_type": "market",
        }], results.append)
        self.assertEqual(results[0]["state"], "failed")
        self.assertEqual(results[0]["msg"], "시세 없음")
        self.assertEqual(results[0]["fee"], 0)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["state"], "failed")

    def test_invalid_quote_does_not_replace_or_evaluate_conditionals(self):
        results = []
        self.trader.send_request([{
            "id": "stop", "type": "sell", "price": 0, "amount": 0.01,
            "ord_type": "stop_loss", "trigger": 49000,
        }], results.append)
        for price in (0, -1, float("nan"), float("inf")):
            with self.subTest(price=price):
                self.trader.update_quote("BTC", price)
                self.assertEqual(self.trader.quotes["BTC"], 50000)
                self.assertEqual(len(self.trader.pending_conditionals), 1)
                self.assertEqual(len(results), 1)

    def test_commission_ratio_is_ignored_for_balance_and_results(self):
        trader = SimulationTrader(
            budget=100000, currency="BTC", commission_ratio=0.25)
        trader.update_quote("BTC", 50000)
        result = []
        trader.send_request([{
            "id": "zero-fee", "type": "buy", "price": 1, "amount": 0.01,
            "ord_type": "market",
        }], result.append)
        self.assertEqual(result[0]["fee"], 0)
        self.assertEqual(trader.balance, 99500)

    def test_terminal_history_keeps_independent_request_copy(self):
        request = {
            "id": "copy", "type": "buy", "price": 1, "amount": 0.01,
            "ord_type": "market", "metadata": {"marker": "original"},
        }
        results = []
        self.trader.send_request([request], results.append)

        request["metadata"]["marker"] = "mutated request"
        results[0]["request"]["metadata"]["marker"] = "mutated callback"

        self.assertEqual(
            self.trader.order_history[0]["request"]["metadata"]["marker"],
            "original",
        )


class SimulationTraderConditionalTest(unittest.TestCase):
    def _holding_trader(self):
        # BTC 1개를 50000에 보유한 상태로 세팅
        trader = SimulationTrader(budget=1000000, currency="BTC")
        trader.update_quote("BTC", 50000)
        trader.send_request([{
            "id": "buy", "type": "buy", "price": 50000, "amount": 1.0,
            "date_time": "2026-07-03T12:00:00",
        }], lambda r: None)
        return trader

    def test_stop_loss_registered_returns_requested(self):
        trader = self._holding_trader()
        results = []
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
            "date_time": "2026-07-03T12:00:00",
        }], results.append)
        self.assertEqual(results[0]["state"], "requested")
        self.assertEqual(len(trader.pending_conditionals), 1)

    def test_stop_loss_fires_when_price_drops_to_trigger(self):
        trader = self._holding_trader()
        results = []
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
        }], results.append)
        trader.update_quote("BTC", 47000)  # 트리거 도달
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["type"], "sell")
        self.assertEqual(results[-1]["price"], 47000)
        self.assertNotIn("BTC", trader.assets)  # 전량 매도
        self.assertEqual(len(trader.pending_conditionals), 0)

    def test_stop_loss_does_not_fire_above_trigger(self):
        trader = self._holding_trader()
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
        }], lambda r: None)
        trader.update_quote("BTC", 48000)  # 아직 트리거 위
        self.assertEqual(len(trader.pending_conditionals), 1)

    def test_take_profit_fires_when_price_rises_to_trigger(self):
        trader = self._holding_trader()
        results = []
        trader.send_request([{
            "id": "tp", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "take_profit", "trigger": 55000,
        }], results.append)
        trader.update_quote("BTC", 55000)
        self.assertEqual(results[-1]["state"], "done")
        self.assertEqual(results[-1]["price"], 55000)
        self.assertEqual(len(trader.pending_conditionals), 0)

    def test_cancel_removes_pending_conditional(self):
        trader = self._holding_trader()
        trader.send_request([{
            "id": "sl", "type": "sell", "price": 0, "amount": 1.0,
            "ord_type": "stop_loss", "trigger": 47000,
        }], lambda r: None)
        trader.cancel_request("sl")
        self.assertEqual(len(trader.pending_conditionals), 0)
        trader.update_quote("BTC", 47000)  # 취소되었으므로 발동 안 함
        self.assertIn("BTC", trader.assets)  # 여전히 보유 (매도 안 됨)


if __name__ == "__main__":
    unittest.main()
