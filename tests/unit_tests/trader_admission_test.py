"""Inactive admission contract; deterministic synchronization, fake transport."""
from dataclasses import FrozenInstanceError
import threading
import unittest
from unittest.mock import Mock, patch

import requests
from smtm.trader.admission import AdmissionOutcome, _AdmissionClosed
from smtm.trader.binance_trader import BinanceTrader
from smtm.trader.bithumb_trader import BithumbTrader
from smtm.trader.okx_trader import OkxTrader
from smtm.trader.upbit_trader import UpbitTrader
from smtm.trader.simulation_trader import SimulationTrader
from smtm.trader.trader import Trader


class TraderAdmissionTest(unittest.TestCase):
    ADAPTERS = (UpbitTrader, BinanceTrader, OkxTrader, BithumbTrader)

    def setUp(self):
        self.workers, self.releases, self.threads, self.errors = [], [], [], []
        for patcher in (patch.dict('os.environ', {}, clear=True),
                        patch('requests.sessions.Session.request',
                              side_effect=AssertionError('Network forbidden')),
                        patch('threading.excepthook', side_effect=self.errors.append)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        for release in self.releases:
            release.set()
        for worker in self.workers:
            worker.stop()
        for thread in self.threads:
            thread.join(3)
            self.assertFalse(thread.is_alive())

    def trader(self, cls=BinanceTrader):
        trader = cls(budget=100000, opt_mode=False)
        self.workers.append(trader.worker)
        trader.ACCESS_KEY, trader.SECRET_KEY = 'synthetic-access', 'synthetic-secret'
        trader.SERVER_URL = 'https://exchange.invalid'
        if cls is OkxTrader:
            trader.PASSPHRASE = 'synthetic-passphrase'
        trader.asset = (100, 10)
        trader.logger = trader.worker.logger = Mock()
        trader._start_timer = Mock()
        return trader

    @staticmethod
    def request(identifier='test-id'):
        return {'id': identifier, 'type': 'buy', 'price': 100, 'amount': 1}

    @staticmethod
    def response(cls):
        payload = {UpbitTrader: {'uuid': 'exchange-id'},
                   BinanceTrader: {'orderId': 123},
                   OkxTrader: {'code': '0', 'data': [{'ordId': 'exchange-id', 'sCode': '0'}]},
                   BithumbTrader: {'status': '0000', 'order_id': 'exchange-id'}}[cls]
        response = Mock(status_code=200)
        response.json.return_value = payload
        return response

    def wait(self, event):
        self.assertTrue(event.wait(3), 'Expected event was not signaled')

    def thread(self, action):
        thread = threading.Thread(target=action, daemon=True)
        self.threads.append(thread)
        thread.start()
        return thread

    def blocker(self, worker, failure=None):
        entered, release = threading.Event(), threading.Event()
        self.releases.append(release)
        def run(task):
            entered.set()
            self.wait(release)
            if failure is not None:
                raise failure
        worker.post_task({'runnable': run})
        self.wait(entered)
        return release

    def complete(self, fence):
        self.wait(fence._run.completed)
        return fence.wait()

    def test_optional_capability_is_nonabstract_and_simulation_unsupported(self):
        self.assertNotIn('get_admission_control', Trader.__abstractmethods__)
        self.assertIsNone(SimulationTrader().get_admission_control())

    def test_accessor_alone_does_not_activate_or_change_legacy_calls(self):
        trader = self.trader()
        control = trader.get_admission_control()
        self.assertIs(control, trader.get_admission_control())
        request, callback = self.request(), Mock()
        with patch.object(trader.worker, 'post_task') as post:
            self.assertIsNone(trader.send_request([request], callback))
        self.assertIs(post.call_args.args[0]['request'], request)
        self.assertNotIn('_admission_run', post.call_args.args[0])

    def test_handle_is_immutable_and_legacy_entry_cannot_bypass_managed_gate(self):
        trader = self.trader()
        handle = trader.get_admission_control().open_run()
        with self.assertRaises(FrozenInstanceError):
            handle._run = object()
        with self.assertRaisesRegex(RuntimeError, 'admission handle'):
            trader.send_request([self.request()], Mock())
        with patch('requests.post') as post:
            trader._execute_order({'request': self.request(), 'callback': Mock()})
            with self.assertRaises(_AdmissionClosed):
                trader._request_post('https://exchange.invalid/create', creation=True)
        post.assert_not_called()
        self.assertEqual(trader.get_submission_status(), {})
        self.assertEqual(self.complete(handle.close()), AdmissionOutcome.SUBMISSION_FENCE_REACHED)

    def test_close_is_idempotent_and_rejects_future_submissions(self):
        trader = self.trader()
        handle = trader.get_admission_control().open_run()
        release = self.blocker(trader.worker)
        fence = handle.close()
        self.assertEqual(fence.outcome, AdmissionOutcome.ADMISSION_CLOSED)
        self.assertFalse(fence.done)
        self.assertFalse(handle.submit([self.request()], Mock()))
        self.assertIs(handle.close()._run, fence._run)
        release.set()
        self.assertEqual(self.complete(fence), AdmissionOutcome.SUBMISSION_FENCE_REACHED)

    def test_batch_enqueue_and_close_have_one_fifo_order(self):
        trader = self.trader()
        handle = trader.get_admission_control().open_run()
        entered, release, closing = threading.Event(), threading.Event(), threading.Event()
        self.releases.append(release)
        queued, accepted, fences = [], [], []
        def post(task):
            queued.append(task)
            if len(queued) == 1:
                entered.set()
                self.wait(release)
        with patch.object(trader.worker, 'post_task', side_effect=post):
            submitter = self.thread(lambda: accepted.append(handle.submit(
                [self.request('first'), self.request('second')], Mock())))
            self.wait(entered)
            def close():
                closing.set()
                fences.append(handle.close())
            closer = self.thread(close)
            self.wait(closing)
            release.set()
            submitter.join(3)
            closer.join(3)
        self.assertEqual(accepted, [True])
        self.assertEqual([task['request']['id'] for task in queued[:2]], ['first', 'second'])
        self.assertNotIn('request', queued[2])
        self.assertFalse(handle.submit([self.request('late')], Mock()))
        for task in queued:
            task['runnable'](task)
        self.assertEqual(fences[0].outcome, AdmissionOutcome.SUBMISSION_FENCE_REACHED)
        self.assertEqual(trader.get_submission_status(), {})

    def test_queued_admitted_and_preexisting_legacy_work_are_rejected_on_close(self):
        trader = self.trader()
        release = self.blocker(trader.worker)
        callback = Mock()
        trader.send_request([self.request('legacy')], callback)
        handle = trader.get_admission_control().open_run()
        self.assertTrue(handle.submit([self.request('admitted')], callback))
        fence = handle.close()
        with patch('requests.post') as post:
            release.set()
            self.complete(fence)
        post.assert_not_called()
        callback.assert_not_called()
        self.assertEqual(trader.get_submission_status(), {})

    def test_close_during_price_preparation_prevents_creation(self):
        for cls in (UpbitTrader, BithumbTrader):
            with self.subTest(adapter=cls.__name__):
                trader = self.trader(cls)
                trader.is_opt_mode = True
                handle = trader.get_admission_control().open_run()
                entered, release = threading.Event(), threading.Event()
                self.releases.append(release)
                callback = Mock()
                def price(*args):
                    entered.set()
                    self.wait(release)
                    return 100
                with patch.object(trader, '_optimize_price', side_effect=price), \
                     patch('requests.post') as post:
                    handle.submit([self.request()], callback)
                    self.wait(entered)
                    fence = handle.close()
                    self.assertFalse(fence.done)
                    release.set()
                    self.complete(fence)
                post.assert_not_called()
                callback.assert_not_called()
                self.assertEqual(trader.get_submission_status()['test-id']['state'], 'not_dispatched')

    def test_close_after_possible_dispatch_retains_known_or_unknown_owner(self):
        for cls in self.ADAPTERS:
            for known in (True, False):
                with self.subTest(adapter=cls.__name__, known=known):
                    trader = self.trader(cls)
                    handle = trader.get_admission_control().open_run()
                    entered, release = threading.Event(), threading.Event()
                    self.releases.append(release)
                    request, callback = self.request(), Mock()
                    def transport(*args, **kwargs):
                        entered.set()
                        self.wait(release)
                        if known:
                            return self.response(cls)
                        raise requests.ConnectionError('synthetic lost ACK')
                    with patch('requests.post', side_effect=transport) as post:
                        handle.submit([request], callback)
                        self.wait(entered)
                        self.assertTrue(trader.get_submission_status()['test-id']['dispatched'])
                        fence = handle.close()
                        release.set()
                        self.assertEqual(self.complete(fence), AdmissionOutcome.SUBMISSION_FENCE_REACHED)
                    self.assertEqual(post.call_count, 1)
                    self.assertEqual(trader.get_submission_status()['test-id']['state'],
                                     'known' if known else 'unknown')
                    self.assertIs(trader._submissions['test-id']['callback'], callback)
                    self.assertIs(trader._submissions['test-id']['request'], request)
                    self.assertEqual(callback.call_count, 1 if known else 0)

    def test_task_failure_completes_fence_before_public_callback_unblocks(self):
        trader = self.trader()
        failure = RuntimeError('task failure')
        release = self.blocker(trader.worker, failure)
        handle = trader.get_admission_control().open_run()
        callback_entered, callback_release = threading.Event(), threading.Event()
        self.releases.append(callback_release)
        def terminated():
            callback_entered.set()
            self.wait(callback_release)
        trader.worker.register_on_terminated(terminated)
        handle.submit([self.request()], Mock())
        fence = handle.close()
        release.set()
        self.wait(callback_entered)
        self.assertEqual(self.complete(fence), AdmissionOutcome.EXECUTION_FAILURE)
        self.assertIs(fence.failure, failure)
        self.assertTrue(trader.worker.thread.is_alive())
        callback_release.set()

    def test_clean_early_stop_and_callback_failure_complete_pending_fence(self):
        for fail_callback in (False, True):
            with self.subTest(fail_callback=fail_callback):
                trader = self.trader()
                release = self.blocker(trader.worker)
                handle = trader.get_admission_control().open_run()
                callback_entered, callback_release = threading.Event(), threading.Event()
                self.releases.append(callback_release)
                def terminated():
                    callback_entered.set()
                    self.wait(callback_release)
                    if fail_callback:
                        raise RuntimeError('termination callback')
                trader.worker.register_on_terminated(terminated)
                trader.worker.post_task(None)
                fence = handle.close()
                release.set()
                self.wait(callback_entered)
                self.assertEqual(self.complete(fence), AdmissionOutcome.EXECUTION_FAILURE)
                self.assertTrue(trader.worker.thread.is_alive())
                callback_release.set()

    def test_registration_after_generation_failure_cannot_miss_fence_failure(self):
        trader = self.trader()
        failure = RuntimeError('before observer')
        release = self.blocker(trader.worker, failure)
        observed = trader.worker._observe_run
        def observe(run, callback):
            release.set()
            run.thread.join(3)
            self.assertFalse(run.thread.is_alive())
            observed(run, callback)
        with patch.object(trader.worker, '_observe_run', side_effect=observe):
            handle = trader.get_admission_control().open_run()
        fence = handle.close()
        self.assertEqual(fence.outcome, AdmissionOutcome.EXECUTION_FAILURE)
        self.assertIs(fence.failure, failure)
        self.assertFalse(handle.submit([self.request()], Mock()))

    def test_stale_queued_handle_and_fence_never_reactivate_after_restart(self):
        trader = self.trader()
        release = self.blocker(trader.worker, RuntimeError('first generation'))
        control = trader.get_admission_control()
        old = control.open_run()
        old.submit([self.request('old')], Mock())
        old_fence = old.close()
        release.set()
        self.assertEqual(self.complete(old_fence), AdmissionOutcome.EXECUTION_FAILURE)
        trader.worker.thread.join(3)
        trader.worker.start()
        new = control.open_run()
        self.assertFalse(old.submit([self.request('stale')], Mock()))
        old.close()
        new_fence = new.close()
        self.assertEqual(self.complete(new_fence), AdmissionOutcome.SUBMISSION_FENCE_REACHED)
        self.assertEqual(old_fence.outcome, AdmissionOutcome.EXECUTION_FAILURE)
        self.assertEqual(trader.get_submission_status(), {})

    def test_reentrant_close_and_wait_on_worker_never_self_wait(self):
        trader = self.trader()
        handle = trader.get_admission_control().open_run()
        closed, results, fences = threading.Event(), [], []
        def callback(result):
            fence = handle.close()
            fences.append(fence)
            results.append(fence.wait())
            closed.set()
        with patch('requests.post', return_value=self.response(BinanceTrader)):
            handle.submit([self.request()], callback)
            self.wait(closed)
            self.assertEqual(self.complete(fences[0]), AdmissionOutcome.SUBMISSION_FENCE_REACHED)
        self.assertEqual(results, [AdmissionOutcome.ADMISSION_CLOSED])
        self.assertEqual(trader.get_submission_status()['test-id']['state'], 'known')

    def test_reached_fence_stays_reached_when_later_generation_task_fails(self):
        trader = self.trader()
        control = trader.get_admission_control()
        old = control.open_run()
        fence = old.close()
        self.complete(fence)
        new = control.open_run()
        release = self.blocker(trader.worker, RuntimeError('later failure'))
        new_fence = new.close()
        release.set()
        self.assertEqual(self.complete(new_fence), AdmissionOutcome.EXECUTION_FAILURE)
        self.assertEqual(fence.outcome, AdmissionOutcome.SUBMISSION_FENCE_REACHED)

    def test_open_never_restarts_stopped_worker_or_overlaps_pending_fence(self):
        trader = self.trader()
        control = trader.get_admission_control()
        handle = control.open_run()
        with self.assertRaisesRegex(RuntimeError, 'Previous admission'):
            control.open_run()
        release = self.blocker(trader.worker)
        fence = handle.close()
        with self.assertRaisesRegex(RuntimeError, 'Previous admission'):
            control.open_run()
        release.set()
        self.complete(fence)
        trader.worker.stop()
        with self.assertRaisesRegex(RuntimeError, 'running Worker'):
            control.open_run()

    def test_close_during_binance_okx_signing(self):
        for cls, method in [(BinanceTrader, '_signed_query'), (OkxTrader, '_create_signature')]:
            trader = self.trader(cls)
            handle = trader.get_admission_control().open_run()
            entered, release = threading.Event(), threading.Event()
            self.releases.append(release)
            original = getattr(trader, method)
            def signing(*args, **kwargs):
                entered.set()
                self.wait(release)
                return original(*args, **kwargs)
            callback = Mock()
            with patch.object(trader, method, side_effect=signing), patch('requests.post') as post:
                self.assertTrue(handle.submit([self.request()], callback))
                self.wait(entered)
                fence = handle.close()
                release.set()
                self.assertEqual(self.complete(fence), AdmissionOutcome.SUBMISSION_FENCE_REACHED)
            post.assert_not_called()
            callback.assert_not_called()
            self.assertEqual(trader.get_submission_status()['test-id']['state'], 'not_dispatched')

    def test_observer_registration_after_clean_end_blocked_callback(self):
        trader = self.trader()
        callback_entered, callback_release = threading.Event(), threading.Event()
        self.releases.append(callback_release)
        def terminated():
            callback_entered.set()
            self.wait(callback_release)
        trader.worker.register_on_terminated(terminated)
        original = trader.worker._observe_run
        def observe(run, callback):
            trader.worker.post_task(None)
            self.wait(callback_entered)
            original(run, callback)
        with patch.object(trader.worker, '_observe_run', side_effect=observe):
            handle = trader.get_admission_control().open_run()
        fence = handle.close()
        self.assertEqual(fence.wait(), AdmissionOutcome.EXECUTION_FAILURE)
        self.assertTrue(trader.worker.thread.is_alive())
        self.assertFalse(handle.submit([self.request()], Mock()))

    def test_iterator_can_close_own_run(self):
        trader = self.trader()
        handle = trader.get_admission_control().open_run()
        fences = []
        def requests():
            fences.append(handle.close())
            yield self.request()
        self.assertFalse(handle.submit(requests(), Mock()))
        self.assertEqual(self.complete(fences[0]), AdmissionOutcome.SUBMISSION_FENCE_REACHED)
        self.assertEqual(trader.get_submission_status(), {})

    def test_requested_callback_failure_fails_fence_and_keeps_known_owner(self):
        trader = self.trader()
        handle = trader.get_admission_control().open_run()
        entered, release = threading.Event(), threading.Event()
        self.releases.append(release)
        failure = RuntimeError('requested callback')
        def callback(result):
            entered.set()
            self.wait(release)
            raise failure
        with patch('requests.post', return_value=self.response(BinanceTrader)):
            handle.submit([self.request()], callback)
            self.wait(entered)
            fence = handle.close()
            release.set()
            self.assertEqual(self.complete(fence), AdmissionOutcome.EXECUTION_FAILURE)
        self.assertIs(fence.failure, failure)
        self.assertEqual(trader.get_submission_status()['test-id']['state'], 'known')
        self.assertIs(trader._submissions['test-id']['callback'], callback)

    def test_reached_fence_does_not_wait_for_external_terminal_callback(self):
        trader = self.trader()
        handle = trader.get_admission_control().open_run()
        requested, entered, release = threading.Event(), threading.Event(), threading.Event()
        self.releases.append(release)
        def callback(result):
            if result['state'] == 'requested':
                requested.set()
            else:
                entered.set()
                self.wait(release)
        with patch('requests.post', return_value=self.response(BinanceTrader)):
            handle.submit([self.request()], callback)
            self.wait(requested)
            fence = handle.close()
            self.complete(fence)
        order = trader.order_map['test-id']
        terminal = {'orderId': 123, 'symbol': 'BTCUSDT', 'status': 'FILLED',
                    'price': '100', 'executedQty': '1'}
        self.thread(lambda: trader._complete_order('test-id', order, terminal))
        self.wait(entered)
        self.assertEqual(trader.order_map, {})
        self.assertEqual(trader.get_submission_status()['test-id']['state'], 'settling')
        self.assertEqual(fence.outcome, AdmissionOutcome.SUBMISSION_FENCE_REACHED)
        self.assertIs(trader._submissions['test-id']['callback'], callback)
        release.set()
