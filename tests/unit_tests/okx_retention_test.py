"""Known OKX order recovery using only fake exchange responses and manual timers."""

import threading
import unittest
from collections import deque
from unittest.mock import Mock, patch

from smtm.trader.okx_trader import OkxTrader


class ManualTimer:
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
            raise AssertionError("Timer is not active")
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


class OkxRetentionTest(unittest.TestCase):
    def setUp(self):
        self.trader = OkxTrader.__new__(OkxTrader)
        self.trader.logger = Mock()
        self.trader._order_lock = threading.Lock()
        self.trader.market = "BTC-USDT"
        self.trader.worker = QueuedWorker()
        self.trader.timer = None
        self.trader.asset = (0, 0)
        self.trader.balance = 50000
        self.trader.commission_ratio = 0.001
        self.callback = Mock()
        self.order = {
            "order_id": "444", "callback": self.callback,
            "result": {"state": "requested", "type": "buy", "price": 10000, "amount": 1},
        }
        self.trader.order_map = {"request": self.order}
        self.trader._query_order = Mock(return_value=None)
        self.trader._cancel_order = Mock(return_value=None)
        self.timers = []
        timer_patch = patch("smtm.trader.base_exchange_trader.threading.Timer",
                            side_effect=self.make_timer)
        timer_patch.start()
        self.addCleanup(timer_patch.stop)
        network_patch = patch("requests.sessions.Session.request",
                              side_effect=AssertionError("Network forbidden"))
        network_patch.start()
        self.addCleanup(network_patch.stop)

    def make_timer(self, interval, callback):
        timer = ManualTimer(interval, callback)
        self.timers.append(timer)
        return timer

    def terminal(self, **changes):
        response = {"ordId": "444", "instId": "BTC-USDT", "state": "canceled",
                    "avgPx": "10000", "accFillSz": "0.25"}
        response.update(changes)
        return response

    def assert_pending(self):
        self.assertIs(self.trader.order_map["request"], self.order)
        self.assertEqual(self.order["result"], {
            "state": "requested", "type": "buy", "price": 10000, "amount": 1})
        self.callback.assert_not_called()
        self.assertEqual(self.trader.balance, 50000)
        self.assertEqual(self.trader.asset, (0, 0))
        self.assertEqual(sum(timer.active for timer in self.timers), 1)

    def run_poll(self):
        timer = self.trader.timer
        timer.fire()
        self.assertEqual(len(self.trader.worker.tasks), 1)
        self.trader.worker.run_next()
        self.assertFalse(self.trader.worker.tasks)
        self.assertTrue(timer.cancelled)

    def invalid_responses(self):
        responses = [None, {}, [], "bad", 1]
        for key in ("ordId", "instId", "state", "avgPx", "accFillSz"):
            response = self.terminal()
            del response[key]
            responses.append(response)
        for key, values in {
            "ordId": [None, "", True, "999", 444, 444.0, []],
            "instId": [None, "ETH-USDT", []],
            "state": [None, "live", "partially_filled", "unknown", [], {}],
            "avgPx": [None, "", True, False, "bad", "nan", "inf", "-1", "0", "1e-400", [], 10**400],
            "accFillSz": [None, "", True, False, "bad", "nan", "inf", "-1", "1e-400", [], 10**400],
        }.items():
            responses.extend(self.terminal(**{key: value}) for value in values)
        responses.extend([
            self.terminal(avgPx="1e308", accFillSz="1e308"),
            self.terminal(avgPx="1.7976931348623157e308", accFillSz="1"),
            self.terminal(avgPx="1e-300", accFillSz="1e-300"),
            self.terminal(state="filled", avgPx="", accFillSz="0"),
            self.terminal(state="filled", avgPx="10000", accFillSz="0"),
            self.terminal(avgPx="", accFillSz="1e-400"),
        ])
        return responses

    def test_uncertain_queries_keep_original_order_after_cancel(self):
        for response in self.invalid_responses():
            with self.subTest(response=response):
                self.trader._cancel_order.return_value = {"ordId": "444", "sCode": "0"}
                self.trader._query_order.return_value = response
                self.trader.cancel_request("request")
                self.assert_pending()
                self.assertEqual(len(self.timers), 1)

    def test_unusable_poll_keeps_order_and_one_successor(self):
        self.trader._start_timer()
        for number, response in enumerate(self.invalid_responses(), start=2):
            with self.subTest(response=response):
                self.trader._query_order.return_value = response
                self.run_poll()
                self.assert_pending()
                self.assertEqual(len(self.timers), number)
                self.assertEqual(self.trader.timer.interval, self.trader.RESULT_CHECKING_INTERVAL)

    def test_cancel_payload_never_substitutes_for_order_query(self):
        for response in [None, {}, [], "bad", {"ordId": "444", "sCode": "0"}, self.terminal()]:
            with self.subTest(response=response):
                self.trader._cancel_order.return_value = response
                self.trader.cancel_request("request")
                self.assert_pending()
        self.assertEqual(self.trader._query_order.call_count, 6)

    def test_uncertain_cancel_then_terminal_poll_accounts_once(self):
        self.trader.cancel_request("request")
        self.assert_pending()
        self.trader._query_order.return_value = self.terminal()
        self.run_poll()
        self.assertEqual(self.trader.order_map, {})
        self.assertIsNone(self.trader.timer)
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.asset, (10000, 0.25))
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["state"], "done")
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0.25)
        self.trader.cancel_request("request")
        self.trader._update_order_result(None)
        self.callback.assert_called_once()
        self.trader._cancel_order.assert_called_once_with("444")
        self.assertEqual(self.trader._query_order.call_count, 2)

    def test_documented_terminal_states_settle_in_both_paths(self):
        for state in ("filled", "canceled", "mmp_canceled"):
            for operation in ("cancel", "poll"):
                for amount in (("1",) if state == "filled" else ("0", "0.25")):
                    with self.subTest(state=state, operation=operation, amount=amount):
                        callback = Mock()
                        self.trader.order_map = {"request": {
                            "order_id": "444", "callback": callback,
                            "result": {"type": "buy", "state": "requested"}}}
                        response = self.terminal(state=state, accFillSz=amount,
                                                 avgPx="" if amount == "0" else "10000")
                        self.trader._query_order.return_value = response
                        if operation == "cancel":
                            self.trader.cancel_request("request")
                        else:
                            self.trader._update_order_result(None)
                        self.assertEqual(self.trader.order_map, {})
                        callback.assert_called_once()
                        self.assertEqual(callback.call_args[0][0]["amount"], float(amount))

    def test_partial_cancel_preserves_sell_accounting(self):
        self.order["result"]["type"] = "sell"
        self.trader.asset = (8000, 1)
        self.trader._query_order.return_value = self.terminal()
        self.trader.cancel_request("request")
        self.assertEqual(self.trader.asset, (8000, 0.75))
        self.assertEqual(self.trader.balance, 52498)
        self.callback.assert_called_once()

    def test_average_fill_price_used_instead_of_limit_or_last_price(self):
        self.trader._query_order.return_value = self.terminal(px="0", fillPx="12000")
        self.trader.cancel_request("request")
        self.assertEqual(self.callback.call_args[0][0]["price"], 10000)
        self.assertEqual(self.trader.balance, 47498)

    def test_explicit_zero_fill_cancel_has_no_accounting_effect(self):
        for price in ("", "0", 0, "10000"):
            with self.subTest(price=price):
                self.trader.order_map["request"] = self.order
                self.trader._query_order.return_value = self.terminal(avgPx=price, accFillSz="0")
                self.trader.cancel_request("request")
                self.assertEqual(self.trader.balance, 50000)
                self.assertEqual(self.trader.asset, (0, 0))
                self.assertEqual(self.trader.order_map, {})
                self.assertEqual(self.callback.call_args[0][0]["amount"], 0)

    def test_unknown_request_is_noop(self):
        self.trader.cancel_request("unknown")
        self.trader._cancel_order.assert_not_called()
        self.trader._query_order.assert_not_called()
        self.assertIsNone(self.trader.timer)

    def test_empty_map_stops_timer_without_query(self):
        self.trader._start_timer()
        self.trader.order_map.clear()
        self.run_poll()
        self.assertIsNone(self.trader.timer)
        self.trader._query_order.assert_not_called()

    def test_malformed_envelopes_keep_real_query_path_unresolved(self):
        del self.trader._query_order, self.trader._cancel_order
        self.trader._validate_credentials = Mock(return_value=True)
        self.trader._auth_headers = Mock(return_value={})
        self.trader.SERVER_URL = "https://exchange.invalid"
        self.trader._request_get = Mock()
        self.trader._request_post = Mock()
        envelopes = [None, [], "bad", 1, {}, {"code": "0", "data": []},
                     {"code": "0", "data": {}}, {"code": "0", "data": "bad"},
                     {"code": "0", "data": [None]}, {"code": "0", "data": [1]},
                     {"code": "0", "data": ["bad"]}, {"code": "0", "data": [[]]},
                     {"code": "1", "data": [self.terminal()]},
                     {"code": "0", "data": [self.terminal(sCode="51000")]}]
        for response in envelopes:
            with self.subTest(response=response):
                self.trader._request_post.return_value = response
                self.trader._request_get.return_value = response
                self.trader.cancel_request("request")
                self.assert_pending()
                self.run_poll()
                self.assert_pending()

    def test_unexpected_cancel_exception_keeps_tracking_and_schedules_poll(self):
        self.trader._cancel_order.side_effect = RuntimeError("cancel failure")
        with self.assertRaisesRegex(RuntimeError, "cancel failure"):
            self.trader.cancel_request("request")
        self.assert_pending()
        self.trader._query_order.assert_not_called()

    def test_unexpected_query_exception_keeps_tracking_and_schedules_poll(self):
        self.trader._query_order.side_effect = RuntimeError("query failure")
        with self.assertRaisesRegex(RuntimeError, "query failure"):
            self.trader.cancel_request("request")
        self.assert_pending()
        with self.assertRaisesRegex(RuntimeError, "query failure"):
            self.run_poll()
        self.assert_pending()

    def launch(self, operation):
        errors = []
        def run():
            try:
                operation()
            except BaseException as error:
                errors.append(error)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread, errors

    def finish(self, thread, errors):
        thread.join(2)
        self.assertFalse(thread.is_alive(), "Deadlock watchdog")
        if errors:
            raise errors[0]

    def test_cancel_blocked_while_poll_completes_does_not_double_account(self):
        entered, release = threading.Event(), threading.Event()
        def cancel(_):
            entered.set()
            if not release.wait(2):
                raise AssertionError("Cancel release watchdog")
            return {"ordId": "444", "sCode": "0"}
        self.trader._cancel_order.side_effect = cancel
        thread, errors = self.launch(lambda: self.trader.cancel_request("request"))
        try:
            self.assertTrue(entered.wait(2))
            self.assertIs(self.trader.order_map["request"], self.order)
            self.trader._query_order.return_value = self.terminal(state="filled")
            self.trader._update_order_result(None)
        finally:
            release.set()
            self.finish(thread, errors)
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.order_map, {})
        self.trader._query_order.assert_called_once()

    def test_late_nonterminal_poll_cannot_restore_completed_order(self):
        entered, release = threading.Event(), threading.Event()
        def query(_):
            if threading.current_thread() is threading.main_thread():
                return self.terminal()
            entered.set()
            if not release.wait(2):
                raise AssertionError("Poll release watchdog")
            return self.terminal(state="live")
        self.trader._query_order.side_effect = query
        thread, errors = self.launch(lambda: self.trader._update_order_result(None))
        try:
            self.assertTrue(entered.wait(2))
            self.trader.cancel_request("request")
        finally:
            release.set()
            self.finish(thread, errors)
        self.callback.assert_called_once()
        self.assertEqual(self.trader.order_map, {})
        self.assertIsNone(self.trader.timer)

    def test_simultaneous_terminal_queries_claim_one_completion(self):
        barrier = threading.Barrier(2)
        def query(_):
            barrier.wait(timeout=2)
            return self.terminal()
        self.trader._query_order.side_effect = query
        thread, errors = self.launch(lambda: self.trader.cancel_request("request"))
        try:
            self.trader._update_order_result(None)
        finally:
            self.finish(thread, errors)
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.asset, (10000, 0.25))
        self.assertEqual(self.trader.order_map, {})

    def test_simultaneous_cancellations_claim_one_completion(self):
        barrier = threading.Barrier(2)
        def query(_):
            barrier.wait(timeout=2)
            return self.terminal()
        self.trader._query_order.side_effect = query
        thread, errors = self.launch(lambda: self.trader.cancel_request("request"))
        try:
            self.trader.cancel_request("request")
        finally:
            self.finish(thread, errors)
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.order_map, {})

    def test_late_query_preserves_replacement_and_new_entry(self):
        for operation in ("poll", "cancel"):
            with self.subTest(operation=operation):
                self.trader.order_map = {"request": self.order}
                replacement = {"order_id": "555", "result": {"state": "requested"}, "callback": Mock()}
                new_order = {"order_id": "666", "result": {"state": "requested"}, "callback": Mock()}
                def query(_):
                    acquired = self.trader._order_lock.acquire(timeout=2)
                    self.assertTrue(acquired, "Query ran under ownership lock")
                    try:
                        self.trader.order_map["request"] = replacement
                        self.trader.order_map["new"] = new_order
                    finally:
                        self.trader._order_lock.release()
                    return self.terminal()
                self.trader._query_order.side_effect = query
                if operation == "poll":
                    self.trader._update_order_result(None)
                else:
                    self.trader.cancel_request("request")
                self.assertIs(self.trader.order_map["request"], replacement)
                self.assertIs(self.trader.order_map["new"], new_order)
                self.callback.assert_not_called()
                self.assertEqual(self.order["result"]["state"], "requested")

    def test_late_cancel_ack_preserves_replacement_without_query(self):
        replacement = {"order_id": "555", "result": {"state": "requested"}, "callback": Mock()}
        def cancel(_):
            acquired = self.trader._order_lock.acquire(timeout=2)
            self.assertTrue(acquired, "Cancel ran under ownership lock")
            try:
                self.trader.order_map["request"] = replacement
            finally:
                self.trader._order_lock.release()
            return {"ordId": "444", "sCode": "0"}
        self.trader._cancel_order.side_effect = cancel
        self.trader.cancel_request("request")
        self.assertIs(self.trader.order_map["request"], replacement)
        self.trader._query_order.assert_not_called()
        self.callback.assert_not_called()

    def test_callback_can_reenter_without_lock_and_add_order(self):
        def callback(_):
            acquired = self.trader._order_lock.acquire(blocking=False)
            self.assertTrue(acquired, "Callback ran under ownership lock")
            self.trader._order_lock.release()
            self.trader.cancel_request("request")
            self.trader.order_map["new"] = {"order_id": "555"}
        self.callback.side_effect = callback
        self.trader._query_order.return_value = self.terminal()
        self.trader._update_order_result(None)
        self.assertEqual(self.trader.order_map, {"new": {"order_id": "555"}})
        self.callback.assert_called_once()
        self.trader._cancel_order.assert_not_called()
        self.assertEqual(sum(timer.active for timer in self.timers), 1)

    def test_callback_failure_never_restores_completed_order(self):
        for operation in ("poll", "cancel"):
            with self.subTest(operation=operation):
                self.callback.reset_mock()
                self.callback.side_effect = RuntimeError("client failure")
                self.trader.order_map = {"request": self.order, "new": {"order_id": "555"}}
                self.trader.balance = 50000
                self.trader.asset = (0, 0)
                self.trader._query_order.return_value = self.terminal()
                with self.assertRaisesRegex(RuntimeError, "client failure"):
                    if operation == "poll":
                        self.trader._update_order_result(None)
                    else:
                        self.trader.cancel_request("request")
                self.assertNotIn("request", self.trader.order_map)
                self.assertIn("new", self.trader.order_map)
                self.assertEqual(self.trader.balance, 47498)
                self.assertEqual(sum(timer.active for timer in self.timers), 1)
                self.trader.cancel_request("request")
                self.callback.assert_called_once()

    def test_distinct_order_settlements_serialize_existing_accounting(self):
        test = self
        class CheckedAsset(tuple):
            def __getitem__(self, index):
                test.assertTrue(test.trader._order_lock.locked(),
                                "Accounting read assets without ownership lock")
                return super().__getitem__(index)
        self.trader.asset = CheckedAsset((0, 0))
        second_callback = Mock()
        self.trader.order_map["second"] = {
            "order_id": "555", "callback": second_callback,
            "result": {"state": "requested", "type": "buy"},
        }
        barrier = threading.Barrier(2)
        queried = threading.local()
        def query(order_id):
            if not getattr(queried, "started", False):
                queried.started = True
                barrier.wait(timeout=2)
            return self.terminal(ordId=order_id,
                                 accFillSz="0.25" if order_id == "444" else "0.5")
        self.trader._query_order.side_effect = query
        thread, errors = self.launch(lambda: self.trader.cancel_request("second"))
        try:
            self.trader._update_order_result(None)
        finally:
            self.finish(thread, errors)
        self.callback.assert_called_once()
        second_callback.assert_called_once()
        self.assertEqual(self.trader.asset, (10000, 0.75))
        self.assertEqual(self.trader.balance, 42493)
        self.assertEqual(self.trader.order_map, {})

    def test_accounting_failure_is_not_attempted_again(self):
        self.trader._call_callback = Mock(side_effect=RuntimeError("accounting failure"))
        self.trader._query_order.return_value = self.terminal()
        with self.assertRaisesRegex(RuntimeError, "accounting failure"):
            self.trader.cancel_request("request")
        self.trader.cancel_request("request")
        self.trader._update_order_result(None)
        self.trader._call_callback.assert_called_once()
        self.callback.assert_not_called()
        self.assertEqual(self.trader.order_map, {})

    def test_cancel_all_snapshots_ids_without_copying_callback_owner(self):
        class CallbackOwner:
            def __init__(self):
                self.lock = threading.Lock()
            def callback(self, _):
                pass
        self.order["callback"] = CallbackOwner().callback
        self.trader.order_map["second"] = {"order_id": "555"}
        cancelled = []
        def cancel(request_id):
            cancelled.append(request_id)
            with self.trader._order_lock:
                self.trader.order_map.pop(request_id)
                self.trader.order_map["new"] = {"order_id": "666"}
        self.trader.cancel_request = cancel
        self.trader.cancel_all_requests()
        self.assertEqual(cancelled, ["request", "second"])
        self.assertEqual(self.trader.order_map, {"new": {"order_id": "666"}})
