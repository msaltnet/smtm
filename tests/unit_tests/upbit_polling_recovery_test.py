"""Exercise Upbit polling with a queued worker and manually fired timers."""

import unittest
from collections import deque
from unittest.mock import Mock, patch

from smtm import UpbitTrader


class FakeTimer:
    """One-shot timer that never creates a thread or waits for real time."""

    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self.active = False
        self.cancelled = False

    def start(self):
        self.active = True

    def cancel(self):
        self.active = False
        self.cancelled = True

    def fire(self):
        if not self.active:
            raise AssertionError("Only an active timer can fire")
        self.active = False
        self.callback()


class QueuedWorker:
    def __init__(self):
        self.tasks = deque()

    def post_task(self, task):
        self.tasks.append(task)

    def run_next(self):
        task = self.tasks.popleft()
        task["runnable"](task)


class UpbitPollingRecoveryTests(unittest.TestCase):
    def setUp(self):
        # Avoid starting a worker or looking up credentials in the constructor.
        self.trader = UpbitTrader.__new__(UpbitTrader)
        self.trader.logger = Mock()
        self.trader.worker = QueuedWorker()
        self.trader.timer = None
        self.trader.asset = (0, 0)
        self.trader.balance = 50000
        self.trader.commission_ratio = 0.0005
        self.callback = Mock()
        self.order = {
            "uuid": "fake-order-uuid",
            "callback": self.callback,
            "result": {
                "state": "requested",
                "type": "buy",
                "price": 10000,
                "amount": 1,
            },
        }
        self.trader.order_map = {"fake-request-id": self.order}
        self.trader._query_order_list = Mock()
        self.timers = []
        timer_patch = patch(
            "smtm.trader.base_exchange_trader.threading.Timer",
            side_effect=self.make_timer,
        )
        timer_patch.start()
        self.addCleanup(timer_patch.stop)
        network_patch = patch(
            "requests.sessions.Session.request",
            side_effect=AssertionError("Network access is forbidden in this test"),
        )
        network_patch.start()
        self.addCleanup(network_patch.stop)

    def make_timer(self, interval, callback):
        timer = FakeTimer(interval, callback)
        self.timers.append(timer)
        return timer

    def run_poll(self):
        timer = self.trader.timer
        timer.fire()
        self.assertEqual(len(self.trader.worker.tasks), 1)
        self.trader.worker.run_next()
        self.assertFalse(self.trader.worker.tasks)
        self.assertTrue(timer.cancelled)

    def assert_one_successor(self, timer_count):
        self.assertEqual(len(self.timers), timer_count)
        self.assertIs(self.trader.timer, self.timers[-1])
        self.assertEqual(sum(timer.active for timer in self.timers), 1)
        self.assertEqual(
            self.trader.timer.interval, self.trader.RESULT_CHECKING_INTERVAL
        )
        self.trader._start_timer()
        self.assertEqual(len(self.timers), timer_count)

    def test_failed_poll_recovers_and_reports_terminal_fill_once(self):
        self.trader._query_order_list.side_effect = [
            None,
            [{
                "uuid": "fake-order-uuid",
                "state": "done",
                "created_at": "2026-10-06T10:00:00+09:00",
                "price": "10000",
                "executed_volume": "1",
            }],
        ]
        self.trader._start_timer()

        self.run_poll()

        self.assertIs(self.trader.order_map["fake-request-id"], self.order)
        self.assertEqual(self.order["result"]["state"], "requested")
        self.callback.assert_not_called()
        self.assertEqual(self.trader.asset, (0, 0))
        self.assertEqual(self.trader.balance, 50000)
        self.assert_one_successor(2)

        self.run_poll()

        self.callback.assert_called_once_with({
            "state": "done",
            "type": "buy",
            "price": 10000.0,
            "amount": 1.0,
            "date_time": "2026-10-06T10:00:00",
        })
        self.assertEqual(self.trader.asset, (10000, 1))
        self.assertEqual(self.trader.balance, 39995)
        self.assertEqual(self.trader.order_map, {})
        self.assertIsNone(self.trader.timer)
        self.assertFalse(any(timer.active for timer in self.timers))
        self.assertEqual(self.trader._query_order_list.call_count, 2)
        self.trader._query_order_list.assert_called_with(["fake-order-uuid"])

        # A late queued poll must neither query nor report the fill again.
        self.trader._update_order_result(None)
        self.callback.assert_called_once()
        self.assertEqual(self.trader._query_order_list.call_count, 2)
        self.assertEqual(len(self.timers), 2)

    def test_repeated_failures_keep_order_and_one_successor(self):
        self.trader._query_order_list.return_value = None
        self.trader._start_timer()

        for poll_number in range(1, 4):
            self.run_poll()
            self.assertIs(self.trader.order_map["fake-request-id"], self.order)
            self.callback.assert_not_called()
            self.assertEqual(self.trader._query_order_list.call_count, poll_number)
            self.assert_one_successor(poll_number + 1)

    def test_empty_order_map_clears_expired_timer_without_query(self):
        self.trader._start_timer()
        self.trader.order_map.clear()

        self.run_poll()

        self.trader._query_order_list.assert_not_called()
        self.callback.assert_not_called()
        self.assertIsNone(self.trader.timer)
        self.assertEqual(len(self.timers), 1)
        self.assertFalse(any(timer.active for timer in self.timers))

    def test_successful_empty_query_keeps_order_and_one_successor(self):
        self.trader._query_order_list.return_value = []
        self.trader._start_timer()

        self.run_poll()

        self.assertIs(self.trader.order_map["fake-request-id"], self.order)
        self.callback.assert_not_called()
        self.trader._query_order_list.assert_called_once_with(["fake-order-uuid"])
        self.assert_one_successor(2)
