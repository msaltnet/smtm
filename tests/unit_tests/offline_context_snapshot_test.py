"""Offline characterization of today's chat and strategy context boundaries.

These tests do not prescribe a future strategy prompt policy. No session starts.
"""
import ast
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from smtm.llm.llm_client import LlmResponse, ToolCall
from smtm.llm.system_operator import SystemOperator
from smtm.llm.tools.market_data_tool import MarketDataTool
from smtm.strategy.strategy_llm import StrategyLlm
from tests.e2e_tests.fake_llm_client import (
    FakeDataProvider, FakeLlmClient, FakeSnapshotDataProvider,
)


def mixed_snapshot():
    """Return fresh synthetic values, deliberately putting news before a candle."""
    return [
        {"type": "news", "title": "synthetic-news-marker",
         "summary": "fixture only", "source": "fixture",
         "metadata": {"tags": ["synthetic"]}},
        {"type": "primary_candle", "market": "BTC",
         "date_time": "2026-10-13T00:00:00", "opening_price": 50000,
         "high_price": 51000, "low_price": 49000, "closing_price": 50000,
         "acc_price": 1000000, "acc_volume": 20},
        {"type": "funding_rate", "source": "synthetic-funding-marker",
         "funding_rate": 0.0001},
        {"type": "sentiment_index", "source": "synthetic-sentiment-marker",
         "value": 45},
    ]


class SnapshotProviderTests(unittest.TestCase):
    """Replay complete per-call snapshots without borrowing mutable fixtures."""

    def test_mixed_items_are_returned_together_in_order(self):
        """Keep every item from a mixed snapshot in its original position."""
        snapshot = mixed_snapshot()
        provider = FakeSnapshotDataProvider([snapshot])
        self.assertEqual(provider.get_info(), snapshot)
        self.assertEqual(provider.call_count, 1)

    def test_empty_snapshot_is_not_replaced_with_a_default_candle(self):
        """Explicit empty snapshots remain empty, including after exhaustion."""
        provider = FakeSnapshotDataProvider([[]])
        self.assertEqual(provider.get_info(), [])
        self.assertEqual(provider.get_info(), [])
        self.assertEqual(provider.call_count, 2)

    def test_sequence_preserves_empty_slots_and_repeats_last_snapshot(self):
        """Advance through complete snapshots without skipping empty slots."""
        first = mixed_snapshot()
        last = [{"type": "news", "title": "last-snapshot"}]
        provider = FakeSnapshotDataProvider([first, [], last])
        self.assertEqual([provider.get_info() for _ in range(4)],
                         [first, [], last, last])
        self.assertEqual(provider.call_count, 4)

    def test_empty_timeline_always_returns_empty(self):
        """An empty timeline has no implicit market-data fallback."""
        provider = FakeSnapshotDataProvider([])
        self.assertEqual([provider.get_info() for _ in range(3)], [[], [], []])

    def test_constructor_detaches_nested_input_and_timeline(self):
        """Caller mutation cannot rewrite either stored replay position."""
        snapshot = mixed_snapshot()
        expected = copy.deepcopy(snapshot)
        timeline = [snapshot, snapshot]
        provider = FakeSnapshotDataProvider(timeline)
        snapshot[0]["metadata"]["tags"].append("changed")
        snapshot.reverse()
        timeline.clear()
        self.assertEqual(provider.get_info(), expected)
        self.assertEqual(provider.get_info(), expected)

    def test_returned_snapshots_are_deeply_detached_from_future_reads(self):
        """Nested mutations of one read cannot contaminate later reads."""
        snapshot = mixed_snapshot()
        provider = FakeSnapshotDataProvider([snapshot, snapshot])
        first = provider.get_info()
        first[0]["metadata"]["tags"].append("changed")
        first.pop()
        second = provider.get_info()
        self.assertEqual(second, snapshot)
        second[0]["metadata"]["tags"].clear()
        self.assertEqual(provider.get_info(), snapshot)

    def test_flat_or_malformed_timelines_fail_explicitly(self):
        """Reject ambiguous flat input and malformed snapshot containers."""
        for value in (None, {}, "bad", mixed_snapshot(), [None], [[None]], [[1]]):
            with self.subTest(value=value):
                with self.assertRaises(TypeError):
                    FakeSnapshotDataProvider(value)


class LegacyProviderCompatibilityTests(unittest.TestCase):
    """Snapshot support must not reinterpret the existing candle fake API."""

    def test_default_and_legacy_empty_constructor_keep_the_default_candle(self):
        """Preserve both legacy paths that select the default candle."""
        for provider in (FakeDataProvider(), FakeDataProvider([])):
            self.assertEqual(provider.get_info(), [FakeDataProvider._default_candle()])

    def test_existing_sequence_advances_one_candle_and_repeats_last(self):
        """Preserve legacy single-candle sequencing and exhaustion."""
        first = {"type": "primary_candle", "closing_price": 1}
        last = {"type": "primary_candle", "closing_price": 2}
        provider = FakeDataProvider([first, last])
        self.assertEqual([provider.get_info() for _ in range(3)],
                         [[first], [last], [last]])
        self.assertEqual(provider.call_count, 3)

    def test_existing_set_candles_and_empty_set_behavior_is_preserved(self):
        """Legacy replacement keeps its call index and accepts an empty set."""
        provider = FakeDataProvider()
        provider.get_info()
        replacement = [{"closing_price": 10}, {"closing_price": 20}]
        provider.set_candles(replacement)
        self.assertEqual(provider.get_info(), [replacement[-1]])
        provider.set_candles([])
        self.assertEqual(provider.get_info(), [])


class FakeLlmCaptureTests(unittest.TestCase):
    """Call logs describe arguments at each call, not their later mutations."""

    def test_call_log_detaches_messages_tools_and_tool_choice(self):
        """Record nested arguments as they were when the fake was called."""
        client = FakeLlmClient()
        messages = [{"role": "user", "content": [{"text": "original"}]}]
        tools = [{"name": "fixture", "input_schema": {"required": ["x"]}}]
        choice = {"type": "tool", "name": "fixture"}
        expected = copy.deepcopy((messages, tools, choice))
        client.create_message("system", messages, tools, choice)
        messages[0]["content"][0]["text"] = "changed"
        tools[0]["input_schema"]["required"].append("y")
        choice["name"] = "changed"
        record = client.call_log[0]
        self.assertEqual((record["messages"], record["tools"], record["tool_choice"]),
                         expected)


class OfflineContextRouteTests(unittest.TestCase):
    """Use the real chat/tool and strategy consumers with synthetic boundaries."""

    @staticmethod
    def make_chat_operator(provider, responses):
        """Register only the read-only market tool; never assemble/start a session."""
        client = FakeLlmClient(responses)
        operator = SystemOperator(client, {})
        manager = Mock()
        manager.list_sessions.return_value = []
        manager.get_session.return_value = SimpleNamespace(
            operator=SimpleNamespace(data_provider=provider))
        operator.session_manager = manager
        operator.tool_router.register(MarketDataTool(manager))
        return operator, client, manager

    @staticmethod
    def chat_responses(tool_id):
        """One market lookup followed by a final text response."""
        return [
            LlmResponse("", tool_calls=[ToolCall(
                tool_id, "get_market_data", {"session": "fixture"})]),
            LlmResponse("synthetic complete"),
        ]

    def assert_tool_snapshot(self, client, call_index, expected, tool_id):
        """Inspect the next model request, not only the tool's own return value."""
        messages = client.call_log[call_index]["messages"]
        block = messages[-1]["content"][0]
        self.assertEqual(block["type"], "tool_result")
        self.assertEqual(block["tool_use_id"], tool_id)
        self.assertEqual(ast.literal_eval(block["content"]), {"result": expected})

    def test_chat_receives_all_mixed_items_through_real_tool_and_router(self):
        """Observe the complete tool result in the following model request."""
        snapshot = mixed_snapshot()
        provider = FakeSnapshotDataProvider([snapshot])
        operator, client, manager = self.make_chat_operator(
            provider, self.chat_responses("market-1"))
        self.assertEqual(operator.chat("read synthetic context"), "synthetic complete")
        self.assertEqual(len(client.call_log), 2)
        self.assertEqual(len(client.call_log[0]["messages"]), 1)
        self.assertEqual(len(client.call_log[1]["messages"]), 3)
        self.assert_tool_snapshot(client, 1, snapshot, "market-1")
        manager.get_session.assert_called_once_with("fixture")
        self.assertEqual(provider.call_count, 1)
        self.assertEqual(operator.system_monitor.tool_call_log[0]["result"],
                         {"result": snapshot})

    def test_chat_keeps_successive_mixed_and_empty_snapshots_separate(self):
        """A later empty tool result cannot rewrite an earlier captured call."""
        first = mixed_snapshot()
        provider = FakeSnapshotDataProvider([first, []])
        operator, client, _ = self.make_chat_operator(
            provider, self.chat_responses("market-1") + self.chat_responses("market-2"))
        operator.chat("first snapshot")
        first_call = copy.deepcopy(client.call_log[1])
        operator.chat("second snapshot")
        self.assertEqual(len(client.call_log), 4)
        self.assert_tool_snapshot(client, 1, first, "market-1")
        self.assert_tool_snapshot(client, 3, [], "market-2")
        self.assertEqual(client.call_log[1], first_call)
        self.assertEqual(provider.call_count, 2)

    @staticmethod
    def make_hold_strategy():
        """Standalone real strategy with one scripted hold, no trader or timer."""
        client = FakeLlmClient([LlmResponse("", tool_calls=[ToolCall(
            "decision-1", "submit_decision", {"action": "hold", "reason": "fixture"})])])
        strategy = StrategyLlm(llm_client=client)
        strategy.initialize(500000)
        return strategy, client

    def test_strategy_currently_uses_only_first_primary_candle_and_holds(self):
        """Characterize the current prompt boundary with one order-free hold."""
        snapshot = mixed_snapshot()
        later_candle = {**snapshot[1], "closing_price": 77777,
                        "date_time": "2026-10-13T00:01:00"}
        snapshot.append(later_candle)
        strategy, client = self.make_hold_strategy()
        strategy.update_trading_info(FakeSnapshotDataProvider([snapshot]).get_info())
        before = (strategy.balance, strategy.asset_amount,
                  copy.deepcopy(strategy.waiting_requests))
        self.assertIsNone(strategy.get_request())
        self.assertEqual(len(client.call_log), 1)
        record = client.call_log[0]
        self.assertEqual(record["tool_choice"],
                         {"type": "tool", "name": "submit_decision"})
        self.assertEqual([tool["name"] for tool in record["tools"]], ["submit_decision"])
        self.assertEqual(strategy.data, [snapshot[1]])
        prompt = record["messages"][0]["content"]
        self.assertIn(str(snapshot[1]), prompt)
        for marker in ("synthetic-news-marker", "synthetic-funding-marker",
                       "synthetic-sentiment-marker", "77777"):
            self.assertNotIn(marker, prompt)
        self.assertEqual((strategy.balance, strategy.asset_amount,
                          strategy.waiting_requests), before)

    def test_fresh_strategy_with_empty_or_non_candle_snapshot_makes_no_call(self):
        """A fresh strategy needs a primary candle before requesting a decision."""
        for snapshot in ([], [mixed_snapshot()[0]]):
            with self.subTest(snapshot=snapshot):
                strategy, client = self.make_hold_strategy()
                strategy.update_trading_info(FakeSnapshotDataProvider([snapshot]).get_info())
                self.assertIsNone(strategy.get_request())
                self.assertEqual(client.call_log, [])
                self.assertEqual(strategy.data, [])

    def test_empty_snapshot_after_candle_preserves_current_strategy_history(self):
        """Characterize existing history retention without promising freshness."""
        snapshot = mixed_snapshot()
        provider = FakeSnapshotDataProvider([snapshot, []])
        strategy, client = self.make_hold_strategy()
        strategy.update_trading_info(provider.get_info())
        strategy.update_trading_info(provider.get_info())
        self.assertEqual(strategy.data, [snapshot[1]])
        self.assertIsNone(strategy.get_request())
        self.assertEqual(len(client.call_log), 1)
