"""Exercise Upbit polling with a queued worker and manually fired timers."""

import unittest
import threading
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
        self.trader._order_lock = threading.Lock()
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
        self.trader._cancel_order = Mock(return_value=None)
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

    def terminal_response(self, **changes):
        response = {
            "uuid": "fake-order-uuid",
            "state": "cancel",
            "created_at": "2026-10-06T10:00:00+09:00",
            "price": "10000",
            "executed_volume": "0.25",
        }
        response.update(changes)
        return response

    def assert_pending(self):
        self.assertIs(self.trader.order_map["fake-request-id"], self.order)
        self.assertEqual(self.order["result"], {
            "state": "requested", "type": "buy", "price": 10000, "amount": 1,
        })
        self.callback.assert_not_called()
        self.assertEqual(self.trader.asset, (0, 0))
        self.assertEqual(self.trader.balance, 50000)
        self.assertEqual(sum(timer.active for timer in self.timers), 1)

    def test_uncertain_cancel_and_fallback_retain_order_and_polling(self):
        invalid_responses = [
            None, [], {}, "unusable", [None], [{"uuid": "fake-order-uuid"}],
            [self.terminal_response(uuid="another-order")],
            [self.terminal_response(state="wait")],
            [self.terminal_response(state="watch")],
            [self.terminal_response(state="unknown")],
        ]
        self.trader._start_timer()
        for response in invalid_responses:
            with self.subTest(response=response):
                self.trader._query_order_list.return_value = response
                self.trader.cancel_request("fake-request-id")
                self.assert_pending()
                self.assertEqual(len(self.timers), 1)

    def test_unusable_cancel_payloads_do_not_mutate_pending_result(self):
        invalid_responses = [None, [], {}, "unusable"]
        for key in ("uuid", "state", "created_at", "price", "executed_volume"):
            response = self.terminal_response()
            del response[key]
            invalid_responses.append(response)
        for key, values in {
            "state": ["wait", "watch", "unknown", None, []],
            "uuid": ["another-order", None],
            "created_at": [None, 123, "", "  "],
            "price": [True, False, "bad", "nan", "inf", "-1", [], 10**400],
            "executed_volume": [None, True, False, "bad", "nan", "inf", "-1", {}, 10**400],
        }.items():
            invalid_responses.extend(self.terminal_response(**{key: value}) for value in values)
        invalid_responses.append(self.terminal_response(price="1e308", executed_volume="1e308"))
        invalid_responses.append(self.terminal_response(price="1.7976931348623157e308", executed_volume="1"))
        self.trader._query_order_list.return_value = []
        for response in invalid_responses:
            with self.subTest(response=response):
                self.trader._cancel_order.return_value = response
                self.trader.cancel_request("fake-request-id")
                self.assert_pending()
                self.assertEqual(len(self.timers), 1)

    def test_uncertain_cancel_recovers_after_unusable_polls_once(self):
        self.trader._query_order_list.return_value = None
        self.trader.cancel_request("fake-request-id")
        self.assert_pending()
        for response in (None, {}, "bad", [None, {}],
                         [self.terminal_response(state="wait")],
                         [self.terminal_response(price="nan")]):
            self.trader._query_order_list.return_value = response
            self.run_poll()
            self.assert_pending()
        # Ignore unusable rows and stop after the first matching terminal row.
        terminal = self.terminal_response(state="done", executed_volume="1")
        self.trader._query_order_list.return_value = [None, {}, terminal, terminal]
        self.run_poll()
        self.callback.assert_called_once_with({
            "state": "done", "type": "buy", "price": 10000.0, "amount": 1.0,
            "date_time": "2026-10-06T10:00:00",
        })
        self.assertEqual(self.trader.balance, 39995)
        self.assertEqual(self.trader.asset, (10000, 1))
        self.assertEqual(self.trader.order_map, {})
        self.assertIsNone(self.trader.timer)
        self.trader.cancel_request("fake-request-id")
        self.trader._update_order_result(None)
        self.callback.assert_called_once()
        self.trader._cancel_order.assert_called_once()

    def test_confirmed_partial_cancel_preserves_buy_accounting(self):
        self.trader._cancel_order.return_value = self.terminal_response()
        self.trader.cancel_request("fake-request-id")
        self.callback.assert_called_once_with({
            "state": "done", "type": "buy", "price": 10000.0, "amount": 0.25,
            "date_time": "2026-10-06T10:00:00",
        })
        self.assertEqual(self.trader.balance, 47499)
        self.assertEqual(self.trader.asset, (10000, 0.25))
        self.assertEqual(self.trader.order_map, {})
        self.trader._query_order_list.assert_not_called()

    def test_confirmed_partial_cancel_preserves_sell_accounting(self):
        self.order["result"]["type"] = "sell"
        self.trader.asset = (8000, 1)
        self.trader._cancel_order.return_value = self.terminal_response()
        self.trader.cancel_request("fake-request-id")
        self.assertEqual(self.trader.balance, 52499)
        self.assertEqual(self.trader.asset, (8000, 0.75))
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0.25)

    def test_confirmed_zero_fill_cancel_keeps_accounting_unchanged(self):
        self.trader._cancel_order.return_value = self.terminal_response(executed_volume="0")
        self.trader.cancel_request("fake-request-id")
        self.assertEqual(self.trader.balance, 50000)
        self.assertEqual(self.trader.asset, (0, 0))
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0)
        self.assertEqual(self.trader.order_map, {})

    def test_confirmed_null_price_preserves_existing_accounting(self):
        self.trader._cancel_order.return_value = self.terminal_response(price=None)
        self.trader.cancel_request("fake-request-id")
        self.assertEqual(self.trader.balance, 50000)
        self.assertEqual(self.trader.asset, (0, 0.25))
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["price"], 0)

    def test_fallback_finds_matching_terminal_among_other_rows(self):
        self.trader._query_order_list.return_value = [
            None, self.terminal_response(uuid="other"),
            self.terminal_response(state="wait"),
            self.terminal_response(state="done", executed_volume="1"),
        ]
        self.trader.cancel_request("fake-request-id")
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 39995)
        self.assertEqual(self.trader.asset, (10000, 1))
        self.assertEqual(self.trader.order_map, {})

    def test_unknown_cancel_request_is_noop(self):
        self.trader.cancel_request("unknown")
        self.trader._cancel_order.assert_not_called()
        self.trader._query_order_list.assert_not_called()
        self.callback.assert_not_called()
        self.assertEqual(self.timers, [])

    def test_poll_wins_while_cancel_response_is_in_flight(self):
        self.run_terminal_race(cancel_is_delayed=True)

    def test_cancel_wins_while_poll_response_is_in_flight(self):
        self.run_terminal_race(cancel_is_delayed=False)

    def run_terminal_race(self, cancel_is_delayed):
        entered = threading.Event()
        release = threading.Event()
        errors = []
        response = self.terminal_response()

        def delayed_response(*_):
            acquired = self.trader._order_lock.acquire(blocking=False)
            self.assertTrue(acquired, "Exchange calls must run outside the order lock")
            if acquired:
                self.trader._order_lock.release()
            entered.set()
            if not release.wait(2):
                raise AssertionError("Test did not release the delayed response")
            return response if cancel_is_delayed else [response]

        def background():
            try:
                if cancel_is_delayed:
                    self.trader.cancel_request("fake-request-id")
                else:
                    self.trader._update_order_result(None)
            except BaseException as error:
                errors.append(error)

        if cancel_is_delayed:
            self.trader._cancel_order.side_effect = delayed_response
            self.trader._query_order_list.return_value = [response]
        else:
            self.trader._query_order_list.side_effect = delayed_response
            self.trader._cancel_order.return_value = response
        thread = threading.Thread(target=background, daemon=True)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            if cancel_is_delayed:
                self.trader._update_order_result(None)
            else:
                self.trader.cancel_request("fake-request-id")
            self.callback.assert_called_once()
        finally:
            release.set()
            thread.join(2)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.assertIsNone(self.trader.timer)
        self.assertFalse(any(timer.active for timer in self.timers))
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47499)
        self.assertEqual(self.trader.asset, (10000, 0.25))
        self.assertEqual(self.trader.order_map, {})

    def test_late_cancel_response_cannot_retire_replacement_order(self):
        replacement = {
            "uuid": "replacement-uuid", "callback": Mock(),
            "result": {"state": "requested"},
        }

        def replace_before_response(_):
            self.trader.order_map["fake-request-id"] = replacement
            return self.terminal_response()

        self.trader._cancel_order.side_effect = replace_before_response
        self.trader._query_order_list.return_value = [self.terminal_response()]
        self.trader.cancel_request("fake-request-id")
        self.assertIs(self.trader.order_map["fake-request-id"], replacement)
        self.assertEqual(replacement["result"], {"state": "requested"})
        self.assertEqual(self.order["result"]["state"], "requested")
        self.callback.assert_not_called()
        replacement["callback"].assert_not_called()
        self.assertEqual(self.trader.balance, 50000)

    def test_poll_snapshot_cannot_retire_replacement_order(self):
        replacement = {"uuid": "replacement-uuid", "callback": Mock(), "result": {}}

        def replace_before_response(_):
            self.trader.order_map["fake-request-id"] = replacement
            return [self.terminal_response()]

        self.trader._query_order_list.side_effect = replace_before_response
        self.trader._update_order_result(None)
        self.assertIs(self.trader.order_map["fake-request-id"], replacement)
        self.callback.assert_not_called()
        replacement["callback"].assert_not_called()

    def test_callback_runs_outside_order_lock(self):
        def callback(_):
            acquired = self.trader._order_lock.acquire(blocking=False)
            self.assertTrue(acquired)
            if acquired:
                self.trader._order_lock.release()
            self.trader.cancel_request("fake-request-id")

        self.callback.side_effect = callback
        self.trader._cancel_order.return_value = self.terminal_response()
        self.trader.cancel_request("fake-request-id")
        self.callback.assert_called_once()
        self.trader._cancel_order.assert_called_once()

    def test_poll_preserves_another_order_added_during_query(self):
        new_order = {"uuid": "new-uuid", "callback": Mock(), "result": {}}

        def add_before_response(_):
            self.trader.order_map["new-request-id"] = new_order
            return [self.terminal_response()]

        self.trader._query_order_list.side_effect = add_before_response
        self.trader._update_order_result(None)
        self.assertEqual(self.trader.order_map, {"new-request-id": new_order})
        self.assertIs(self.trader.order_map["new-request-id"], new_order)
        new_order["callback"].assert_not_called()
        self.callback.assert_called_once()
        self.assert_one_successor(1)

    def test_callback_failure_does_not_restore_or_account_order_twice(self):
        self.callback.side_effect = ValueError("client callback failed")
        self.trader._cancel_order.return_value = self.terminal_response()
        with self.assertRaisesRegex(ValueError, "client callback failed"):
            self.trader.cancel_request("fake-request-id")
        self.assertEqual(self.trader.order_map, {})
        self.trader.cancel_request("fake-request-id")
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47499)
        self.assertEqual(self.trader.asset, (10000, 0.25))
