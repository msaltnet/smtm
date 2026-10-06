import copy
import unittest
from unittest.mock import patch
from smtm import StrategyLlm, StrategyFactory
from smtm.llm.llm_client import LlmResponse, ToolCall


class ScriptedLlmClient:
    """지정된 판단을 반환하는 테스트용 클라이언트"""

    def __init__(self, decision=None, raise_error=False):
        self.decision = decision
        self.raise_error = raise_error
        self.call_log = []

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        self.call_log.append({"system_prompt": system_prompt, "messages": messages,
                              "tools": tools, "tool_choice": tool_choice})
        if self.raise_error:
            raise RuntimeError("api error")
        if self.decision is None:
            return LlmResponse(text="no tool call", tool_calls=[])
        return LlmResponse(text="", tool_calls=[
            ToolCall(id="t1", name="submit_decision", arguments=self.decision)
        ])


CANDLE = {
    "type": "primary_candle", "market": "BTC", "date_time": "2026-07-03T12:00:00",
    "opening_price": 50000, "high_price": 51000, "low_price": 49000,
    "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
}


def make_strategy(decision=None, raise_error=False, budget=500000):
    client = ScriptedLlmClient(decision=decision, raise_error=raise_error)
    strategy = StrategyLlm(llm_client=client)
    strategy.initialize(budget)
    strategy.update_trading_info([CANDLE])
    return strategy, client


class StrategyLlmTests(unittest.TestCase):
    def assert_invalid_decision_holds_then_recovers(self, decision, assets=10000):
        strategy, client = make_strategy(decision, budget=500000000)
        strategy.asset_amount = assets
        strategy.is_simulation = True
        strategy.waiting_requests = {
            "waiting-buy": {"request": {"id": "waiting-buy"}, "state": "requested"},
            "waiting-sell": {"request": {"id": "waiting-sell"}, "state": "requested"},
        }
        before = copy.deepcopy((strategy.balance, strategy.asset_amount,
                                strategy.waiting_requests))

        with patch("smtm.strategy.strategy_llm.DateConverter.timestamp_id",
                   return_value="new-order") as timestamp_id:
            self.assertIsNone(strategy.get_request())
            timestamp_id.assert_not_called()
            self.assertEqual(len(client.call_log), 1)
            self.assertEqual((strategy.balance, strategy.asset_amount,
                              strategy.waiting_requests), before)

            client.decision = {"action": "buy", "price": "5e4", "amount": "0.5"}
            requests = strategy.get_request()
            timestamp_id.assert_called_once_with()

        self.assertEqual(len(client.call_log), 2)
        self.assertEqual(requests, [
            {"id": "waiting-buy", "type": "cancel", "price": 0, "amount": 0,
             "date_time": CANDLE["date_time"]},
            {"id": "waiting-sell", "type": "cancel", "price": 0, "amount": 0,
             "date_time": CANDLE["date_time"]},
            {"id": "new-order", "type": "buy", "price": 50000.0, "amount": 0.5,
             "date_time": CANDLE["date_time"]},
        ])
        self.assertEqual((strategy.balance, strategy.asset_amount,
                          strategy.waiting_requests), before)

    def assert_invalid_numeric_values_hold(self, values):
        for action in ("buy", "sell"):
            for field in ("price", "amount"):
                for label, value in values:
                    with self.subTest(action=action, field=field, value=label):
                        # A True price used to become 1.0; amount=5000 ensures
                        # that the existing minimum-buy check cannot mask it.
                        decision = {"action": action, "price": 50000, "amount": 5000}
                        decision[field] = value
                        self.assert_invalid_decision_holds_then_recovers(decision)

    def test_boolean_price_or_amount_holds(self):
        self.assert_invalid_numeric_values_hold([("true", True), ("false", False)])

    def test_non_finite_price_or_amount_holds(self):
        self.assert_invalid_numeric_values_hold([
            ("nan", float("nan")), ("inf", float("inf")), ("-inf", float("-inf")),
            ("string nan", "NaN"), ("string inf", "Infinity"),
            ("string -inf", "-Infinity"), ("string overflow", "1e400"),
        ])

    def test_numeric_conversion_errors_hold(self):
        self.assert_invalid_numeric_values_hold([
            ("integer overflow", 10 ** 400), ("malformed string", "not-a-number"),
            ("list", [1]), ("mapping", {"value": 1}),
        ])

    def test_missing_null_or_non_positive_numbers_still_hold(self):
        self.assert_invalid_numeric_values_hold([
            ("null", None), ("empty string", ""), ("zero", 0), ("negative", -1),
            ("string zero", "0"), ("string negative", "-1"),
        ])
        for action in ("buy", "sell"):
            for field in ("price", "amount"):
                with self.subTest(action=action, missing=field):
                    decision = {"action": action, "price": 50000, "amount": 1}
                    del decision[field]
                    self.assert_invalid_decision_holds_then_recovers(decision)

    def test_finite_operands_with_overflowing_notional_hold(self):
        for action in ("buy", "sell"):
            with self.subTest(action=action):
                self.assert_invalid_decision_holds_then_recovers(
                    {"action": action, "price": 1e308, "amount": 10}, assets=10)

    def test_nan_sell_amount_with_zero_holdings_holds(self):
        self.assert_invalid_decision_holds_then_recovers(
            {"action": "sell", "price": 50000, "amount": float("nan")}, assets=0)

    def test_finite_numeric_inputs_keep_normalized_request_shape(self):
        for action in ("buy", "sell"):
            for price, amount in ((50000, 1), (50000.5, 0.5), ("5e4", "0.5")):
                with self.subTest(action=action, price=price, amount=amount):
                    strategy, client = make_strategy(
                        {"action": action, "price": price, "amount": amount})
                    strategy.asset_amount = 1
                    strategy.is_simulation = True
                    with patch("smtm.strategy.strategy_llm.DateConverter.timestamp_id",
                               return_value="valid-order"):
                        self.assertEqual(strategy.get_request(), [{
                            "id": "valid-order", "type": action,
                            "price": float(price), "amount": float(amount),
                            "date_time": CANDLE["date_time"],
                        }])
                    self.assertEqual(len(client.call_log), 1)

    def test_existing_buy_notional_boundaries_are_preserved(self):
        for price, accepted in ((4999, False), (5000, True),
                                (500000, True), (500001, False)):
            with self.subTest(price=price):
                strategy, client = make_strategy(
                    {"action": "buy", "price": price, "amount": 1})
                self.assertEqual(strategy.get_request() is not None, accepted)
                self.assertEqual(len(client.call_log), 1)

    def test_existing_sell_holdings_and_no_minimum_are_preserved(self):
        for price, amount, accepted in ((50000, 2, True), (50000, 2.01, False),
                                        (1, 1, True), (1e308, 1, True)):
            with self.subTest(price=price, amount=amount):
                strategy, client = make_strategy(
                    {"action": "sell", "price": price, "amount": amount})
                strategy.asset_amount = 2
                self.assertEqual(strategy.get_request() is not None, accepted)
                self.assertEqual(len(client.call_log), 1)

    def test_buy_decision_produces_buy_request(self):
        strategy, client = make_strategy(
            {"action": "buy", "price": 50000, "amount": 0.5,
             "confidence": 0.8, "reason": "상승 추세"})
        requests = strategy.get_request()
        self.assertEqual(requests[-1]["type"], "buy")
        self.assertEqual(requests[-1]["price"], 50000)
        self.assertEqual(requests[-1]["amount"], 0.5)
        # 강제 tool use 확인
        self.assertEqual(client.call_log[0]["tool_choice"],
                         {"type": "tool", "name": "submit_decision"})

    def test_hold_decision_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "hold", "confidence": 0.5, "reason": "관망"})
        self.assertIsNone(strategy.get_request())

    def test_sell_without_position_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "sell", "price": 50000, "amount": 1.0,
             "confidence": 0.9, "reason": "하락"})
        self.assertIsNone(strategy.get_request())  # 보유 수량 0

    def test_buy_exceeding_balance_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "buy", "price": 50000, "amount": 100.0,
             "confidence": 0.9, "reason": "무리한 매수"})
        self.assertIsNone(strategy.get_request())  # 500만 > 잔고 50만

    def test_llm_error_falls_back_to_hold(self):
        strategy, _ = make_strategy(raise_error=True)
        self.assertIsNone(strategy.get_request())

    def test_no_tool_call_falls_back_to_hold(self):
        strategy, _ = make_strategy(decision=None)
        self.assertIsNone(strategy.get_request())

    def test_invalid_action_falls_back_to_hold(self):
        strategy, _ = make_strategy(
            {"action": "yolo", "reason": "?"})
        self.assertIsNone(strategy.get_request())

    def test_update_result_tracks_balance_and_asset(self):
        strategy, _ = make_strategy(
            {"action": "buy", "price": 50000, "amount": 0.5,
             "confidence": 0.8, "reason": "매수"})
        strategy.update_result({
            "request": {"id": "1"}, "type": "buy", "price": 50000, "amount": 0.5,
            "msg": "success", "state": "done", "balance": 475000,
            "date_time": "2026-07-03T12:00:01",
        })
        self.assertLess(strategy.balance, 500000)
        self.assertEqual(strategy.asset_amount, 0.5)

    def test_update_result_uses_zero_fee_from_successful_buy(self):
        strategy = StrategyLlm(llm_client=None)
        strategy.initialize(500000)

        strategy.update_result({
            "request": {"id": "b"}, "type": "buy", "state": "done",
            "msg": "success", "price": 50000, "amount": 2, "fee": 0,
        })

        self.assertEqual(strategy.balance, 400000)

    def test_not_initialized_returns_none(self):
        strategy = StrategyLlm(llm_client=ScriptedLlmClient())
        self.assertIsNone(strategy.get_request())

    def test_factory_creates_llm_strategy_with_client(self):
        client = ScriptedLlmClient()
        strategy = StrategyFactory.create("LLM", llm_client=client)
        self.assertIsInstance(strategy, StrategyLlm)
        self.assertIs(strategy.llm_client, client)
