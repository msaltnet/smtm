"""Known-order recovery with no exchange, real timer, or worker thread."""

import threading
import unittest
from collections import deque
from unittest.mock import Mock, patch

from smtm.trader.binance_trader import BinanceTrader


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


class BinanceRetentionTest(unittest.TestCase):
    def setUp(self):
        self.trader = BinanceTrader.__new__(BinanceTrader)
        self.trader.logger = Mock()
        self.trader._order_lock = threading.Lock()
        self.trader.market = "BTCUSDT"
        self.trader.worker = QueuedWorker()
        self.trader.timer = None
        self.trader.asset = (0, 0)
        self.trader.balance = 50000
        self.trader.commission_ratio = 0.001
        self.callback = Mock()
        self.order = {
            "order_id": 444,
            "callback": self.callback,
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
        response = {"orderId": 444, "symbol": "BTCUSDT", "status": "CANCELED",
                    "price": "10000", "executedQty": "0.25",
                    "cummulativeQuoteQty": "2500"}
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
        for key in ("orderId", "symbol", "status", "price", "executedQty"):
            response = self.terminal()
            del response[key]
            responses.append(response)
        for key, values in {
            "orderId": [None, True, 999, "444", 444.0, []],
            "symbol": [None, "ETHUSDT", []],
            "status": [None, "NEW", "PARTIALLY_FILLED", "PENDING_NEW",
                       "PENDING_CANCEL", "unknown", []],
            "price": [None, True, False, "bad", "nan", "inf", "-1", "1e-400", [], 10**400],
            "executedQty": [None, True, False, "bad", "nan", "inf", "-1", "1e-400", [], 10**400],
        }.items():
            responses.extend(self.terminal(**{key: value}) for value in values)
        responses.append(self.terminal(price="1e308", executedQty="1e308"))
        responses.append(self.terminal(price="1.7976931348623157e308", executedQty="1"))
        # Market fills need usable cumulative quote, never an invented zero price.
        response = self.terminal(price="0")
        del response["cummulativeQuoteQty"]
        responses.append(response)
        responses.extend(self.terminal(price="0", cummulativeQuoteQty=value)
                         for value in (None, True, False, "0", "bad", "nan", "inf", "-1", [], 10**400))
        responses.append(self.terminal(price="0", executedQty="1e-300", cummulativeQuoteQty="1e308"))
        responses.append(self.terminal(price="0", executedQty="1e308", cummulativeQuoteQty="1e-300"))
        responses.append(self.terminal(price="1e-300", executedQty="1e-300"))
        responses.append(self.terminal(status="FILLED", executedQty="0", cummulativeQuoteQty="0"))
        return responses

    def test_unusable_cancel_and_fallback_keep_original_order(self):
        for response in self.invalid_responses():
            with self.subTest(response=response):
                self.trader._cancel_order.return_value = response
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
        self.trader._cancel_order.assert_called_once_with(444)
        self.assertEqual(self.trader._query_order.call_count, 2)

    def test_documented_terminal_states_settle_in_both_paths(self):
        for status in ("FILLED", "CANCELED", "REJECTED", "EXPIRED", "EXPIRED_IN_MATCH"):
            for operation in ("cancel", "poll"):
                with self.subTest(status=status, operation=operation):
                    callback = Mock()
                    self.trader.order_map = {"request": {
                        "order_id": 444, "callback": callback,
                        "result": {"type": "buy", "state": "requested"}}}
                    amount = "1" if status == "FILLED" else "0"
                    response = self.terminal(status=status, executedQty=amount)
                    self.trader._cancel_order.return_value = response
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
        self.trader._cancel_order.return_value = self.terminal()
        self.trader.cancel_request("request")
        self.assertEqual(self.trader.asset, (8000, 0.75))
        self.assertEqual(self.trader.balance, 52498)
        self.callback.assert_called_once()
        self.trader._query_order.assert_not_called()

    def test_market_fill_uses_cumulative_quote(self):
        self.trader._cancel_order.return_value = self.terminal(price="0")
        self.trader.cancel_request("request")
        self.assertEqual(self.callback.call_args[0][0]["price"], 10000)
        self.assertEqual(self.trader.balance, 47498)

    def test_zero_fill_cancel_has_no_accounting_effect(self):
        self.trader._cancel_order.return_value = self.terminal(price="0", executedQty="0", cummulativeQuoteQty="0")
        self.trader.cancel_request("request")
        self.assertEqual(self.trader.balance, 50000)
        self.assertEqual(self.trader.asset, (0, 0))
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0)

    def test_nonterminal_cancel_can_resolve_from_fallback(self):
        self.trader._cancel_order.return_value = self.terminal(status="PARTIALLY_FILLED")
        self.trader._query_order.return_value = self.terminal(status="FILLED", executedQty="1")
        self.trader.cancel_request("request")
        self.trader._query_order.assert_called_once_with(444)
        self.assertEqual(self.trader.asset, (10000, 1))
        self.assertEqual(self.trader.balance, 39990)
        self.callback.assert_called_once()

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
            return self.terminal()
        self.trader._cancel_order.side_effect = cancel
        thread, errors = self.launch(lambda: self.trader.cancel_request("request"))
        try:
            self.assertTrue(entered.wait(2))
            self.assertIs(self.trader.order_map["request"], self.order)
            self.trader._query_order.return_value = self.terminal(status="FILLED")
            self.trader._update_order_result(None)
        finally:
            release.set()
            self.finish(thread, errors)
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.order_map, {})
        self.trader._query_order.assert_called_once()

    def test_poll_blocked_while_cancel_completes_does_not_restore_order(self):
        entered, release = threading.Event(), threading.Event()
        def query(_):
            entered.set()
            if not release.wait(2):
                raise AssertionError("Poll release watchdog")
            return self.terminal(status="NEW")
        self.trader._query_order.side_effect = query
        thread, errors = self.launch(lambda: self.trader._update_order_result(None))
        try:
            self.assertTrue(entered.wait(2))
            self.trader._cancel_order.return_value = self.terminal()
            self.trader.cancel_request("request")
        finally:
            release.set()
            self.finish(thread, errors)
        self.callback.assert_called_once()
        self.assertEqual(self.trader.order_map, {})
        self.assertIsNone(self.trader.timer)

    def test_simultaneous_terminal_responses_claim_one_completion(self):
        barrier = threading.Barrier(2)
        def terminal_response(_):
            barrier.wait(timeout=2)
            return self.terminal()
        self.trader._cancel_order.side_effect = terminal_response
        self.trader._query_order.side_effect = terminal_response
        thread, errors = self.launch(lambda: self.trader.cancel_request("request"))
        try:
            self.trader._update_order_result(None)
        finally:
            self.finish(thread, errors)
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.asset, (10000, 0.25))
        self.assertEqual(self.trader.order_map, {})

    def test_late_poll_preserves_replacement_and_new_entry(self):
        replacement = {"order_id": 555, "result": {"state": "requested"}, "callback": Mock()}
        new_order = {"order_id": 666, "result": {"state": "requested"}, "callback": Mock()}
        def query(_):
            acquired = self.trader._order_lock.acquire(timeout=2)
            self.assertTrue(acquired, "Query ran under ownership lock")
            try:
                self.trader.order_map["request"] = replacement
                self.trader.order_map["new"] = new_order
            finally:
                self.trader._order_lock.release()
            return self.terminal(status="FILLED")
        self.trader._query_order.side_effect = query
        self.trader._update_order_result(None)
        self.assertIs(self.trader.order_map["request"], replacement)
        self.assertIs(self.trader.order_map["new"], new_order)
        self.callback.assert_not_called()
        self.assertEqual(self.order["result"]["state"], "requested")

    def test_late_cancel_preserves_replacement(self):
        replacement = {"order_id": 555, "result": {"state": "requested"}, "callback": Mock()}
        def cancel(_):
            acquired = self.trader._order_lock.acquire(timeout=2)
            self.assertTrue(acquired, "Cancel ran under ownership lock")
            try:
                self.trader.order_map["request"] = replacement
            finally:
                self.trader._order_lock.release()
            return self.terminal()
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
            self.trader.order_map["new"] = {"order_id": 555}
        self.callback.side_effect = callback
        self.trader._query_order.return_value = self.terminal()
        self.trader._update_order_result(None)
        self.assertEqual(self.trader.order_map, {"new": {"order_id": 555}})
        self.callback.assert_called_once()
        self.trader._cancel_order.assert_not_called()
        self.assertEqual(sum(timer.active for timer in self.timers), 1)

    def test_callback_failure_never_restores_completed_order(self):
        self.callback.side_effect = RuntimeError("client failure")
        self.trader._query_order.return_value = self.terminal()
        self.trader.order_map["new"] = {"order_id": 555}
        with self.assertRaisesRegex(RuntimeError, "client failure"):
            self.trader._update_order_result(None)
        self.assertNotIn("request", self.trader.order_map)
        self.assertIn("new", self.trader.order_map)
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(sum(timer.active for timer in self.timers), 1)
