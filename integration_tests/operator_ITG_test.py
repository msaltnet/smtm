import unittest
import time
from smtm import Operator
from unittest.mock import *
import requests


class OperatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ITG_operator_execute_trading(self):
        data_provider = MagicMock()
        analyzer = MagicMock()
        strategy = MagicMock()
        trader = MagicMock()
        count = 0
        last_time = time.time()

        def check_interval():
            nonlocal count, last_time
            count += 1
            now = time.time()
            interval = now - last_time
            print(f"count {count}, interval {interval}, now {now}, last_time {last_time}")
            if count > 1 and count < 4:
                self.assertTrue(interval > 0.9)
                self.assertTrue(interval < 1.1)
            last_time = now

        data_provider.get_info = check_interval

        op = Operator()
        self.assertEqual(op.state, None)
        op.initialize(data_provider, strategy, trader, analyzer, budget=50000)
        self.assertEqual(op.state, "ready")
        analyzer.initialize.assert_called_with(trader.get_account_info)
        strategy.initialize.assert_called_with(50000, add_spot_callback=ANY)

        strategy.get_request.return_value = "mango"
        op.set_interval(1)
        op.start()
        time.sleep(2.5)
        strategy.get_request.assert_called()
        strategy.update_trading_info.assert_called()
        analyzer.put_trading_info.assert_called()
        analyzer.put_requests.assert_called_with("mango")
        trader.send_request.assert_called_with("mango", ANY)
        callback = trader.send_request.call_args[0][1]
        callback({"state": "done"})
        strategy.update_result.assert_called_with({"state": "done"})
        analyzer.put_result.assert_called_with({"state": "done"})
        self.assertEqual(op.state, "running")

        dummy_callback = MagicMock()
        analyzer.get_return_report.return_value = "dummy_report"
        op.get_score(dummy_callback)
        time.sleep(0.5)
        analyzer.get_return_report.assert_called()
        dummy_callback.assert_called_with("dummy_report")

        op.stop()
        time.sleep(0.5)
        self.assertEqual(op.state, "ready")
