import unittest
from unittest.mock import MagicMock
from smtm import Analyzer


class AnalyzerTests(unittest.TestCase):
    def setUp(self):
        self.monitor = MagicMock()
        self.analyzer = Analyzer(self.monitor)
        self.account = {
            "balance": 400000,
            "asset": {"BTC": (50000, 2.0)},   # (평균단가, 수량)
            "quote": {"BTC": 60000},
        }
        self.analyzer.initialize(lambda: self.account)

    def test_put_methods_delegate_to_system_monitor(self):
        self.analyzer.put_trading_info([{"type": "primary_candle"}])
        self.monitor.log_market_data.assert_called_once()

        self.analyzer.put_requests([{"id": "1"}, {"id": "2"}])
        self.assertEqual(self.monitor.log_trade_request.call_count, 2)

        self.analyzer.put_result({"state": "done"})
        self.monitor.log_trade_result.assert_called_once()

        self.analyzer.put_safety_event({"reason": "blocked"})
        self.monitor.log_safety_event.assert_called_once()

    def test_current_account_value_includes_assets_at_quote(self):
        # 400000 + 2.0 * 60000 = 520000
        self.assertEqual(self.analyzer.current_account_value(), 520000)

    def test_current_account_value_falls_back_to_avg_price_without_quote(self):
        # quote가 없으면 평균단가로 자산 가치를 계산한다
        self.account["quote"] = {}
        # 400000 + 2.0 * 50000(평균단가) = 500000
        self.assertEqual(self.analyzer.current_account_value(), 500000)

    def test_get_return_report_computes_cumulative_return(self):
        self.analyzer.make_start_point()          # 시작 가치 520000
        self.account["balance"] = 452000          # 현재 가치 572000 → +10%
        report = self.analyzer.get_return_report()
        self.assertEqual(report["start_value"], 520000)
        self.assertEqual(report["current_value"], 572000)
        self.assertEqual(report["cumulative_return"], 10.0)

    def test_get_return_report_without_start_point_returns_zero(self):
        report = self.analyzer.get_return_report()
        self.assertEqual(report["cumulative_return"], 0)

    def test_drawing_callbacks_accumulate(self):
        self.analyzer.add_drawing_spot("2026-07-03T12:00:00", 100)
        self.analyzer.add_value_for_line_graph("2026-07-03T12:00:00", 200)
        self.assertEqual(len(self.analyzer.spots), 1)
        self.assertEqual(len(self.analyzer.lines), 1)

    def test_analyzer_tags_session_name(self):
        analyzer = Analyzer(self.monitor, session_name="s9")
        analyzer.put_result({"state": "done"})
        self.monitor.log_trade_result.assert_called_once_with(
            {"state": "done"}, session="s9")
