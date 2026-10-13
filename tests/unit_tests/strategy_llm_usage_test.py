"""Offline strategy-usage regression coverage; no trading session is started."""
import copy
import unittest
from unittest.mock import Mock, patch

from smtm.llm.llm_client import LlmResponse, ToolCall
from smtm.llm.system_monitor import SystemMonitor
from smtm.llm.system_operator import SystemOperator
from smtm.session_manager import SessionManager
from smtm.strategy.strategy_factory import StrategyFactory
from smtm.strategy.strategy_llm import StrategyLlm


CANDLE = {
    "type": "primary_candle", "market": "BTC", "date_time": "2026-10-11T00:00:00",
    "opening_price": 50000, "high_price": 51000, "low_price": 49000,
    "closing_price": 50000, "acc_price": 1000000, "acc_volume": 20,
}
PROFILE = {
    "exchange": "UPB", "currency": "BTC", "budget": 500000,
    "virtual": True, "strategy": "LLM", "term": 60,
}


def response(action="hold", usage=None, **decision):
    """Make one normalized fake response with optional decision overrides."""
    return LlmResponse(
        text="synthetic decision text",
        tool_calls=[ToolCall("decision-1", "submit_decision", {
            "action": action, "reason": "synthetic reason", **decision,
        })],
        usage={"input_tokens": 11, "output_tokens": 7} if usage is None else usage,
    )


class StrategyUsageTests(unittest.TestCase):
    """Exercise real assembly, strategy decisions, and monitor aggregation."""

    def setUp(self):
        """Substitute only market/trader boundaries; keep sessions stopped."""
        self.client = Mock()
        self.client.create_message.return_value = response()
        self.monitor = SystemMonitor()
        self.manager = SessionManager(llm_client=self.client, system_monitor=self.monitor)
        self.traders = []

        def make_trader(*args, **kwargs):
            trader = Mock()
            trader.get_account_info.return_value = {"balance": 500000, "asset": {}}
            self.traders.append(trader)
            return trader

        for target, kwargs in (
            ("smtm.data.data_provider_factory.DataProviderFactory.create",
             {"return_value": Mock()}),
            ("smtm.trader.trader_factory.TraderFactory.create",
             {"side_effect": make_trader}),
        ):
            patcher = patch(target, **kwargs)
            patcher.start()
            self.addCleanup(patcher.stop)

    def make_strategy(self, name="alpha", code="LLM", candles=True):
        """Assemble a stopped synthetic session and return its strategy."""
        result = self.manager.create_session({**PROFILE, "strategy": code}, name=name)
        self.assertTrue(result["success"], result)
        strategy = self.manager.get_session(name).operator.strategy
        if candles:
            strategy.update_trading_info([CANDLE])
        return strategy

    def assert_usage(self, calls, input_tokens, output_tokens, monitor=None):
        """Check the unchanged public usage keys and exact totals."""
        self.assertEqual((monitor or self.monitor).get_llm_usage(), {
            "call_count": calls, "total_input_tokens": input_tokens,
            "total_output_tokens": output_tokens,
        })

    def test_session_hold_response_is_counted_once_without_prompt_or_decision_text(self):
        """The original missing-usage bug reproduces through real assembly."""
        strategy = self.make_strategy()
        self.assertIsNone(strategy.get_request())
        self.client.create_message.assert_called_once()
        self.assert_usage(1, 11, 7)
        record = self.monitor.llm_interaction_log[0]
        self.assertEqual(record["request"], {"source": "strategy", "session": "alpha"})
        self.assertEqual(record["response_text"], "")
        self.assertEqual(record["usage"], {"input_tokens": 11, "output_tokens": 7})
        self.assertIs(strategy.llm_client, self.client)
        self.traders[0].send_request.assert_not_called()

    def test_invalid_or_missing_decisions_count_without_orders_or_cancellations(self):
        """Rejected paid responses still count and preserve waiting orders."""
        strategy = self.make_strategy()
        strategy.waiting_requests = {"pending": {"state": "requested"}}
        before = copy.deepcopy(strategy.waiting_requests)
        responses = [
            LlmResponse(text="no tool", usage={"input_tokens": 11, "output_tokens": 7}),
            response("unknown"), response("buy", price="bad", amount=1),
            response("sell", price=50000, amount=1),
        ]
        for index, item in enumerate(responses, 1):
            with self.subTest(index=index):
                self.client.create_message.return_value = item
                self.assertIsNone(strategy.get_request())
                self.assertEqual(strategy.waiting_requests, before)
                self.assert_usage(index, index * 11, index * 7)
        self.assertEqual(self.client.create_message.call_count, len(responses))
        self.traders[0].send_request.assert_not_called()

    def test_two_sessions_and_replacement_keep_session_and_monitor_attribution(self):
        """A callback captures its session name and monitor at assembly."""
        first = self.make_strategy("alpha")
        second = self.make_strategy("beta")
        first.get_request()
        second.get_request()
        self.assertTrue(self.manager.replace_session("alpha", PROFILE)["success"])
        replacement = self.manager.get_session("alpha").operator.strategy
        self.assertIsNot(first, replacement)
        replacement.update_trading_info([CANDLE])
        replacement.get_request()
        other_monitor = SystemMonitor()
        self.manager.system_monitor = other_monitor
        first.get_request()
        third = self.make_strategy("gamma")
        third.get_request()
        self.assertEqual([r["request"]["session"] for r in self.monitor.llm_interaction_log],
                         ["alpha", "beta", "alpha", "alpha"])
        self.assert_usage(4, 44, 28)
        self.assert_usage(1, 11, 7, other_monitor)
        self.assertEqual(other_monitor.llm_interaction_log[0]["request"]["session"], "gamma")

    def test_chat_and_strategy_responses_share_totals_without_double_counting(self):
        """The same client is logged once by each caller's own boundary."""
        operator = SystemOperator(self.client, {})
        operator.system_monitor = self.monitor
        operator.session_manager = self.manager
        strategy = self.make_strategy()
        self.client.create_message.side_effect = [
            LlmResponse("first chat", usage={"input_tokens": 3, "output_tokens": 2}),
            response(),
            LlmResponse("second chat", usage={"input_tokens": 5, "output_tokens": 4}),
        ]
        self.assertEqual(operator.chat("hello"), "first chat")
        self.assertIsNone(strategy.get_request())
        self.assertEqual(operator.chat("status"), "second chat")
        self.assertEqual(self.client.create_message.call_count, 3)
        self.assert_usage(3, 19, 13)
        self.assertEqual(operator.get_status()["llm_usage"], self.monitor.get_llm_usage())
        self.assertEqual([r["request"].get("source") for r in self.monitor.llm_interaction_log],
                         [None, "strategy", None])

    def test_reused_response_usage_is_a_snapshot_per_returned_call(self):
        """Count calls rather than response identity and detach nested usage."""
        item = response(usage={"input_tokens": 11, "output_tokens": 7, "details": [1]})
        self.client.create_message.return_value = item
        strategy = self.make_strategy()
        strategy.get_request()
        item.usage["input_tokens"] = 20
        item.usage["details"].append(2)
        strategy.get_request()
        item.usage.clear()
        self.assert_usage(2, 31, 14)
        self.assertEqual(self.monitor.llm_interaction_log[0]["usage"]["details"], [1])
        self.assertEqual(self.monitor.llm_interaction_log[1]["usage"]["details"], [1, 2])

    def test_no_data_no_client_and_algorithmic_strategy_add_no_usage(self):
        """No model call means no synthetic strategy usage entry."""
        self.assertIsNone(self.make_strategy(candles=False).get_request())
        self.manager.llm_client = None
        self.assertIsNone(self.make_strategy("no-client").get_request())
        self.manager.llm_client = self.client
        for code in ("BNH", "RSI", "SMA"):
            self.make_strategy(code.lower(), code=code).get_request()
        self.client.create_message.assert_not_called()
        self.assert_usage(0, 0, 0)

    def test_provider_failure_holds_without_invented_usage_or_raw_exception(self):
        """Provider failures disclose no exception payload and invent no usage."""
        strategy = self.make_strategy()
        self.client.create_message.side_effect = RuntimeError("private payload sentinel")
        with self.assertLogs(strategy.logger, "WARNING") as captured:
            self.assertIsNone(strategy.get_request())
        self.assertNotIn("private payload sentinel", " ".join(captured.output))
        self.client.create_message.assert_called_once()
        self.assert_usage(0, 0, 0)

    def test_missing_usage_keys_count_returned_call_without_estimating_tokens(self):
        """Empty or partial normalized usage retains existing total semantics."""
        strategy = self.make_strategy()
        for usage in ({}, {"input_tokens": 4}, {"output_tokens": 3}):
            self.client.create_message.return_value = response(usage=usage)
            self.assertIsNone(strategy.get_request())
        self.assert_usage(3, 4, 3)

    def test_monitor_failure_does_not_change_a_valid_decision_or_retry(self):
        """An unavailable monitor cannot suppress a valid synthetic request."""
        strategy = self.make_strategy()
        self.client.create_message.return_value = response("buy", price=50000, amount=1)
        with patch.object(self.monitor, "log_llm_interaction",
                          side_effect=RuntimeError("private observer sentinel")) as observe:
            with self.assertLogs(strategy.logger, "WARNING") as captured:
                requests = strategy.get_request()
        self.assertEqual(requests[-1]["type"], "buy")
        self.assertEqual(requests[-1]["price"], 50000)
        self.assertEqual(requests[-1]["amount"], 1)
        self.assertNotIn("private observer sentinel", " ".join(captured.output))
        observe.assert_called_once()
        self.client.create_message.assert_called_once()
        self.assert_usage(0, 0, 0)

    def test_session_without_monitor_preserves_standalone_behavior(self):
        """A manager without observation remains a valid construction path."""
        self.manager.system_monitor = None
        strategy = self.make_strategy()
        self.assertIsNone(strategy.get_request())
        self.client.create_message.assert_called_once()
        self.assert_usage(0, 0, 0)


class StrategyUsageObserverTests(unittest.TestCase):
    """Verify the optional observer contract independently of sessions."""

    def make_strategy(self, observer=None, item=None, initialized=True):
        """Build a standalone strategy with a normalized fake response."""
        client = Mock()
        client.create_message.return_value = item or response()
        strategy = StrategyLlm(client, [], usage_observer=observer)
        if initialized:
            strategy.initialize(500000)
            strategy.update_trading_info([CANDLE])
        return strategy, client

    def test_observer_is_optional_for_existing_positional_construction(self):
        """Existing direct and factory calls require no new argument."""
        client = Mock()
        client.create_message.return_value = response()
        for strategy in (StrategyLlm(), StrategyLlm(client, []),
                         StrategyFactory.create("LLM", client)):
            self.assertIsInstance(strategy, StrategyLlm)
        self.assertIsNone(StrategyFactory.create("unknown", client))

    def test_observer_receives_only_detached_usage_before_decision_validation(self):
        """Observer mutation cannot rewrite provider response or trade fields."""
        item = response("buy", price=50000, amount=1)
        item.usage["details"] = {"tokens": [1]}
        observed = []

        def observer(usage):
            observed.append(copy.deepcopy(usage))
            usage["input_tokens"] = 999
            usage["details"]["tokens"].append(2)

        strategy, client = self.make_strategy(observer, item)
        requests = strategy.get_request()
        self.assertEqual(requests[-1]["type"], "buy")
        self.assertEqual(item.usage, {"input_tokens": 11, "output_tokens": 7,
                                    "details": {"tokens": [1]}})
        self.assertEqual(observed, [item.usage])
        client.create_message.assert_called_once()

    def test_failing_observer_keeps_hold_and_valid_sell_unchanged(self):
        """Observer exceptions are isolated for both no-order and order paths."""
        for action in ("hold", "sell"):
            with self.subTest(action=action):
                observer = Mock(side_effect=RuntimeError("observer payload sentinel"))
                strategy, client = self.make_strategy(
                    observer, response(action, price=50000, amount=1))
                strategy.asset_amount = 1
                with self.assertLogs(strategy.logger, "WARNING") as captured:
                    requests = strategy.get_request()
                if action == "hold":
                    self.assertIsNone(requests)
                else:
                    self.assertEqual(requests[-1]["type"], "sell")
                self.assertNotIn("observer payload sentinel", " ".join(captured.output))
                observer.assert_called_once()
                client.create_message.assert_called_once()

    def test_uninitialized_strategy_does_not_call_client_or_observer(self):
        """Initialization remains required even when observation is configured."""
        observer = Mock()
        strategy, client = self.make_strategy(observer, initialized=False)
        self.assertIsNone(strategy.get_request())
        client.create_message.assert_not_called()
        observer.assert_not_called()

    def test_usage_access_or_copy_failure_cannot_suppress_valid_requests(self):
        """Failure preparing observer input is isolated like observer failure."""
        class UncopyableUsage(dict):
            """Synthetic usage whose defensive copy fails."""

            def __deepcopy__(self, memo):
                """Simulate an unsupported value without exposing its payload."""
                raise RuntimeError("private usage sentinel")

        for mode in ("missing", "uncopyable"):
            with self.subTest(mode=mode):
                item = response("buy", price=50000, amount=1)
                if mode == "missing":
                    del item.usage
                else:
                    item.usage = UncopyableUsage(input_tokens=11)
                observer = Mock()
                strategy, client = self.make_strategy(observer, item)
                strategy.waiting_requests = {"pending": {"state": "requested"}}
                with self.assertLogs(strategy.logger, "WARNING") as captured:
                    requests = strategy.get_request()
                self.assertEqual([request["type"] for request in requests], ["cancel", "buy"])
                self.assertEqual(strategy.waiting_requests, {"pending": {"state": "requested"}})
                self.assertEqual(strategy.balance, 500000)
                self.assertNotIn("private usage sentinel", " ".join(captured.output))
                observer.assert_not_called()
                client.create_message.assert_called_once()

    def test_factory_forwards_observer_only_to_llm_strategy(self):
        """Algorithmic strategies remain independent of the observer."""
        observer = Mock()
        client = Mock()
        client.create_message.return_value = response()
        strategy = StrategyFactory.create("LLM", client, usage_observer=observer)
        strategy.initialize(500000)
        strategy.update_trading_info([CANDLE])
        self.assertIsNone(strategy.get_request())
        observer.assert_called_once_with({"input_tokens": 11, "output_tokens": 7})
        for code in ("BNH", "RSI", "SMA", "unknown"):
            StrategyFactory.create(code, client, usage_observer=observer)
        observer.assert_called_once()
