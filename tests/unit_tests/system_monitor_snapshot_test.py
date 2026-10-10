"""Point-in-time monitoring regressions using synthetic, offline payloads."""

import copy
from decimal import Decimal
import unittest
from unittest.mock import patch

from smtm.analyzer import Analyzer
from smtm.llm.llm_client import ToolCall
from smtm.llm.system_monitor import SystemMonitor
from smtm.llm.tool import Tool, ToolResult
from smtm.llm.tool_router import ToolRouter
from smtm.llm.tools.trade_history_tool import TradeHistoryTool


class SystemMonitorSnapshotTests(unittest.TestCase):
    """Capture and read boundaries must not expose mutable record aliases."""

    def setUp(self):
        self.monitor = SystemMonitor()
        self.clock = patch.object(self.monitor, "_timestamp", return_value="2026-01-02T03:04:05")
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def _capture_cases(self, payload):
        return (
            ("market_data_log", "data", lambda: self.monitor.log_market_data([payload], session="s1")),
            ("trade_request_log", "request", lambda: self.monitor.log_trade_request(payload, session="s1")),
            ("trade_result_log", "result", lambda: self.monitor.log_trade_result(payload, session="s1")),
            ("tool_call_log", "arguments", lambda: self.monitor.log_tool_call("tool", payload, {})),
            ("tool_call_log", "result", lambda: self.monitor.log_tool_call("tool", {}, payload)),
            ("llm_interaction_log", "request", lambda: self.monitor.log_llm_interaction(payload, "reply", {})),
            ("llm_interaction_log", "usage", lambda: self.monitor.log_llm_interaction({}, "reply", payload)),
            ("safety_event_log", "event", lambda: self.monitor.log_safety_event(payload, session="s1")),
            ("snapshots", "portfolio", lambda: self.monitor.take_snapshot(payload)),
        )

    def test_every_payload_is_detached_at_capture(self):
        for index in range(9):
            payload = {"nested": {"values": [1, {"value": 2}]}}
            attribute, field, capture = self._capture_cases(payload)[index]
            with self.subTest(attribute=attribute, field=field):
                capture()
                record = getattr(self.monitor, attribute)[-1]
                expected = copy.deepcopy(record)
                payload["nested"]["values"][1]["value"] = 99
                payload["nested"]["values"].append(3)
                payload["added"] = True
                self.assertEqual(record, expected)

    def test_reused_payload_produces_independent_records(self):
        for index in range(9):
            payload = {"nested": [1]}
            attribute, field, capture = self._capture_cases(payload)[index]
            with self.subTest(attribute=attribute, field=field):
                capture()
                first = getattr(self.monitor, attribute)[-1]
                expected = copy.deepcopy(first)
                payload["nested"].append(2)
                capture()
                second = getattr(self.monitor, attribute)[-1]
                self.assertEqual(first, expected)
                self.assertNotEqual(first[field], second[field])
                payload.clear()
                value = second[field][0] if field == "data" else second[field]
                self.assertEqual(value, {"nested": [1, 2]})

    def test_market_data_outer_list_is_also_detached(self):
        data = [{"price": 10}]
        self.monitor.log_market_data(data)
        data.clear()
        self.assertEqual(self.monitor.market_data_log[0]["data"], [{"price": 10}])

    def test_llm_request_and_usage_capture_preserves_totals(self):
        request = {"messages": [{"role": "user", "content": [{"text": "original"}]}]}
        usage = {"input_tokens": 12, "output_tokens": 3}
        self.monitor.log_llm_interaction(request, "reply", usage)
        usage.update(input_tokens=99, output_tokens=100)
        request["messages"][0]["content"][0]["text"] = "changed"
        self.monitor.log_llm_interaction({}, "empty usage", {})
        self.assertEqual(self.monitor.get_llm_usage(), {
            "total_input_tokens": 12, "total_output_tokens": 3, "call_count": 2,
        })
        self.assertEqual(self.monitor.llm_interaction_log[0]["request"]["messages"][0]
                         ["content"][0]["text"], "original")

    def test_tool_arguments_and_result_are_both_detached(self):
        shared = {"values": [1]}
        arguments = {"input": shared}
        result = {"output": shared}
        self.monitor.log_tool_call("tool", arguments, result)
        shared["values"].append(2)
        arguments.clear()
        result.clear()
        record = self.monitor.tool_call_log[0]
        self.assertEqual(record, {
            "timestamp": "2026-01-02T03:04:05", "tool_name": "tool",
            "arguments": {"input": {"values": [1]}},
            "result": {"output": {"values": [1]}},
        })

    def test_trade_history_reads_do_not_expose_stored_records(self):
        for session in (None, "s1", "s2"):
            with self.subTest(session=session):
                monitor = SystemMonitor()
                for name, number in (("s1", 1), ("s2", 2), ("s1", 3)):
                    monitor.log_trade_result({"nested": [number]}, session=name)
                expected = copy.deepcopy(monitor.trade_result_log)
                returned = monitor.get_trade_log(session=session)
                returned[0]["result"]["nested"].append(99)
                returned[0]["session"] = "changed"
                returned.reverse()
                returned.append({"fake": True})
                returned.clear()
                self.assertEqual(monitor.trade_result_log, expected)
                self.assertEqual(monitor.get_trade_log(), expected)

    def test_snapshot_reads_do_not_expose_stored_records(self):
        self.monitor.take_snapshot({"asset": {"BTC": (Decimal("10.25"), [2])}})
        expected = copy.deepcopy(self.monitor.snapshots)
        first = self.monitor.get_snapshots()
        first[0]["portfolio"]["asset"]["BTC"][1].append(3)
        first[0]["timestamp"] = "changed"
        first.clear()
        self.assertEqual(self.monitor.get_snapshots(), expected)

    def test_repeated_reads_are_independent(self):
        self.monitor.log_trade_result({"nested": [1]})
        self.monitor.take_snapshot({"nested": [1]})
        for getter, field in ((self.monitor.get_trade_log, "result"),
                              (self.monitor.get_snapshots, "portfolio")):
            with self.subTest(field=field):
                first, second = getter(), getter()
                first[0][field]["nested"].append(2)
                self.assertEqual(second[0][field]["nested"], [1])
                self.assertEqual(getter(), second)

    def test_empty_reads_do_not_mutate_monitor(self):
        for getter in (self.monitor.get_trade_log, self.monitor.get_snapshots):
            with self.subTest(getter=getter.__name__):
                result = getter()
                result.append({"fake": True})
                self.assertEqual(getter(), [])

    def test_session_filter_and_order_remain_unchanged(self):
        for session, number in (("s1", 1), (None, 2), ("s2", 3), ("s1", 4)):
            self.monitor.log_trade_result({"n": number}, session=session)
        self.assertEqual([r["result"]["n"] for r in self.monitor.get_trade_log()], [1, 2, 3, 4])
        self.assertEqual([r["result"]["n"] for r in self.monitor.get_trade_log(session="s1")], [1, 4])
        self.assertEqual(self.monitor.get_trade_log(session="missing"), [])

    def test_record_shapes_timestamps_and_python_values_are_preserved(self):
        portfolio = {"asset": {"BTC": (Decimal("10.25"), 2)}}
        self.monitor.take_snapshot(portfolio)
        self.monitor.log_trade_result({"price": Decimal("10.25")}, session="s1")
        self.assertEqual(self.monitor.get_snapshots(), [{
            "timestamp": "2026-01-02T03:04:05", "portfolio": portfolio,
        }])
        self.assertIsInstance(self.monitor.get_snapshots()[0]["portfolio"]["asset"]["BTC"], tuple)
        self.assertEqual(self.monitor.get_trade_log(), [{
            "timestamp": "2026-01-02T03:04:05", "session": "s1",
            "result": {"price": Decimal("10.25")},
        }])

    def test_time_arguments_keep_existing_no_filter_behavior(self):
        self.monitor.log_trade_result({"n": 1}, session="s1")
        self.monitor.take_snapshot({"n": 1})
        self.assertEqual(self.monitor.get_trade_log("future", "past", "s1"),
                         self.monitor.get_trade_log(session="s1"))
        self.assertEqual(self.monitor.get_snapshots("future", "past"), self.monitor.get_snapshots())

    def test_analyzer_forwarded_records_are_detached(self):
        analyzer = Analyzer(self.monitor, session_name="s1")
        payload = {"nested": [1]}
        analyzer.put_trading_info([payload])
        analyzer.put_requests([payload])
        analyzer.put_result(payload)
        analyzer.put_safety_event(payload)
        payload["nested"].append(2)
        for attribute, field in (("market_data_log", "data"), ("trade_request_log", "request"),
                                 ("trade_result_log", "result"), ("safety_event_log", "event")):
            with self.subTest(attribute=attribute):
                record = getattr(self.monitor, attribute)[0]
                value = record[field][0] if field == "data" else record[field]
                self.assertEqual(value, {"nested": [1]})
                self.assertEqual(record["session"], "s1")

    def test_router_result_mutation_does_not_rewrite_monitor(self):
        class EchoTool(Tool):
            """Return ordinary structured data without any external work."""
            name = "echo"

            def execute(self, arguments):
                return ToolResult(success=True, data={"nested": arguments["nested"]})

        router = ToolRouter(self.monitor)
        router.register(EchoTool())
        arguments = {"nested": [1]}
        result = router.execute(ToolCall(id="call1", name="echo", arguments=arguments))
        result.data["nested"].append(2)
        arguments.clear()
        self.assertEqual(self.monitor.tool_call_log[0]["arguments"], {"nested": [1]})
        self.assertEqual(self.monitor.tool_call_log[0]["result"], {"nested": [1]})

    def test_trade_history_tool_returns_detached_records(self):
        self.monitor.log_trade_result({"nested": [1]}, session="s1")
        tool = TradeHistoryTool(self.monitor)
        result = tool.execute({"count": 1, "session": "s1"})
        self.assertTrue(result.success)
        result.data[0]["result"]["nested"].append(2)
        self.assertEqual(tool.execute({"count": 1, "session": "s1"}).data[0]
                         ["result"]["nested"], [1])
