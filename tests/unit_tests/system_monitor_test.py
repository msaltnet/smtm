import unittest
from smtm.llm.system_monitor import SystemMonitor


class SystemMonitorTests(unittest.TestCase):
    def setUp(self):
        self.monitor = SystemMonitor()

    def test_log_market_data_stores_data(self):
        data = [{"type": "primary_candle", "market": "BTC", "closing_price": 50000}]
        self.monitor.log_market_data(data)
        self.assertEqual(len(self.monitor.market_data_log), 1)

    def test_log_trade_request_stores_request(self):
        request = {"id": "req_1", "type": "buy", "price": 50000, "amount": 0.01}
        self.monitor.log_trade_request(request)
        self.assertEqual(len(self.monitor.trade_request_log), 1)

    def test_log_trade_result_stores_result(self):
        result = {"type": "buy", "price": 50000, "amount": 0.01, "state": "done"}
        self.monitor.log_trade_result(result)
        self.assertEqual(len(self.monitor.trade_result_log), 1)

    def test_log_tool_call_stores_call_and_result(self):
        self.monitor.log_tool_call("execute_trade", {"action": "buy"}, {"success": True})
        self.assertEqual(len(self.monitor.tool_call_log), 1)
        self.assertEqual(self.monitor.tool_call_log[0]["tool_name"], "execute_trade")

    def test_log_llm_interaction_stores_usage(self):
        self.monitor.log_llm_interaction(
            request={"messages": [{"role": "user", "content": "hi"}]},
            response_text="hello",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        self.assertEqual(len(self.monitor.llm_interaction_log), 1)

    def test_log_safety_event_stores_event(self):
        self.monitor.log_safety_event({"type": "blocked", "reason": "손실 한도 초과"})
        self.assertEqual(len(self.monitor.safety_event_log), 1)

    def test_take_snapshot_stores_portfolio(self):
        portfolio = {"balance": 400000, "asset": {"BTC": (50000, 0.01)}}
        self.monitor.take_snapshot(portfolio)
        self.assertEqual(len(self.monitor.snapshots), 1)

    def test_get_trade_log_returns_all_results(self):
        self.monitor.log_trade_result({"type": "buy", "price": 50000})
        self.monitor.log_trade_result({"type": "sell", "price": 51000})
        log = self.monitor.get_trade_log()
        self.assertEqual(len(log), 2)

    def test_get_llm_usage_returns_token_totals(self):
        self.monitor.log_llm_interaction({}, "r1", {"input_tokens": 100, "output_tokens": 50})
        self.monitor.log_llm_interaction({}, "r2", {"input_tokens": 200, "output_tokens": 80})
        usage = self.monitor.get_llm_usage()
        self.assertEqual(usage["total_input_tokens"], 300)
        self.assertEqual(usage["total_output_tokens"], 130)
        self.assertEqual(usage["call_count"], 2)


class SystemMonitorSessionTagTests(unittest.TestCase):
    def setUp(self):
        self.monitor = SystemMonitor()

    def test_logs_carry_session_tag(self):
        self.monitor.log_market_data([{"type": "primary_candle"}], session="s1")
        self.monitor.log_trade_request({"id": "r1"}, session="s1")
        self.monitor.log_trade_result({"state": "done"}, session="s1")
        self.monitor.log_safety_event({"type": "blocked"}, session="s1")
        self.assertEqual(self.monitor.market_data_log[0]["session"], "s1")
        self.assertEqual(self.monitor.trade_request_log[0]["session"], "s1")
        self.assertEqual(self.monitor.trade_result_log[0]["session"], "s1")
        self.assertEqual(self.monitor.safety_event_log[0]["session"], "s1")

    def test_untagged_logs_default_to_none(self):
        self.monitor.log_trade_result({"state": "done"})
        self.assertIsNone(self.monitor.trade_result_log[0]["session"])

    def test_get_trade_log_filters_by_session(self):
        self.monitor.log_trade_result({"n": 1}, session="s1")
        self.monitor.log_trade_result({"n": 2}, session="s2")
        logs = self.monitor.get_trade_log(session="s1")
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["result"]["n"], 1)
        self.assertEqual(len(self.monitor.get_trade_log()), 2)
