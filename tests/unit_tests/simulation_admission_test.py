"""Synchronous simulation admission contract, using only local deterministic fakes.

Events and barriers establish race ordering. Timeouts are deadlock guards, never
the mechanism that makes a race pass. Simulation does not own a Worker; the one
explicit Worker test represents an independently queued producer.
"""
import threading
import unittest
from unittest.mock import Mock, patch

from smtm.trader.admission import AdmissionOutcome
from smtm.trader.simulation_trader import SimulationTrader
from smtm.worker import Worker


class SimulationAdmissionTest(unittest.TestCase):
    def setUp(self):
        self.threads = []
        self.releases = []
        self.workers = []

    def tearDown(self):
        for release in self.releases:
            release.set()
        for thread in self.threads:
            thread.join(3)
            self.assertFalse(thread.is_alive(), "Simulation caller did not finish")
        for worker in self.workers:
            worker.stop()

    def wait(self, event):
        self.assertTrue(event.wait(3), "Expected synchronization event was not set")

    def release_event(self):
        event = threading.Event()
        self.releases.append(event)
        return event

    def start(self, action):
        """Capture thread exceptions so failures cannot silently escape unittest."""
        result, errors = [], []

        def run():
            try:
                result.append(action())
            except BaseException as error:
                errors.append(error)

        thread = threading.Thread(target=run, daemon=True)
        self.threads.append(thread)
        thread.start()
        return thread, result, errors

    def join(self, call, expected_error=None):
        thread, result, errors = call
        thread.join(3)
        self.assertFalse(thread.is_alive(), "Simulation call blocked unexpectedly")
        if expected_error is None:
            self.assertEqual(errors, [])
        else:
            self.assertEqual(len(errors), 1)
            self.assertIs(errors[0], expected_error)
        return result

    @staticmethod
    def request(identifier="order", price=40, amount=1, kind="limit", side="buy"):
        return {
            "id": identifier, "type": side, "price": price,
            "amount": amount, "ord_type": kind,
        }

    def trader(self, budget=1000):
        trader = SimulationTrader(budget=budget, currency="BTC")
        trader.logger = Mock()
        trader.update_quote("BTC", 50)
        return trader

    def managed(self, budget=1000):
        trader = self.trader(budget)
        control = trader.get_admission_control()
        return trader, control, control.open_run()

    def assert_reached(self, fence):
        self.assertTrue(fence.done)
        self.assertEqual(fence.outcome, AdmissionOutcome.SUBMISSION_FENCE_REACHED)
        self.assertEqual(fence.wait(), AdmissionOutcome.SUBMISSION_FENCE_REACHED)
        self.assertIsNone(fence.failure)

    def assert_pending(self, fence):
        self.assertFalse(fence.done)
        self.assertEqual(fence.outcome, AdmissionOutcome.ADMISSION_CLOSED)
        self.assertIsNone(fence.failure)

    def assert_failed(self, fence, failure):
        self.assertTrue(fence.done)
        self.assertEqual(fence.outcome, AdmissionOutcome.EXECUTION_FAILURE)
        self.assertEqual(fence.wait(), AdmissionOutcome.EXECUTION_FAILURE)
        self.assertIs(fence.failure, failure)

    def test_accessor_is_inert_and_legacy_simulation_remains_synchronous(self):
        trader = self.trader()
        control = trader.get_admission_control()
        self.assertIsNotNone(control)
        self.assertIs(control, trader.get_admission_control())
        results = []
        self.assertIsNone(trader.send_request(
            [self.request(kind="market")], results.append))
        self.assertEqual(results[0]["state"], "done")
        self.assertEqual(trader.balance, 950)
        self.assertIsNone(trader.update_quote("BTC", 60))
        self.assertEqual(trader.quotes["BTC"], 60)

    def test_open_run_needs_no_worker_and_managed_calls_are_synchronous(self):
        with patch.object(Worker, "start", side_effect=AssertionError(
                "Simulation must not start a Worker")):
            trader, control, handle = self.managed()
            callers, results = [], []

            def callback(result):
                callers.append(threading.get_ident())
                results.append(result)

            self.assertTrue(handle.update_quote("BTC", 60))
            self.assertTrue(handle.submit([self.request(kind="market")], callback))
            self.assertEqual(callers, [threading.get_ident()])
            self.assertEqual(results[0]["price"], 60)
            self.assertEqual(trader.balance, 940)
            self.assertFalse(hasattr(trader, "worker"))
            self.assert_reached(handle.close())

    def test_managed_mode_permanently_rejects_unbound_legacy_calls(self):
        trader, control, handle = self.managed()
        callback = Mock()
        for closed in (False, True):
            with self.subTest(closed=closed):
                if closed:
                    self.assert_reached(handle.close())
                with self.assertRaises(RuntimeError):
                    trader.send_request([self.request()], callback)
                with self.assertRaises(RuntimeError):
                    trader.update_quote("BTC", 1)
        callback.assert_not_called()
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.quotes["BTC"], 50)
        self.assertEqual(trader.pending_orders, {})

    def test_close_is_idempotent_rejects_stale_work_and_does_not_synthesize_results(self):
        trader, control, handle = self.managed()
        with self.assertRaises(RuntimeError):
            control.open_run()
        fence = handle.close()
        self.assert_reached(fence)
        self.assert_reached(handle.close())
        callback = Mock()
        self.assertFalse(handle.submit([self.request()], callback))
        self.assertFalse(handle.update_quote("BTC", 1))
        callback.assert_not_called()
        self.assertEqual(trader.get_submission_status(), {})
        self.assertEqual(trader.quotes["BTC"], 50)
        newer = control.open_run()
        self.assertIsNot(newer, handle)
        self.assertFalse(handle.submit([self.request("stale")], callback))
        self.assertFalse(handle.update_quote("BTC", 2))
        self.assertTrue(newer.submit([self.request("new", kind="market")], callback))
        self.assertEqual(callback.call_count, 1)
        self.assert_reached(newer.close())
        self.assert_reached(fence)

    def test_initial_opt_in_refuses_legacy_pending_work_without_activating(self):
        trader = self.trader()
        control = trader.get_admission_control()
        original = []
        trader.send_request([self.request("legacy")], original.append)
        with self.assertRaises(RuntimeError):
            control.open_run()
        self.assertIsNone(trader.update_quote("BTC", 45))
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        trader.cancel_request("legacy")
        self.assertEqual([result["msg"] for result in original], ["success", "canceled"])
        self.assert_reached(control.open_run().close())

    def test_constructor_currency_with_reentrant_hash_is_rejected_before_opt_in(self):
        hashed, handles, callback = threading.Event(), [], Mock()

        class Currency(str):
            def __hash__(value):
                hashed.set()
                handles[0].close()
                return str.__hash__(value)

        trader = SimulationTrader(budget=1000, currency=Currency("BTC"))
        trader.logger = Mock()
        trader.update_quote("BTC", 50)
        control = trader.get_admission_control()

        def attempt_managed_fill():
            handles.append(control.open_run())
            return handles[0].submit([self.request(kind="market")], callback)

        thread, results, errors = self.start(attempt_managed_fill)
        thread.join(3)
        self.assertFalse(thread.is_alive(), "Constructor currency must not reenter a held lock")
        self.assertEqual(results, [])
        self.assertEqual(handles, [])
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], RuntimeError)
        self.assertFalse(hashed.is_set())
        callback.assert_not_called()
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.order_history, [])
        self.assertIsNone(trader.send_request([], callback))
        self.assertIsNone(trader.update_quote("BTC", 60))
        trader.currency = "BTC"
        self.assert_reached(control.open_run().close())

    def test_initial_opt_in_rejects_custom_or_nonfinite_inherited_state_without_hooks(self):
        hooks = []

        class Number:
            def __float__(value):
                hooks.append("float")
                raise AssertionError("Numeric conversion hook must not run")

            def __ge__(value, other):
                hooks.append("compare")
                raise AssertionError("Numeric comparison hook must not run")

        class Key(str):
            def __hash__(value):
                hooks.append("hash")
                return str.__hash__(value)

        class Mapping(dict):
            def items(value):
                hooks.append("items")
                raise AssertionError("Custom mapping hook must not run")

            def __bool__(value):
                hooks.append("bool")
                raise AssertionError("Custom mapping truth hook must not run")

        class Holding(tuple):
            def __len__(value):
                hooks.append("len")
                raise AssertionError("Custom holding hook must not run")

        cases = (
            ("balance object", "balance", Number()),
            ("commission object", "commission_ratio", Number()),
            ("quote object", "quotes", {"BTC": Number()}),
            ("asset object", "assets", {"BTC": (Number(), 1)}),
            ("quote custom key", "quotes", {Key("BTC"): 50}),
            ("asset custom key", "assets", {Key("BTC"): (50, 1)}),
            ("quote custom map", "quotes", Mapping({"BTC": 50})),
            ("asset custom map", "assets", Mapping({"BTC": (50, 1)})),
            ("pending custom map", "pending_orders", Mapping()),
            ("custom holding", "assets", {"BTC": Holding((50, 1))}),
            ("negative balance", "balance", -1),
            ("nan balance", "balance", float("nan")),
            ("infinite balance", "balance", float("inf")),
            ("boolean balance", "balance", True),
            ("negative asset", "assets", {"BTC": (50, -1)}),
            ("infinite quote", "quotes", {"BTC": float("inf")}),
            ("zero quote", "quotes", {"BTC": 0}),
        )
        for name, attribute, value in cases:
            with self.subTest(state=name):
                trader = self.trader()
                control = trader.get_admission_control()
                setattr(trader, attribute, value)
                hooks.clear()
                with self.assertRaises(RuntimeError):
                    control.open_run()
                self.assertEqual(hooks, [])
                # A refused opt-in must leave legacy mode usable. Restore the
                # deliberately invalid test fixture before exercising it.
                trader.balance, trader.commission_ratio = 1000, 0
                trader.assets, trader.quotes, trader.pending_orders = {}, {"BTC": 50}, {}
                results = []
                self.assertIsNone(trader.send_request(
                    [self.request(kind="market")], results.append))
                self.assertEqual(results[0]["state"], "done")
                self.assert_reached(control.open_run().close())

    def test_initial_opt_in_accepts_plain_finite_existing_account_state(self):
        trader = self.trader()
        trader.assets = {"BTC": (50, 1), "ETH": [5.5, 2], "EMPTY": (0, 0)}
        trader.quotes = {"BTC": 50, "ETH": 5.5}
        before = trader.get_account_info()
        handle = trader.get_admission_control().open_run()
        after = trader.get_account_info()
        for key in ("balance", "asset", "quote", "reserved_balance", "reserved_asset"):
            self.assertEqual(after[key], before[key])
        self.assert_reached(handle.close())

    def test_initial_opt_in_refuses_each_active_legacy_callback(self):
        for source in ("submit", "quote", "cancel"):
            with self.subTest(source=source):
                trader = self.trader()
                control = trader.get_admission_control()
                entered, release = threading.Event(), self.release_event()

                def callback(result):
                    if result["state"] == "done":
                        entered.set()
                        self.wait(release)

                if source == "submit":
                    action = lambda: trader.send_request(
                        [self.request(kind="market")], callback)
                else:
                    trader.send_request([self.request()], callback)
                    action = (lambda: trader.update_quote("BTC", 39)) if source == "quote" \
                        else (lambda: trader.cancel_request("order"))
                call = self.start(action)
                self.wait(entered)
                with self.assertRaises(RuntimeError):
                    control.open_run()
                release.set()
                self.join(call)
                self.assert_reached(control.open_run().close())

    def test_close_from_first_batch_callback_rejects_later_request_and_self_waits_safely(self):
        trader, control, handle = self.managed()
        observed, results = [], []

        def callback(result):
            results.append(result)
            fence = handle.close()
            observed.append((fence.done, fence.wait()))

        call = self.start(lambda: handle.submit([
            self.request("first", kind="market"),
            self.request("second", kind="market"),
        ], callback))
        self.assertEqual(self.join(call), [True])
        self.assertEqual(observed, [(False, AdmissionOutcome.ADMISSION_CLOSED)])
        self.assertEqual([result["request"]["id"] for result in results], ["first"])
        self.assertEqual(trader.balance, 950)
        self.assertEqual(trader.get_submission_status()["first"]["state"], "settled")
        self.assertEqual(trader.get_submission_status()["second"]["state"], "not_dispatched")
        self.assert_reached(handle.close())

    def test_close_during_request_preparation_prevents_any_accounting_or_callback(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        validate = trader._validate_request
        callback = Mock()

        def preparing(request, kind):
            entered.set()
            self.wait(release)
            return validate(request, kind)

        with patch.object(trader, "_validate_request", side_effect=preparing):
            call = self.start(lambda: handle.submit(
                [self.request(kind="market")], callback))
            self.wait(entered)
            self.assertEqual(trader.get_submission_status()["order"]["state"], "preparing")
            fence = handle.close()
            self.assert_pending(fence)
            release.set()
            self.assertEqual(self.join(call), [True])
        self.assert_reached(fence)
        callback.assert_not_called()
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.assets, {})
        self.assertEqual(trader.order_history, [])
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.get_submission_status()["order"]["state"], "not_dispatched")
        self.assertFalse(trader.get_submission_status()["order"]["callback_failed"])

    def test_close_during_quote_conversion_preserves_quote_and_pending_order(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []
        handle.submit([self.request()], results.append)

        class Price:
            def __float__(price):
                entered.set()
                self.wait(release)
                return 39.0

        call = self.start(lambda: handle.update_quote("BTC", Price()))
        self.wait(entered)
        fence = handle.close()
        self.assert_pending(fence)
        release.set()
        self.assertEqual(self.join(call), [True])
        self.assert_reached(fence)
        self.assertEqual(trader.quotes["BTC"], 50)
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assertEqual([result["state"] for result in results], ["requested"])

    def test_execution_error_during_preparation_fails_fence_without_any_fill(self):
        trader, control, handle = self.managed()
        failure, callback = RuntimeError("preparation failed"), Mock()
        with patch.object(trader, "_validate_request", side_effect=failure):
            with self.assertRaises(RuntimeError) as raised:
                handle.submit([self.request(kind="market")], callback)
        self.assertIs(raised.exception, failure)
        self.assert_failed(handle.close(), failure)
        callback.assert_not_called()
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.assets, {})
        self.assertEqual(trader.order_history, [])
        self.assertFalse(handle.update_quote("BTC", 39))
        self.assert_reached(control.open_run().close())

    def test_callbacks_release_locks_and_fence_waits_for_callback_return(self):
        trader, control, handle = self.managed()
        callback_entered, inspected = threading.Event(), threading.Event()
        release = self.release_event()
        fences, account, status = [], [], []

        def callback(result):
            callback_entered.set()
            self.wait(inspected)
            self.wait(release)

        call = self.start(lambda: handle.submit(
            [self.request(kind="market")], callback))
        self.wait(callback_entered)

        def inspect_and_close():
            account.append(trader.get_account_info())
            status.append(trader.get_submission_status())
            fences.append(handle.close())
            inspected.set()

        inspector = self.start(inspect_and_close)
        self.wait(inspected)
        self.assertEqual(account[0]["balance"], 950)
        self.assertEqual(status[0]["order"]["state"], "settling")
        self.assert_pending(fences[0])
        with self.assertRaises(RuntimeError):
            control.open_run()
        waiter_started = threading.Event()

        def wait_for_fence():
            waiter_started.set()
            return fences[0].wait()

        waiter = self.start(wait_for_fence)
        self.wait(waiter_started)
        self.assert_pending(fences[0])
        release.set()
        self.assertEqual(self.join(call), [True])
        self.join(inspector)
        self.assertEqual(self.join(waiter), [AdmissionOutcome.SUBMISSION_FENCE_REACHED])
        self.assert_reached(fences[0])

    def test_close_during_quote_callback_preserves_next_unclaimed_entry(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "done" and result["request"]["id"] == "first":
                entered.set()
                self.wait(release)

        self.assertTrue(handle.submit([
            self.request("first"), self.request("second"),
        ], callback))
        quote = self.start(lambda: handle.update_quote("BTC", 39))
        self.wait(entered)
        fence = handle.close()
        self.assert_pending(fence)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assertEqual(list(trader.pending_orders), ["second"])
        with self.assertRaises(RuntimeError):
            control.open_run()
        release.set()
        self.assertEqual(self.join(quote), [True])
        self.assert_reached(fence)
        self.assertEqual(trader.balance, 961)
        self.assertEqual(trader.assets["BTC"], (39, 1))
        self.assertEqual([result["request"]["id"] for result in results
                          if result["state"] == "done"], ["first"])
        status = trader.get_submission_status()
        self.assertEqual(status["first"]["state"], "settled")
        self.assertEqual(status["second"]["state"], "pending")
        trader.cancel_request("second")
        self.assertEqual(results[-1]["msg"], "canceled")
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        self.assertEqual(trader.get_submission_status()["second"]["state"], "settled")

    def test_quote_callback_can_close_reentrantly_without_claiming_remaining_entries(self):
        trader, control, handle = self.managed()
        results, observed = [], []

        def callback(result):
            results.append(result)
            if result["state"] == "done":
                observed.append(handle.close().wait())

        handle.submit([self.request("first"), self.request("second")], callback)
        call = self.start(lambda: handle.update_quote("BTC", 39))
        self.assertEqual(self.join(call), [True])
        self.assertEqual(observed, [AdmissionOutcome.ADMISSION_CLOSED])
        self.assertEqual(list(trader.pending_orders), ["second"])
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assert_reached(handle.close())

    def test_new_run_quotes_do_not_fill_previous_run_orders(self):
        trader, control, old = self.managed()
        old_results, new_results = [], []
        old.submit([self.request("old")], old_results.append)
        self.assert_reached(old.close())
        new = control.open_run()
        self.assertTrue(new.submit([self.request("new", price=35)], new_results.append))
        self.assertFalse(old.update_quote("BTC", 1))
        self.assertTrue(new.update_quote("BTC", 30))
        self.assertEqual([result["state"] for result in old_results], ["requested"])
        self.assertEqual([result["state"] for result in new_results], ["requested", "done"])
        self.assertEqual(list(trader.pending_orders), ["old"])
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assertEqual(trader.balance, 970)
        trader.cancel_request("old")
        self.assertEqual(old_results[-1]["msg"], "canceled")
        self.assertEqual(len(new_results), 2)
        self.assert_reached(new.close())

    def test_terminal_callback_failure_is_retained_and_never_retried(self):
        trader, control, handle = self.managed()
        failure = RuntimeError("simulation callback failure")
        callback = Mock(side_effect=failure)
        with self.assertRaises(RuntimeError) as raised:
            handle.submit([self.request(kind="market")], callback)
        self.assertIs(raised.exception, failure)
        fence = handle.close()
        self.assert_failed(fence, failure)
        self.assert_failed(handle.close(), failure)
        self.assertEqual(trader.balance, 950)
        self.assertEqual(len(trader.order_history), 1)
        record = trader.get_submission_status()["order"]
        self.assertEqual(record["state"], "settlement_failed")
        self.assertTrue(record["callback_failed"])
        self.assertFalse(handle.submit([self.request("retry")], callback))
        trader.cancel_request("order")
        self.assertEqual(callback.call_count, 1)
        self.assert_reached(control.open_run().close())

    def test_failure_fence_does_not_allow_new_run_while_another_callback_is_active(self):
        trader, control, handle = self.managed()
        entered1, entered2 = threading.Event(), threading.Event()
        release1, release2 = self.release_event(), self.release_event()
        failure1, failure2 = RuntimeError("first callback"), RuntimeError("second callback")

        def callback1(result):
            entered1.set()
            self.wait(release1)
            raise failure1

        def callback2(result):
            entered2.set()
            self.wait(release2)
            raise failure2

        call1 = self.start(lambda: handle.submit(
            [self.request("first", kind="market")], callback1))
        self.wait(entered1)
        call2 = self.start(lambda: handle.submit(
            [self.request("second", kind="market")], callback2))
        self.wait(entered2)
        fence = handle.close()
        self.assert_pending(fence)
        release1.set()
        self.join(call1, expected_error=failure1)
        self.assert_failed(fence, failure1)
        with self.assertRaises(RuntimeError):
            control.open_run()
        release2.set()
        self.join(call2, expected_error=failure2)
        self.assert_failed(fence, failure1)
        self.assert_reached(control.open_run().close())
        self.assertEqual(trader.balance, 900)
        for record in trader.get_submission_status().values():
            self.assertEqual(record["state"], "settlement_failed")
            self.assertTrue(record["callback_failed"])

    def test_quote_callback_failure_retains_unclaimed_order_and_original_owner(self):
        trader, control, handle = self.managed()
        failure = RuntimeError("fill callback failed")
        first, second = [], []

        def callback(result):
            first.append(result)
            if result["state"] == "done":
                raise failure

        handle.submit([self.request("first")], callback)
        handle.submit([self.request("second")], second.append)
        with self.assertRaises(RuntimeError) as raised:
            handle.update_quote("BTC", 39)
        self.assertIs(raised.exception, failure)
        self.assert_failed(handle.close(), failure)
        self.assertEqual(list(trader.pending_orders), ["second"])
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assertEqual(trader.balance, 961)
        self.assertEqual(trader.get_submission_status()["first"]["state"], "settlement_failed")
        trader.cancel_all_requests()
        self.assertEqual(second[-1]["msg"], "canceled")
        self.assertEqual(len(first), 2)

    def test_pending_callback_failure_keeps_reservation_and_sticky_failure_flag(self):
        trader, control, handle = self.managed()
        failure = RuntimeError("requested callback failed")
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "requested":
                raise failure

        with self.assertRaises(RuntimeError) as raised:
            handle.submit([self.request()], callback)
        self.assertIs(raised.exception, failure)
        self.assert_failed(handle.close(), failure)
        self.assertEqual(list(trader.pending_orders), ["order"])
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assertEqual(trader.get_submission_status()["order"]["state"], "pending")
        self.assertTrue(trader.get_submission_status()["order"]["callback_failed"])
        trader.cancel_request("order")
        self.assertEqual([result["msg"] for result in results], ["success", "canceled"])
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        self.assertTrue(trader.get_submission_status()["order"]["callback_failed"])
        self.assert_failed(handle.close(), failure)

    def test_cancellation_callback_failure_retains_failure_without_repeating_cancellation(self):
        trader, control, handle = self.managed()
        failure, results = RuntimeError("cancel callback failed"), []

        def callback(result):
            results.append(result)
            if result["msg"] == "canceled":
                raise failure

        handle.submit([self.request()], callback)
        with self.assertRaises(RuntimeError) as raised:
            trader.cancel_request("order")
        self.assertIs(raised.exception, failure)
        self.assert_failed(handle.close(), failure)
        self.assertEqual(trader.get_submission_status()["order"]["state"], "settlement_failed")
        self.assertTrue(trader.get_submission_status()["order"]["callback_failed"])
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        self.assertEqual(trader.balance, 1000)
        trader.cancel_request("order")
        trader.cancel_all_requests()
        self.assertEqual(len(results), 2)
        self.assertEqual(len(trader.order_history), 1)

    def test_reentrant_cancel_from_requested_callback_delivers_terminal_after_ack(self):
        trader, control, handle = self.managed()
        observed, fences = [], []

        def callback(result):
            observed.append((result["state"], "entered"))
            if result["state"] == "requested":
                trader.cancel_request("order")
                fences.append(handle.close())
                self.assertEqual(fences[0].wait(), AdmissionOutcome.ADMISSION_CLOSED)
            observed.append((result["state"], "returned"))

        call = self.start(lambda: handle.submit([self.request()], callback))
        self.assertEqual(self.join(call), [True])
        self.assertEqual(observed, [
            ("requested", "entered"), ("requested", "returned"),
            ("done", "entered"), ("done", "returned"),
        ])
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        self.assertEqual(trader.order_history[0]["msg"], "canceled")
        self.assert_reached(fences[0])

    def test_external_cancel_during_requested_callback_completes_in_ack_order(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        observed, canceled = [], threading.Event()

        def callback(result):
            observed.append((result["state"], "entered"))
            if result["state"] == "requested":
                entered.set()
                self.wait(release)
            observed.append((result["state"], "returned"))
            if result["msg"] == "canceled":
                canceled.set()

        submit = self.start(lambda: handle.submit([self.request()], callback))
        self.wait(entered)
        fence = handle.close()
        self.assert_pending(fence)
        cancel = self.start(lambda: trader.cancel_request("order"))
        # Terminal delivery may be deferred, rather than deadlock a callback
        # that joins the canceling thread. The admitted submit still owns it.
        self.join(cancel)
        self.assertFalse(canceled.is_set())
        self.assert_pending(fence)
        release.set()
        self.assertEqual(self.join(submit), [True])
        self.wait(canceled)
        self.assertEqual(observed, [
            ("requested", "entered"), ("requested", "returned"),
            ("done", "entered"), ("done", "returned"),
        ])
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.balance, 1000)
        self.assert_reached(fence)

    def test_callback_mutated_result_cannot_change_lifecycle_or_deferred_cancel_owner(self):
        trader, control, handle = self.managed()
        states = []

        def callback(result):
            states.append(result["state"])
            if result["state"] == "requested":
                trader.cancel_request("order")
                result.clear()
            else:
                result["state"] = "requested"
                result.pop("request")

        self.assertTrue(handle.submit([self.request()], callback))
        self.assertEqual(states, ["requested", "done"])
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        self.assertEqual(trader.get_submission_status()["order"], {
            "state": "settled", "callback_failed": False,
        })
        self.assertEqual(trader.order_history[0]["state"], "done")
        self.assertEqual(trader.order_history[0]["request"]["id"], "order")
        self.assert_reached(handle.close())

    def test_callback_removing_terminal_result_keys_does_not_fail_execution(self):
        trader, control, handle = self.managed()
        self.assertTrue(handle.submit([self.request(kind="market")], lambda result: result.clear()))
        self.assertEqual(trader.get_submission_status()["order"]["state"], "settled")
        self.assertEqual(trader.order_history[0]["state"], "done")
        self.assertEqual(trader.balance, 950)
        self.assert_reached(handle.close())

    def test_quote_does_not_overtake_inflight_requested_callback(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "requested":
                entered.set()
                self.wait(release)

        call = self.start(lambda: handle.submit([self.request()], callback))
        self.wait(entered)
        self.assertTrue(handle.update_quote("BTC", 39))
        self.assertEqual([result["state"] for result in results], ["requested"])
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        release.set()
        self.assertEqual(self.join(call), [True])
        self.assertEqual([result["state"] for result in results], ["requested", "done"])
        self.assertEqual(trader.balance, 961)
        self.assertTrue(handle.update_quote("BTC", 39))
        self.assertEqual(len(results), 2)
        self.assert_reached(handle.close())

    def test_reentrant_quote_fills_after_requested_callback_returns_once(self):
        trader, control, handle = self.managed()
        observed = []

        def callback(result):
            observed.append((result["state"], "entered"))
            if result["state"] == "requested":
                self.assertTrue(handle.update_quote("BTC", 39))
            observed.append((result["state"], "returned"))

        call = self.start(lambda: handle.submit([self.request()], callback))
        self.assertEqual(self.join(call), [True])
        self.assertEqual(observed, [
            ("requested", "entered"), ("requested", "returned"),
            ("done", "entered"), ("done", "returned"),
        ])
        self.assertEqual(trader.balance, 961)
        self.assertEqual(trader.pending_orders, {})
        self.assert_reached(handle.close())

    def test_close_before_requested_callback_returns_rejects_deferred_fill(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "requested":
                entered.set()
                self.wait(release)

        call = self.start(lambda: handle.submit([self.request()], callback))
        self.wait(entered)
        self.assertTrue(handle.update_quote("BTC", 39))
        fence = handle.close()
        self.assert_pending(fence)
        release.set()
        self.assertEqual(self.join(call), [True])
        self.assert_reached(fence)
        self.assertEqual([result["state"] for result in results], ["requested"])
        self.assertEqual(list(trader.pending_orders), ["order"])
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)

    def test_requested_callback_failure_prevents_deferred_fill_and_keeps_owner(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        failure, results = RuntimeError("requested callback failed"), []

        def callback(result):
            results.append(result)
            if result["state"] == "requested":
                entered.set()
                self.wait(release)
                raise failure

        call = self.start(lambda: handle.submit([self.request()], callback))
        self.wait(entered)
        self.assertTrue(handle.update_quote("BTC", 39))
        release.set()
        self.join(call, expected_error=failure)
        self.assert_failed(handle.close(), failure)
        self.assertEqual([result["state"] for result in results], ["requested"])
        self.assertEqual(list(trader.pending_orders), ["order"])
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assertEqual(trader.get_submission_status()["order"], {
            "state": "pending", "callback_failed": True,
        })
        trader.cancel_request("order")
        self.assertEqual(results[-1]["msg"], "canceled")
        self.assertEqual(trader.balance, 1000)

    def test_deferred_cancellation_wins_over_crossing_quote_before_requested_returns(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "requested":
                entered.set()
                self.wait(release)

        call = self.start(lambda: handle.submit([self.request()], callback))
        self.wait(entered)
        self.assertTrue(handle.update_quote("BTC", 39))
        trader.cancel_request("order")
        release.set()
        self.assertEqual(self.join(call), [True])
        self.assertEqual([result["msg"] for result in results], ["success", "canceled"])
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.assets, {})
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(len(trader.order_history), 1)
        self.assert_reached(handle.close())

    def test_deferred_cancel_keeps_priority_in_gap_after_requested_callback_returns(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []
        cancel_managed = trader._cancel_managed

        def callback(result):
            results.append(result)
            if result["state"] == "requested":
                trader.cancel_request("order")

        def pause_deferred_cancel(request_id, expected=None):
            if expected is not None:
                # The initial callback has returned and ack_pending is false,
                # but the already-requested cancel has not claimed the entry.
                entered.set()
                self.wait(release)
            return cancel_managed(request_id, expected)

        with patch.object(trader, "_cancel_managed", side_effect=pause_deferred_cancel):
            call = self.start(lambda: handle.submit([self.request()], callback))
            self.wait(entered)
            self.assertTrue(handle.update_quote("BTC", 39))
            self.assertEqual([result["state"] for result in results], ["requested"])
            self.assertEqual(trader.balance, 1000)
            self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
            release.set()
            self.assertEqual(self.join(call), [True])
        self.assertEqual([result["msg"] for result in results], ["success", "canceled"])
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.assets, {})
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(len(trader.order_history), 1)
        self.assert_reached(handle.close())

    def test_multiple_crossing_quotes_during_requested_callback_fill_only_once(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "requested":
                entered.set()
                self.wait(release)

        call = self.start(lambda: handle.submit([self.request()], callback))
        self.wait(entered)
        self.assertTrue(handle.update_quote("BTC", 39))
        self.assertTrue(handle.update_quote("BTC", 35))
        self.assertEqual(len(results), 1)
        release.set()
        self.assertEqual(self.join(call), [True])
        self.assertEqual([result["state"] for result in results], ["requested", "done"])
        self.assertEqual(results[-1]["price"], 39)
        self.assertEqual(trader.balance, 961)
        self.assertEqual(trader.quotes["BTC"], 35)
        self.assertEqual(len(trader.order_history), 1)
        self.assert_reached(handle.close())

    def test_managed_logical_ids_cannot_replay_or_replace_original_record(self):
        trader, control, old = self.managed()
        original, replacement = Mock(), Mock()
        old.submit([self.request(kind="market")], original)
        self.assert_reached(old.close())
        new = control.open_run()
        self.assertTrue(new.submit([self.request(kind="market")], replacement))
        replacement.assert_not_called()
        self.assertEqual(original.call_count, 1)
        self.assertEqual(trader.balance, 950)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.get_submission_status()["order"]["state"], "settled")
        self.assert_reached(new.close())

    def test_pending_request_and_callback_result_mutation_do_not_replace_original_owner(self):
        trader, control, handle = self.managed()
        request, results = self.request(), []
        request["metadata"] = {"owner": "original"}
        handle.submit([request], results.append)
        request["price"] = 1
        request["metadata"]["owner"] = "caller changed"
        results[0]["request"]["price"] = 2
        results[0]["request"]["metadata"]["owner"] = "callback changed"
        self.assert_reached(handle.close())
        trader.cancel_request("order")
        self.assertEqual(results[-1]["request"]["price"], 40)
        self.assertEqual(results[-1]["request"]["metadata"], {"owner": "original"})
        self.assertEqual(trader.order_history[0]["request"]["metadata"], {"owner": "original"})

    def test_custom_metadata_is_rejected_before_deepcopy_hook_or_accounting(self):
        trader, control, handle = self.managed()
        copied, callback = threading.Event(), Mock()

        class Metadata:
            def __deepcopy__(value, memo):
                copied.set()
                handle.close()
                return value

        request = self.request(kind="market")
        request["metadata"] = {"nested": [Metadata()]}
        call = self.start(lambda: handle.submit([request], callback))
        thread, results, errors = call
        thread.join(3)
        self.assertFalse(thread.is_alive(), "Custom metadata must not deadlock admission")
        self.assertEqual(results, [])
        self.assertEqual(len(errors), 1)
        self.assertIsInstance(errors[0], TypeError)
        self.assertFalse(copied.is_set())
        callback.assert_not_called()
        self.assert_failed(handle.close(), errors[0])
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.assets, {})
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.order_history, [])
        self.assertEqual(trader.get_submission_status(), {})

    def test_custom_string_hash_hooks_are_not_run_by_quote_or_cancel(self):
        trader, control, handle = self.managed()
        hashed, results = threading.Event(), []

        class CustomString(str):
            def __hash__(value):
                hashed.set()
                handle.close()
                return str.__hash__(value)

        handle.submit([self.request()], results.append)

        def call_invalid_inputs():
            accepted = handle.update_quote(CustomString("BTC"), 39)
            trader.cancel_request(CustomString("order"))
            return accepted

        call = self.start(call_invalid_inputs)
        self.assertEqual(self.join(call), [True])
        self.assertFalse(hashed.is_set())
        self.assertEqual(trader.quotes["BTC"], 50)
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 40)
        self.assertEqual([result["state"] for result in results], ["requested"])
        self.assertEqual(trader.get_submission_status()["order"]["state"], "pending")
        self.assert_reached(handle.close())

    def test_plain_nested_metadata_is_snapshotted_and_tuple_is_normalized(self):
        trader, control, handle = self.managed()
        request, results = self.request(), []
        request["metadata"] = {"items": ({"owner": "original"}, [1, None, True])}
        self.assertTrue(handle.submit([request], results.append))
        request["metadata"]["items"][0]["owner"] = "changed"
        request["metadata"]["items"][1].append("changed")
        trader.cancel_request("order")
        self.assertEqual(results[-1]["request"]["metadata"], {
            "items": [{"owner": "original"}, [1, None, True]],
        })
        self.assert_reached(handle.close())

    def test_bound_cancel_of_old_entry_fails_current_call_and_keeps_original_owner(self):
        trader, control, old = self.managed()
        failure, original, replacement = RuntimeError("old cancel callback"), [], Mock()

        def callback(result):
            original.append(result)
            if result["msg"] == "canceled":
                raise failure

        old.submit([self.request("old")], callback)
        old_fence = old.close()
        self.assert_reached(old_fence)
        current = control.open_run()
        with self.assertRaises(RuntimeError) as raised:
            current.submit([{"id": "old", "type": "cancel"}], replacement)
        self.assertIs(raised.exception, failure)
        self.assert_failed(current.close(), failure)
        self.assert_reached(old_fence)
        replacement.assert_not_called()
        self.assertEqual([result["msg"] for result in original], ["success", "canceled"])
        self.assertEqual(trader.get_submission_status()["old"], {
            "state": "settlement_failed", "callback_failed": True,
        })
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.balance, 1000)
        self.assertFalse(current.submit([self.request("new", kind="market")], replacement))
        self.assert_reached(control.open_run().close())

    def test_direct_cancel_of_old_entry_does_not_fail_unrelated_current_run(self):
        trader, control, old = self.managed()
        failure, original, current_results = RuntimeError("old cancel callback"), [], []

        def callback(result):
            original.append(result)
            if result["msg"] == "canceled":
                raise failure

        old.submit([self.request("old")], callback)
        old_fence = old.close()
        self.assert_reached(old_fence)
        current = control.open_run()
        with self.assertRaises(RuntimeError) as raised:
            trader.cancel_request("old")
        self.assertIs(raised.exception, failure)
        self.assertTrue(current.submit(
            [self.request("current", kind="market")], current_results.append))
        self.assert_reached(current.close())
        self.assert_reached(old_fence)
        self.assertEqual([result["msg"] for result in original], ["success", "canceled"])
        self.assertEqual(len(current_results), 1)
        self.assertEqual(current_results[0]["state"], "done")
        self.assertEqual(trader.get_submission_status()["old"], {
            "state": "settlement_failed", "callback_failed": True,
        })
        self.assertEqual(trader.balance, 950)

    def test_managed_validation_rejection_is_a_local_settled_result(self):
        trader, control, handle = self.managed()
        results = []
        self.assertTrue(handle.submit([
            self.request("bad-amount", amount=0, kind="market"),
            self.request("bad-price", price=-1),
            self.request("bad-kind", kind="unsupported"),
        ], results.append))
        self.assertEqual([result["state"] for result in results], ["failed"] * 3)
        for record in trader.get_submission_status().values():
            self.assertEqual(record, {"state": "settled", "callback_failed": False})
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.pending_orders, {})
        self.assert_reached(handle.close())

    def test_invalid_unhashable_ids_are_rejected_without_execution_failure(self):
        for identifier in ([], {}, ["order"], {"id": "order"}):
            with self.subTest(identifier=identifier):
                trader, control, handle = self.managed()
                results = []
                self.assertTrue(handle.submit(
                    [self.request(identifier, kind="market")], results.append))
                self.assertEqual(len(results), 1)
                self.assertEqual(results[0]["state"], "failed")
                self.assertEqual(results[0]["msg"], "잘못된 주문 ID")
                self.assertEqual(trader.get_submission_status(), {})
                self.assertEqual(trader.balance, 1000)
                self.assertEqual(trader.assets, {})
                self.assert_reached(handle.close())

    def test_new_run_does_not_trigger_old_conditional_or_release_its_asset_reservation(self):
        trader, control, old = self.managed()
        trader.assets["BTC"] = (50, 2)
        results = []
        request = self.request(kind="stop_loss", side="sell")
        request["trigger"] = 40
        old.submit([request], results.append)
        self.assertEqual(trader.get_account_info()["reserved_asset"], {"BTC": 1})
        self.assert_reached(old.close())
        new = control.open_run()
        self.assertTrue(new.update_quote("BTC", 30))
        self.assertEqual([result["state"] for result in results], ["requested"])
        self.assertEqual(trader.get_account_info()["reserved_asset"], {"BTC": 1})
        self.assertEqual(trader.assets["BTC"], (50, 2))
        trader.cancel_request("order")
        self.assertEqual(results[-1]["msg"], "canceled")
        self.assertEqual(trader.get_account_info()["reserved_asset"], {})
        self.assertEqual(trader.assets["BTC"], (50, 2))
        self.assert_reached(new.close())

    def test_submission_status_is_detached_from_live_state(self):
        trader, control, handle = self.managed()
        handle.submit([self.request("pending")], Mock())
        handle.submit([self.request("settled", kind="market")], Mock())
        snapshot = trader.get_submission_status()
        self.assertEqual(snapshot["pending"]["state"], "pending")
        self.assertFalse(snapshot["pending"]["callback_failed"])
        self.assertEqual(snapshot["settled"]["state"], "settled")
        snapshot["pending"]["state"] = "invented"
        snapshot["pending"]["callback_failed"] = True
        snapshot.pop("settled")
        snapshot["extra"] = {}
        fresh = trader.get_submission_status()
        self.assertEqual(set(fresh), {"pending", "settled"})
        self.assertEqual(fresh["pending"]["state"], "pending")
        self.assertFalse(fresh["pending"]["callback_failed"])
        self.assert_reached(handle.close())

    def test_cancellation_after_close_is_synchronous_ordered_and_uses_original_callbacks(self):
        trader, control, handle = self.managed()
        results = []
        handle.submit([self.request("first"), self.request("second")], results.append)
        self.assert_reached(handle.close())
        self.assertIsNone(trader.cancel_all_requests())
        self.assertEqual([(result["request"]["id"], result["msg"]) for result in results], [
            ("first", "success"), ("second", "success"),
            ("first", "canceled"), ("second", "canceled"),
        ])
        trader.cancel_request("first")
        trader.cancel_all_requests()
        self.assertEqual(len(results), 4)
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(len(trader.order_history), 2)

    def test_closed_run_cancellation_callback_blocks_new_run_until_it_returns(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()

        def callback(result):
            if result["msg"] == "canceled":
                entered.set()
                self.wait(release)

        handle.submit([self.request()], callback)
        fence = handle.close()
        self.assert_reached(fence)
        call = self.start(lambda: trader.cancel_request("order"))
        self.wait(entered)
        with self.assertRaises(RuntimeError):
            control.open_run()
        self.assert_reached(fence)
        release.set()
        self.join(call)
        self.assert_reached(control.open_run().close())

    def test_cancel_claim_wins_before_quote_reaches_next_entry(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "done" and result["request"]["id"] == "first":
                entered.set()
                self.wait(release)

        handle.submit([self.request("first"), self.request("second")], callback)
        quote = self.start(lambda: handle.update_quote("BTC", 39))
        self.wait(entered)
        trader.cancel_request("second")
        release.set()
        self.assertEqual(self.join(quote), [True])
        terminal = [result for result in results if result["state"] == "done"]
        self.assertEqual([(result["request"]["id"], result["msg"]) for result in terminal], [
            ("first", "success"), ("second", "canceled"),
        ])
        self.assertEqual(trader.balance, 961)
        self.assertEqual(trader.assets["BTC"], (39, 1))
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        self.assert_reached(handle.close())

    def test_quote_claim_wins_before_cancel_and_callback_is_delivered_once(self):
        trader, control, handle = self.managed()
        entered, release = threading.Event(), self.release_event()
        results = []

        def callback(result):
            results.append(result)
            if result["state"] == "done":
                entered.set()
                self.wait(release)

        handle.submit([self.request()], callback)
        quote = self.start(lambda: handle.update_quote("BTC", 39))
        self.wait(entered)
        trader.cancel_request("order")
        trader.cancel_all_requests()
        self.assertEqual(len(results), 2)
        release.set()
        self.join(quote)
        self.assertEqual([result["msg"] for result in results], ["success", "success"])
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.balance, 961)
        self.assert_reached(handle.close())

    def test_simultaneous_cancel_and_fill_claim_exactly_one_terminal_result(self):
        trader, control, handle = self.managed()
        results = []
        handle.submit([self.request()], results.append)
        barrier = threading.Barrier(3)

        def quote():
            barrier.wait(3)
            return handle.update_quote("BTC", 39)

        def cancel():
            barrier.wait(3)
            trader.cancel_request("order")

        quote_call, cancel_call = self.start(quote), self.start(cancel)
        barrier.wait(3)
        self.assertEqual(self.join(quote_call), [True])
        self.join(cancel_call)
        self.assertEqual(len(results), 2)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.pending_orders, {})
        self.assertEqual(trader.get_account_info()["reserved_balance"], 0)
        if results[-1]["msg"] == "canceled":
            self.assertEqual(trader.balance, 1000)
            self.assertEqual(trader.assets, {})
        else:
            self.assertEqual(results[-1]["msg"], "success")
            self.assertEqual(trader.balance, 961)
            self.assertEqual(trader.assets["BTC"], (39, 1))
        self.assert_reached(handle.close())

    def test_stale_queued_producer_handles_stay_rejected_across_worker_restart(self):
        trader, control, old = self.managed()
        worker = Worker("simulation-admission-producer")
        worker.logger = Mock()
        self.workers.append(worker)
        entered, release = threading.Event(), self.release_event()
        worker.post_task({"runnable": lambda task: (entered.set(), self.wait(release))})
        worker.start()
        self.wait(entered)
        worker.post_task(None)
        attempted, decisions, callback = threading.Event(), [], Mock()

        def stale_producer(task):
            decisions.append(old.submit([self.request("stale", kind="market")], callback))
            decisions.append(old.update_quote("BTC", 1))
            attempted.set()

        worker.post_task({"runnable": stale_producer})
        self.assert_reached(old.close())
        release.set()
        worker.thread.join(3)
        self.assertFalse(worker.thread.is_alive())
        self.assertFalse(attempted.is_set())
        self.assertTrue(worker.stop())
        new = control.open_run()
        worker.start()
        self.wait(attempted)
        self.assertEqual(decisions, [False, False])
        self.assertIsNone(worker.failure)
        callback.assert_not_called()
        self.assertEqual(trader.balance, 1000)
        self.assertEqual(trader.quotes["BTC"], 50)
        self.assertEqual(trader.get_submission_status(), {})
        self.assertTrue(new.submit([self.request("fresh", kind="market")], callback))
        self.assertEqual(callback.call_count, 1)
        self.assert_reached(new.close())


if __name__ == "__main__":
    unittest.main()
