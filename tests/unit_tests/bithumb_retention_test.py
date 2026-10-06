"""Known Bithumb orders: synthetic detail, manual timers, no exchange access."""
import copy
import threading
import unittest
from collections import deque
from unittest.mock import Mock, patch

from smtm.trader.bithumb_trader import BithumbTrader
from smtm.worker import Worker


class ManualTimer:
    def __init__(self, interval, callback):
        self.interval, self.callback = interval, callback
        self.active = self.cancelled = False

    def start(self):
        self.active = True

    def cancel(self):
        self.active, self.cancelled = False, True

    def fire(self):
        assert self.active
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


class BithumbRetentionTest(unittest.TestCase):
    def setUp(self):
        self.trader = BithumbTrader.__new__(BithumbTrader)
        self.trader._order_lock = threading.Lock()
        self.trader.logger = Mock()
        self.trader.market, self.trader.market_currency = "BTC", "KRW"
        self.trader.balance, self.trader.asset = 50000, (0, 0)
        self.trader.commission_ratio = 0.001
        self.trader.timer = None
        self.trader.worker = QueuedWorker()
        self.callback = Mock()
        self.order = {
            "order_id": "order-1", "callback": self.callback,
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
        data = {"order_status": "Cancel", "order_currency": "BTC", "payment_currency": "KRW",
                "type": "bid", "order_price": "10000", "order_qty": "1",
                "cancel_date": "1572497604668315", "transaction_date": "1572497603668315",
                "contract": [{"units": "0.25", "price": "9000",
                              "transaction_date": "1572497603668315"}]}
        data.update(changes)
        return {"status": "0000", "data": [data]}

    def assert_pending(self):
        self.assertIs(self.trader.order_map["request"], self.order)
        self.assertEqual(self.order["result"], {
            "state": "requested", "type": "buy", "price": 10000, "amount": 1})
        self.callback.assert_not_called()
        self.assertEqual(self.trader.balance, 50000)
        self.assertEqual(self.trader.asset, (0, 0))
        self.assertEqual(sum(t.active for t in self.timers), 1)

    def invalid_responses(self):
        yield from (None, {}, [], "bad", 1, {"status": "5600"})
        for data in (None, [], {}, [None], [self.terminal()["data"][0]] * 2, "bad"):
            yield {"status": "0000", "data": data}
        for status in (None, "", "5600", 0, True, []):
            response = self.terminal()
            response["status"] = status
            yield response
        response = self.terminal()
        del response["status"]
        yield response
        for field in ("order_currency", "payment_currency", "type", "order_qty", "contract", "order_status"):
            response = self.terminal()
            del response["data"][0][field]
            yield response
        for field, values in {
            "order_id": ["other", None, 1, True, []],
            "order_currency": ["ETH", None, []], "payment_currency": ["BTC", None, []],
            "type": ["ask", None, []],
            "order_status": ["Waiting", "Pending", "unknown", None, [], {}],
            "order_qty": [None, "", True, False, "0", "-1", "nan", "inf", "1e-400", "0.1", [], 10**400],
            "contract": [None, "", {}, [None], [{}]],
            "cancel_date": [True, "-1", "nan", "inf", "0", "1.5", "1e300", []],
        }.items():
            for value in values:
                yield self.terminal(**{field: value})
        for field in ("units", "price", "transaction_date"):
            response = self.terminal()
            del response["data"][0]["contract"][0][field]
            yield response
            for value in (None, "", True, False, "bad", "nan", "inf", "-1", "0", "1e-400", [], 10**400):
                response = self.terminal()
                response["data"][0]["contract"][0][field] = value
                yield response
        yield self.terminal(order_status="Completed")  # incomplete cumulative fill
        yield self.terminal(order_status="Completed", contract=[])
        response = self.terminal(order_qty="1e308")
        response["data"][0]["contract"][0]["units"] = "1e308"
        yield response  # nonfinite result price * amount

    def test_uncertain_cancel_and_poll_responses_retain_same_entry(self):
        for response in self.invalid_responses():
            for cancel in (False, True):
                with self.subTest(response=response, cancel=cancel):
                    self.trader._query_order.return_value = response
                    self.trader._cancel_order.return_value = {"status": "0000"}
                    if cancel:
                        self.trader.cancel_request("request")
                    else:
                        self.trader._update_order_result(None)
                    self.assert_pending()

    def test_retained_order_polls_again_and_eventually_settles(self):
        self.trader.cancel_request("request")
        self.assert_pending()
        first = self.trader.timer
        first.fire()
        self.trader.worker.run_next()
        self.assert_pending()
        self.assertTrue(first.cancelled)
        self.trader._query_order.return_value = self.terminal()
        self.trader.timer.fire()
        self.trader.worker.run_next()
        self.assertEqual(self.trader.order_map, {})
        self.assertIsNone(self.trader.timer)
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0.25)
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.asset, (10000, 0.25))

    def test_failed_cancel_can_still_confirm_full_fill(self):
        self.trader._cancel_order.return_value = {"status": "5600"}
        response = self.terminal(order_status="Completed", order_qty="0.25")
        self.trader._query_order.return_value = response
        self.trader.cancel_request("request")
        self.assertEqual(self.trader.order_map, {})
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0.25)

    def test_legacy_object_detail_with_matching_optional_id(self):
        response = self.terminal(order_id="order-1")
        response["data"] = response["data"][0]
        self.trader._query_order.return_value = response
        self.trader._update_order_result(None)
        self.assertEqual(self.trader.order_map, {})
        self.callback.assert_called_once()

    def test_multi_contract_sum_is_exact_and_preserves_positive_result_price(self):
        response = self.terminal(order_status="Completed", order_qty="0.3")
        contracts = response["data"][0]["contract"]
        contracts[0]["units"] = "0.1"
        contracts.append({"units": "0.2", "price": "12000", "transaction_date": "1572497603668315"})
        self.trader._query_order.return_value = response
        self.trader._update_order_result(None)
        self.callback.assert_called_once()
        result = self.callback.call_args[0][0]
        self.assertEqual((result["amount"], result["price"], result["state"]), (0.3, 10000, "done"))
        self.assertEqual(self.trader.balance, 46997)

    def test_inexact_contract_aggregation_remains_unresolved(self):
        for state in ("Completed", "Cancel"):
            with self.subTest(state=state):
                response = self.terminal(order_status=state, order_qty="0.1")
                contracts = response["data"][0]["contract"]
                contracts[0]["units"] = "0.1"
                contracts.append({"units": "1e-30", "price": "10000",
                                  "transaction_date": "1572497603668315"})
                self.trader._query_order.return_value = response
                self.trader._update_order_result(None)
                self.assert_pending()

    def test_price_fallback_to_order_price(self):
        self.order["result"]["price"] = None
        self.trader._query_order.return_value = self.terminal(order_price="8000")
        self.trader._update_order_result(None)
        self.assertEqual(self.callback.call_args[0][0]["price"], 8000)

    def test_absent_or_zero_price_fallback_to_weighted_execution(self):
        for initial in (None, 0):
            with self.subTest(initial=initial):
                self.order["result"]["price"] = initial
                self.trader.order_map["request"] = self.order
                response = self.terminal(order_price="0")
                response["data"][0]["contract"].append(
                    {"units": "0.25", "price": "11000", "transaction_date": "1572497603668315"})
                self.trader._query_order.return_value = response
                self.trader._update_order_result(None)
                self.assertEqual(self.callback.call_args[0][0]["price"], 10000)
                self.assertEqual(self.callback.call_args[0][0]["amount"], 0.5)

    def test_malformed_selected_prices_retain_order(self):
        for field in ("result", "order"):
            for value in (True, "bad", "nan", "inf", "-1", "1e-400", []):
                with self.subTest(field=field, value=value):
                    self.order["result"]["price"] = value if field == "result" else None
                    response = self.terminal(order_price=value if field == "order" else "10000")
                    self.trader._query_order.return_value = response
                    self.trader._update_order_result(None)
                    self.assertIs(self.trader.order_map["request"], self.order)
                    self.callback.assert_not_called()

    def test_zero_cancel_is_explicit_and_does_not_round_assets(self):
        self.order["result"]["price"] = None
        self.trader.asset = (777, 0.123456789)
        self.trader._query_order.return_value = self.terminal(contract=[], order_price="0")
        self.trader.cancel_request("request")
        self.callback.assert_called_once()
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0)
        self.assertEqual(self.trader.balance, 50000)
        self.assertEqual(self.trader.asset, (777, 0.123456789))

    def test_zero_cancel_missing_timestamp_is_retained(self):
        response = self.terminal(contract=[], cancel_date="")
        del response["data"][0]["transaction_date"]
        self.trader._query_order.return_value = response
        self.trader.cancel_request("request")
        self.assert_pending()

    def test_partial_sell_uses_executed_amount_only(self):
        self.order["result"]["type"] = "sell"
        self.trader.asset = (7000, 1)
        self.trader._query_order.return_value = self.terminal(type="ask")
        self.trader.cancel_request("request")
        self.assertEqual(self.trader.balance, 52498)
        self.assertEqual(self.trader.asset, (7000, 0.75))
        self.assertEqual(self.callback.call_args[0][0]["amount"], 0.25)

    def test_repeated_cancellation_and_late_poll_do_not_repeat_settlement(self):
        self.trader._query_order.return_value = self.terminal()
        self.trader.cancel_request("request")
        self.trader.cancel_request("request")
        self.trader._update_order_result(None)
        self.callback.assert_called_once()
        self.trader._cancel_order.assert_called_once_with("order-1")
        self.trader._query_order.assert_called_once_with("order-1")
        self.assertEqual(self.trader.balance, 47498)

    def test_new_entry_during_polling_is_not_lost(self):
        other = copy.copy(self.order)
        other["order_id"] = "new-order"
        def query(_):
            with self.trader._order_lock:
                self.trader.order_map["new"] = other
            return self.terminal()
        self.trader._query_order.side_effect = query
        self.trader._update_order_result(None)
        self.assertEqual(self.trader.order_map, {"new": other})
        self.callback.assert_called_once()
        self.assertEqual(sum(t.active for t in self.timers), 1)

    def test_late_response_cannot_remove_replacement(self):
        replacement = copy.copy(self.order)
        replacement["order_id"] = "replacement"
        def query(_):
            with self.trader._order_lock:
                self.trader.order_map["request"] = replacement
            return self.terminal()
        self.trader._query_order.side_effect = query
        self.trader.cancel_request("request")
        self.assertIs(self.trader.order_map["request"], replacement)
        self.callback.assert_not_called()
        self.assertEqual(self.trader.balance, 50000)

    def run_race(self, left, right):
        errors = []
        def run(action):
            try:
                action()
            except BaseException as err:
                errors.append(err)
        threads = [threading.Thread(target=run, args=(action,), daemon=True) for action in (left, right)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(3)
            self.assertFalse(thread.is_alive(), "race thread did not finish")
        self.assertEqual(errors, [])

    def test_cancel_vs_poll_claims_entry_once(self):
        barrier = threading.Barrier(2, timeout=2)
        def query(_):
            barrier.wait()
            return self.terminal()
        self.trader._query_order.side_effect = query
        self.run_race(lambda: self.trader.cancel_request("request"),
                      lambda: self.trader._update_order_result(None))
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47498)
        self.assertEqual(self.trader.asset, (10000, 0.25))
        self.assertEqual(self.trader.order_map, {})

    def test_cancel_vs_cancel_claims_entry_once(self):
        barrier = threading.Barrier(2, timeout=2)
        self.trader._query_order.side_effect = lambda _: (barrier.wait(), self.terminal())[1]
        self.run_race(lambda: self.trader.cancel_request("request"),
                      lambda: self.trader.cancel_request("request"))
        self.callback.assert_called_once()
        self.assertEqual(self.trader.balance, 47498)

    def test_distinct_concurrent_orders_preserve_both_accounting_updates(self):
        other = copy.deepcopy(self.order)
        other["order_id"] = "order-2"
        other["callback"] = Mock()
        self.trader.order_map["other"] = other
        barrier = threading.Barrier(2, timeout=2)
        self.trader._query_order.side_effect = lambda _: (barrier.wait(), self.terminal())[1]
        self.run_race(lambda: self.trader.cancel_request("request"),
                      lambda: self.trader.cancel_request("other"))
        self.callback.assert_called_once()
        other["callback"].assert_called_once()
        self.assertEqual(self.trader.balance, 44996)
        self.assertEqual(self.trader.asset, (10000, 0.5))

    def test_network_and_callback_are_outside_lock_and_callback_can_reenter(self):
        def check_lock():
            self.assertTrue(self.trader._order_lock.acquire(timeout=1))
            self.trader._order_lock.release()
        def cancel(_):
            check_lock()
        def query(_):
            check_lock()
            return self.terminal()
        def callback(result):
            check_lock()
            self.trader.cancel_request("request")
            self.trader._update_order_result(None)
        self.trader._cancel_order.side_effect = cancel
        self.trader._query_order.side_effect = query
        self.callback.side_effect = callback
        self.trader.cancel_request("request")
        self.callback.assert_called_once()

    def test_callback_failure_cannot_reaccount_claimed_entry(self):
        self.trader._query_order.return_value = self.terminal()
        self.callback.side_effect = RuntimeError("client failed")
        with self.assertRaisesRegex(RuntimeError, "client failed"):
            self.trader._update_order_result(None)
        self.trader._update_order_result(None)
        self.trader.cancel_request("request")
        self.callback.assert_called_once()
        self.assertEqual(self.trader.order_map, {})
        self.assertEqual(self.trader.balance, 47498)

    def test_accounting_failure_is_not_retried_for_claimed_entry(self):
        self.trader._query_order.return_value = self.terminal()
        self.trader._call_callback = Mock(side_effect=RuntimeError("accounting failed"))
        with self.assertRaisesRegex(RuntimeError, "accounting failed"):
            self.trader.cancel_request("request")
        self.trader.cancel_request("request")
        self.trader._update_order_result(None)
        self.trader._call_callback.assert_called_once()
        self.assertEqual(self.trader.order_map, {})

    def test_reentrant_callback_insertion_survives_and_keeps_polling(self):
        replacement = copy.copy(self.order)
        replacement["order_id"] = "replacement"
        def callback(result):
            with self.trader._order_lock:
                self.trader.order_map["request"] = replacement
        self.callback.side_effect = callback
        self.trader._query_order.return_value = self.terminal()
        self.trader._update_order_result(None)
        self.assertIs(self.trader.order_map["request"], replacement)
        self.callback.assert_called_once()
        self.assertEqual(sum(t.active for t in self.timers), 1)

    def test_cancel_sweep_does_not_copy_callback_owners(self):
        class Owner:
            def __deepcopy__(self, memo):
                raise AssertionError("callback owner must not be copied")
            def __call__(self, result):
                pass
        self.order["callback"] = Owner()
        self.trader.cancel_all_requests()
        self.assertIs(self.trader.order_map["request"], self.order)
        self.trader._cancel_order.assert_called_once_with("order-1")

    def test_cancel_finishing_after_poll_does_not_query_or_restore_retired_order(self):
        entered, release = threading.Event(), threading.Event()
        def cancel(_):
            entered.set()
            self.assertTrue(release.wait(2))
        self.trader._cancel_order.side_effect = cancel
        self.trader._query_order.return_value = self.terminal()
        errors = []
        def run():
            try:
                self.trader.cancel_request("request")
            except BaseException as err:
                errors.append(err)
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        try:
            self.assertTrue(entered.wait(2))
            self.trader._update_order_result(None)
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.trader._query_order.assert_called_once_with("order-1")
        self.callback.assert_called_once()
        self.assertEqual(self.trader.order_map, {})

    def test_missing_query_does_not_terminate_real_worker(self):
        worker = Worker("Bithumb-retention-test")
        worker.logger = Mock()
        self.trader.worker = worker
        processed = threading.Event()
        failures = []
        with patch("threading.excepthook", side_effect=failures.append):
            worker.start()
            thread = worker.thread
            try:
                worker.post_task({"runnable": self.trader._update_order_result})
                worker.post_task({"runnable": lambda _: processed.set()})
                self.assertTrue(processed.wait(2), "Worker died after missing response")
                self.assert_pending()
            finally:
                worker.post_task(None)
                thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(failures, [])

    def test_empty_map_stops_timer_and_unknown_cancel_is_noop(self):
        self.trader.order_map.clear()
        self.trader._start_timer()
        old_timer = self.trader.timer
        self.trader._update_order_result(None)
        self.assertIsNone(self.trader.timer)
        self.assertTrue(old_timer.cancelled)
        self.trader.cancel_request("unknown")
        self.trader._query_order.assert_not_called()
        self.trader._cancel_order.assert_not_called()
