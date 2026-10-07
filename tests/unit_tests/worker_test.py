import threading
import unittest
from unittest.mock import ANY, Mock, patch

from smtm import Worker


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.workers = []
        self.releases = []
        self.threads = []
        self.thread_errors = []
        self.error_hook = patch("threading.excepthook", side_effect=self.thread_errors.append)
        self.error_hook.start()
        self.addCleanup(self.error_hook.stop)

    def tearDown(self):
        for release in self.releases:
            release.set()
        for worker in self.workers:
            worker.stop()
        for thread in self.threads:
            thread.join(3)
            self.assertFalse(thread.is_alive(), "helper thread did not exit")

    def worker(self):
        worker = Worker("Worker-lifecycle-test")
        worker.logger = Mock()
        self.workers.append(worker)
        return worker

    def event(self):
        event = threading.Event()
        self.releases.append(event)
        return event

    def wait(self, event):
        self.assertTrue(event.wait(3), "event was not signaled")

    def thread(self, action):
        thread = threading.Thread(target=action, daemon=True)
        self.threads.append(thread)
        thread.start()
        return thread

    def blocking_task(self):
        entered, release = threading.Event(), self.event()

        def run(task):
            entered.set()
            self.wait(release)

        return {"runnable": run}, entered, release

    def begin_stop(self, worker):
        """Observe the stop caller reaching join, not a guessed scheduling delay."""
        joining = threading.Event()
        finished = threading.Event()
        results = []
        real_join = worker.thread.join

        def join(*args, **kwargs):
            joining.set()
            return real_join(*args, **kwargs)

        worker.thread.join = join

        def stop():
            results.append(worker.stop())
            finished.set()

        thread = self.thread(stop)
        self.wait(joining)
        return thread, finished, results

    def test_post_task_put_task_correctly(self):
        worker = Worker("robot")
        worker.task_queue = Mock()
        worker.post_task("mango")
        worker.task_queue.put.assert_called_once_with("mango")

    @patch("threading.Thread")
    def test_start_constructs_and_starts_only_one_live_thread(self, thread_class):
        worker = Worker("robot")
        worker.start()
        worker.start()
        thread_class.assert_called_once_with(target=ANY, name="robot", daemon=True)
        thread_class.return_value.start.assert_called_once()

    def test_register_on_terminated_keeps_callback(self):
        worker = self.worker()
        callback = Mock()
        worker.register_on_terminated(callback)
        self.assertIs(worker.on_terminated, callback)

    def test_failed_thread_start_preserves_queued_work_for_explicit_retry(self):
        worker = self.worker()
        runnable = Mock()
        worker.post_task({"runnable": runnable})
        with patch("threading.Thread") as thread_class:
            thread_class.return_value.start.side_effect = RuntimeError("cannot start")
            with self.assertRaisesRegex(RuntimeError, "cannot start"):
                worker.start()
            self.assertIsNone(worker.thread)
            self.assertTrue(worker.stop())
            thread_class.return_value.join.assert_not_called()
        worker.start()
        self.assertTrue(worker.stop())
        runnable.assert_called_once()

    def test_pre_start_tasks_and_legacy_none_run_fifo(self):
        worker = self.worker()
        calls = []
        for number in range(3):
            worker.post_task({"runnable": lambda task: calls.append(task["number"]),
                              "number": number})
        worker.post_task(None)
        worker.start()
        thread = worker.thread
        thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(calls, [0, 1, 2])
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)
        self.assertTrue(worker.stop())

    def test_queue_completion_waits_until_runnable_exits(self):
        worker = self.worker()
        task, entered, release = self.blocking_task()
        worker.post_task(task)
        worker.start()
        self.wait(entered)
        with worker.task_queue.mutex:
            self.assertEqual(worker.task_queue.unfinished_tasks, 1)
        joined = threading.Event()
        self.thread(lambda: (worker.task_queue.join(), joined.set()))
        self.assertFalse(joined.is_set())
        release.set()
        self.wait(joined)
        self.assertTrue(worker.stop())

    def test_stop_waits_for_blocked_runnable_and_keeps_thread_identity(self):
        worker = self.worker()
        task, entered, release = self.blocking_task()
        worker.post_task(task)
        worker.start()
        original = worker.thread
        self.wait(entered)
        _, finished, results = self.begin_stop(worker)
        self.assertFalse(finished.is_set())
        self.assertIs(worker.thread, original)
        worker.start()
        self.assertIs(worker.thread, original)
        release.set()
        self.wait(finished)
        self.assertEqual(results, [True])
        self.assertFalse(original.is_alive())
        self.assertIsNone(worker.thread)

    def test_stop_waits_for_termination_callback(self):
        worker = self.worker()
        entered, release = threading.Event(), self.event()
        callback_threads = []

        def callback():
            callback_threads.append(threading.current_thread())
            entered.set()
            self.wait(release)

        worker.register_on_terminated(callback)
        worker.start()
        original = worker.thread
        _, finished, results = self.begin_stop(worker)
        self.wait(entered)
        self.assertFalse(finished.is_set())
        worker.start()
        self.assertIs(worker.thread, original)
        release.set()
        self.wait(finished)
        self.assertEqual(results, [True])
        self.assertEqual(callback_threads, [original])

    def test_posts_during_and_after_stop_wait_for_explicit_restart(self):
        worker = self.worker()
        task, entered, release = self.blocking_task()
        calls = []
        worker.post_task(task)
        worker.post_task({"runnable": lambda _: calls.append("before")})
        worker.start()
        self.wait(entered)
        _, finished, results = self.begin_stop(worker)
        worker.post_task({"runnable": lambda _: calls.append("during")})
        release.set()
        self.wait(finished)
        self.assertEqual(results, [True])
        self.assertEqual(calls, ["before"])
        worker.post_task({"runnable": lambda _: calls.append("after")})
        self.assertEqual(worker.task_queue.unfinished_tasks, 2)
        self.assertTrue(worker.stop())
        worker.start()
        self.assertTrue(worker.stop())
        self.assertEqual(calls, ["before", "during", "after"])
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)

    def test_concurrent_repeated_stop_leaves_no_effective_marker(self):
        worker = self.worker()
        task, entered, release = self.blocking_task()
        worker.post_task(task)
        worker.start()
        self.wait(entered)
        # Both stop callers must reach the join of the same still-blocked thread.
        joined = threading.Barrier(3, timeout=3)
        real_join = worker.thread.join

        def join(*args, **kwargs):
            joined.wait()
            return real_join(*args, **kwargs)

        worker.thread.join = join
        results = []
        stoppers = [self.thread(lambda: results.append(worker.stop())) for _ in range(2)]
        joined.wait()
        worker.thread.join = real_join
        release.set()
        for thread in stoppers:
            thread.join(3)
            self.assertFalse(thread.is_alive())
        self.assertEqual(results, [True, True])
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)
        ran = threading.Event()
        worker.start()
        worker.post_task({"runnable": lambda _: ran.set()})
        self.wait(ran)
        self.assertTrue(worker.stop())

    def test_self_stop_requests_shutdown_without_claiming_completion(self):
        worker = self.worker()
        returned = threading.Event()
        results = []

        def run(task):
            results.append(worker.stop())
            returned.set()

        worker.post_task({"runnable": run})
        worker.start()
        self.wait(returned)
        self.assertEqual(results, [False])
        self.assertTrue(worker.stop())
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)

    def test_callback_can_self_stop_and_reenter_without_lifecycle_lock(self):
        worker = self.worker()
        results = []
        callbacks = []

        def callback():
            callbacks.append(threading.current_thread())
            self.assertTrue(worker._lifecycle_lock.acquire(blocking=False))
            worker._lifecycle_lock.release()
            results.append(worker.stop())
            worker.start()  # No overlapping generation while callback is alive.
            worker.register_on_terminated(None)
            worker.post_task({"runnable": lambda _: results.append("next")})

        worker.register_on_terminated(callback)
        worker.start()
        original = worker.thread
        self.assertTrue(worker.stop())
        self.assertEqual(results, [False])
        self.assertEqual(callbacks, [original])
        worker.start()
        self.assertTrue(worker.stop())
        self.assertEqual(results, [False, "next"])

    def test_runnable_can_reenter_worker_without_lifecycle_lock(self):
        worker = self.worker()
        result = threading.Event()

        def run(task):
            self.assertTrue(worker._lifecycle_lock.acquire(blocking=False))
            worker._lifecycle_lock.release()
            worker.start()
            worker.post_task({"runnable": lambda _: result.set()})

        worker.post_task({"runnable": run})
        worker.start()
        self.wait(result)
        self.assertTrue(worker.stop())

    def test_task_failure_is_fail_stop_observable_and_not_retried(self):
        worker = self.worker()
        error = ValueError("synthetic task failure")
        callback = Mock()
        worker.register_on_terminated(callback)
        later = Mock()
        failed_task = Mock(side_effect=error)
        worker.post_task({"runnable": failed_task})
        worker.post_task({"runnable": later})
        worker.start()
        original = worker.thread
        original.join(3)
        self.assertFalse(original.is_alive())
        self.assertFalse(worker.stop())
        self.assertIs(worker.failure, error)
        failed_task.assert_called_once()
        later.assert_not_called()
        callback.assert_called_once()
        self.assertEqual(worker.task_queue.unfinished_tasks, 1)
        self.assertEqual(len(self.thread_errors), 1)
        self.assertIs(self.thread_errors[0].exc_value.__cause__, error)
        worker.start()  # Existing explicit restart policy, not automatic recovery.
        self.assertTrue(worker.stop())
        self.assertIsNone(worker.failure)
        later.assert_called_once()
        failed_task.assert_called_once()
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)

    def test_malformed_task_failure_is_accounted_and_notified(self):
        worker = self.worker()
        callback = Mock()
        worker.register_on_terminated(callback)
        worker.post_task({})
        worker.start()
        worker.thread.join(3)
        self.assertFalse(worker.stop())
        self.assertIsInstance(worker.failure, KeyError)
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)
        callback.assert_called_once()

    def test_callback_failure_prevents_clean_stop_and_does_not_deadlock(self):
        worker = self.worker()
        error = RuntimeError("synthetic callback failure")
        callback = Mock(side_effect=error)
        worker.register_on_terminated(callback)
        worker.start()
        original = worker.thread
        self.assertFalse(worker.stop())
        self.assertFalse(original.is_alive())
        self.assertIs(worker.failure, error)
        self.assertFalse(worker.stop())
        callback.assert_called_once()
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)

    def test_task_failure_remains_primary_when_callback_also_fails(self):
        worker = self.worker()
        primary = ValueError("task failed")
        secondary = RuntimeError("callback failed")
        worker.post_task({"runnable": Mock(side_effect=primary)})
        worker.register_on_terminated(Mock(side_effect=secondary))
        worker.start()
        worker.thread.join(3)
        self.assertFalse(worker.stop())
        self.assertIs(worker.failure, primary)
        self.assertEqual(len(self.thread_errors), 1)
        self.assertIs(self.thread_errors[0].exc_value.__cause__, primary)

    def test_stop_marker_left_by_failure_cannot_stop_restarted_generation(self):
        worker = self.worker()
        entered, release = threading.Event(), self.event()
        error = ValueError("blocked task failed")
        calls = []

        def run(task):
            entered.set()
            self.wait(release)
            raise error

        worker.post_task({"runnable": run})
        worker.post_task({"runnable": lambda _: calls.append("before-marker")})
        worker.start()
        self.wait(entered)
        _, finished, results = self.begin_stop(worker)
        worker.post_task({"runnable": lambda _: calls.append("after-marker")})
        release.set()
        self.wait(finished)
        self.assertEqual(results, [False])
        self.assertEqual(calls, [])
        self.assertIs(worker.failure, error)
        worker.start()
        self.assertTrue(worker.stop())
        self.assertEqual(calls, ["before-marker", "after-marker"])
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)

    def test_old_stop_waiter_does_not_clear_or_use_new_generation(self):
        worker = self.worker()
        worker.start()
        original = worker.thread
        exited, release_stop = threading.Event(), self.event()
        real_join = original.join

        def delayed_join(*args, **kwargs):
            real_join(*args, **kwargs)
            exited.set()
            self.wait(release_stop)

        original.join = delayed_join
        results = []
        stop_done = threading.Event()
        self.thread(lambda: (results.append(worker.stop()), stop_done.set()))
        self.wait(exited)
        self.assertFalse(original.is_alive())
        new_error = ValueError("new generation failure")
        worker.post_task({"runnable": Mock(side_effect=new_error)})
        worker.start()
        newer = worker.thread
        self.assertIsNot(newer, original)
        newer.join(3)
        self.assertFalse(newer.is_alive())
        release_stop.set()
        self.wait(stop_done)
        self.assertEqual(results, [True])
        self.assertIs(worker.thread, newer)
        self.assertIs(worker.failure, new_error)
        self.assertFalse(worker.stop())

    def test_legacy_none_with_stop_leaves_no_effective_marker_on_restart(self):
        worker = self.worker()
        task, entered, release = self.blocking_task()
        worker.post_task(task)
        worker.post_task(None)
        worker.start()
        self.wait(entered)
        _, finished, results = self.begin_stop(worker)
        release.set()
        self.wait(finished)
        self.assertEqual(results, [True])
        ran = threading.Event()
        worker.post_task({"runnable": lambda _: ran.set()})
        worker.start()
        self.wait(ran)
        self.assertTrue(worker.stop())
        self.assertEqual(worker.task_queue.unfinished_tasks, 0)

    def test_queue_join_after_failure_is_not_proof_of_successful_fence(self):
        worker = self.worker()
        error = ValueError("work failed")
        fence = Mock()
        worker.post_task({"runnable": Mock(side_effect=error)})
        worker.post_task({"runnable": fence})
        worker.start()
        worker.thread.join(3)
        self.assertFalse(worker.stop())
        self.assertIs(worker.failure, error)
        self.assertEqual(worker.task_queue.unfinished_tasks, 1)
        fence.assert_not_called()

    def test_stop_before_first_start_does_not_discard_queued_work(self):
        worker = self.worker()
        runnable = Mock()
        worker.post_task({"runnable": runnable})
        self.assertTrue(worker.stop())
        self.assertIsNone(worker.thread)
        self.assertEqual(worker.task_queue.unfinished_tasks, 1)
        worker.start()
        self.assertTrue(worker.stop())
        runnable.assert_called_once()

    def test_capture_run_returns_only_active_generation(self):
        worker = self.worker()
        self.assertIsNone(worker._capture_run())
        task, entered, release = self.blocking_task()
        worker.post_task(task)
        worker.start()
        self.wait(entered)
        run = worker._capture_run()
        self.assertIsNotNone(run)
        self.assertIs(worker._capture_run(), run)
        _, finished, results = self.begin_stop(worker)
        self.assertIsNone(worker._capture_run())
        release.set()
        self.wait(finished)
        self.assertEqual(results, [True])
        self.assertIsNone(worker._capture_run())
        worker.start()
        self.assertIsNot(worker._capture_run(), run)
        self.assertIsNotNone(worker._capture_run())
        self.assertTrue(worker.stop())

    def test_observe_missing_generation_notifies_synchronously_without_lock(self):
        worker = self.worker()
        calls = []
        caller = threading.current_thread()

        def observer(run, error):
            self.assertTrue(worker._lifecycle_lock.acquire(blocking=False))
            worker._lifecycle_lock.release()
            calls.append((run, error, threading.current_thread()))

        worker._observe_run(None, observer)
        self.assertEqual(calls, [(None, None, caller)])

    def test_failed_task_notifies_observer_before_blocking_public_callback(self):
        worker = self.worker()
        task_entered, task_release = threading.Event(), self.event()
        callback_entered, callback_release = threading.Event(), self.event()
        error = ValueError("observed task failure")
        observed = []

        def task(_):
            task_entered.set()
            self.wait(task_release)
            raise error

        def observer(run, failure):
            self.assertTrue(worker._lifecycle_lock.acquire(blocking=False))
            worker._lifecycle_lock.release()
            observed.append((run, failure))

        def callback():
            callback_entered.set()
            self.wait(callback_release)

        public_callback = Mock(side_effect=callback)
        worker.register_on_terminated(public_callback)
        worker.post_task({"runnable": task})
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        worker._observe_run(run, observer)
        task_release.set()
        self.wait(callback_entered)
        self.assertEqual(observed, [(run, error)])
        self.assertIs(worker.failure, error)
        self.assertIsNone(worker._capture_run())
        self.assertTrue(run.thread.is_alive())
        callback_release.set()
        self.assertFalse(worker.stop())
        self.assertEqual(observed, [(run, error)])
        public_callback.assert_called_once_with()

    def test_late_failed_observer_is_synchronous_while_public_callback_blocks(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        callback_entered, callback_release = threading.Event(), self.event()
        error = RuntimeError("cached task failure")
        worker.post_task(task)
        worker.post_task({"runnable": Mock(side_effect=error)})

        def callback():
            callback_entered.set()
            self.wait(callback_release)

        worker.register_on_terminated(callback)
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        task_release.set()
        self.wait(callback_entered)
        calls = []
        caller = threading.current_thread()
        worker._observe_run(run, lambda run, failure: calls.append(
            (run, failure, threading.current_thread())))
        self.assertEqual(calls, [(run, error, caller)])
        self.assertTrue(run.thread.is_alive())
        callback_release.set()
        self.assertFalse(worker.stop())
        self.assertEqual(len(calls), 1)

    def test_clean_early_end_notifies_before_blocking_public_callback(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        callback_entered, callback_release = threading.Event(), self.event()
        fence = Mock()
        observer = Mock()
        worker.post_task(task)
        worker.post_task(None)
        worker.post_task({"runnable": fence})

        def callback():
            callback_entered.set()
            self.wait(callback_release)

        public_callback = Mock(side_effect=callback)
        worker.register_on_terminated(public_callback)
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        worker._observe_run(run, observer)
        task_release.set()
        self.wait(callback_entered)
        observer.assert_called_once_with(run, None)
        fence.assert_not_called()
        self.assertTrue(run.thread.is_alive())
        self.assertIsNone(worker._capture_run())
        self.assertEqual(worker.task_queue.unfinished_tasks, 1)
        callback_release.set()
        self.assertTrue(worker.stop())
        observer.assert_called_once_with(run, None)
        public_callback.assert_called_once_with()

    def test_late_clean_observer_notifies_synchronously_before_callback_exit(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        callback_entered, callback_release = threading.Event(), self.event()
        worker.post_task(task)
        worker.post_task(None)

        def callback():
            callback_entered.set()
            self.wait(callback_release)

        worker.register_on_terminated(callback)
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        task_release.set()
        self.wait(callback_entered)
        caller = threading.current_thread()
        calls = []

        def observer(observed_run, failure):
            self.assertTrue(worker._lifecycle_lock.acquire(blocking=False))
            worker._lifecycle_lock.release()
            calls.append((observed_run, failure, threading.current_thread()))

        worker._observe_run(run, observer)
        self.assertEqual(calls, [(run, None, caller)])
        self.assertTrue(run.thread.is_alive())
        callback_release.set()
        self.assertTrue(worker.stop())
        self.assertEqual(len(calls), 1)

    def test_callback_failure_is_cached_without_renotifying_clean_observer(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        error = RuntimeError("observed callback failure")
        callback = Mock(side_effect=error)
        observer = Mock()
        worker.register_on_terminated(callback)
        worker.post_task(task)
        worker.post_task(None)
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        worker._observe_run(run, observer)
        task_release.set()
        run.thread.join(3)
        self.assertFalse(run.thread.is_alive())
        self.assertFalse(worker.stop())
        observer.assert_called_once_with(run, None)
        callback.assert_called_once_with()
        late_observer = Mock()
        worker._observe_run(run, late_observer)
        late_observer.assert_called_once_with(run, error)

    def test_observers_keep_first_failure_when_public_callback_also_fails(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        primary = ValueError("first observed task error")
        worker.post_task(task)
        worker.post_task({"runnable": Mock(side_effect=primary)})
        callback = Mock(side_effect=RuntimeError("second callback error"))
        worker.register_on_terminated(callback)
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        observer = Mock()
        worker._observe_run(run, observer)
        task_release.set()
        run.thread.join(3)
        self.assertFalse(run.thread.is_alive())
        self.assertFalse(worker.stop())
        observer.assert_called_once_with(run, primary)
        late_observer = Mock()
        worker._observe_run(run, late_observer)
        late_observer.assert_called_once_with(run, primary)
        callback.assert_called_once_with()

    def test_observer_exception_preserves_public_callback_and_other_observers(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        callback = Mock()
        failed_observer = Mock(side_effect=KeyboardInterrupt("observer failed"))
        later_observer = Mock()
        worker.register_on_terminated(callback)
        worker.post_task(task)
        worker.post_task(None)
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        worker._observe_run(run, failed_observer)
        worker._observe_run(run, later_observer)
        task_release.set()
        self.assertTrue(worker.stop())
        failed_observer.assert_called_once_with(run, None)
        later_observer.assert_called_once_with(run, None)
        callback.assert_called_once_with()
        self.assertIsNone(worker.failure)
        worker.logger.error.assert_called_once()
        self.assertEqual(self.thread_errors, [])
        late_failed_observer = Mock(side_effect=RuntimeError("late observer failed"))
        worker._observe_run(run, late_failed_observer)
        late_failed_observer.assert_called_once_with(run, None)
        self.assertTrue(worker.stop())
        callback.assert_called_once_with()

    def test_observer_failure_does_not_replace_task_failure(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        error = ValueError("primary task failure")
        callback = Mock()
        worker.register_on_terminated(callback)
        worker.post_task(task)
        worker.post_task({"runnable": Mock(side_effect=error)})
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        failed_observer = Mock(side_effect=RuntimeError("observer failed"))
        later_observer = Mock()
        worker._observe_run(run, failed_observer)
        worker._observe_run(run, later_observer)
        task_release.set()
        self.assertFalse(worker.stop())
        failed_observer.assert_called_once_with(run, error)
        later_observer.assert_called_once_with(run, error)
        callback.assert_called_once_with()
        self.assertIs(worker.failure, error)
        self.assertEqual(len(self.thread_errors), 1)
        self.assertIs(self.thread_errors[0].exc_value.__cause__, error)

    def test_observer_can_self_stop_and_reenter_without_self_wait(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        callback = Mock()
        worker.register_on_terminated(callback)
        worker.post_task(task)
        worker.post_task(None)
        worker.start()
        self.wait(task_entered)
        run = worker._capture_run()
        results = []

        def observer(observed_run, failure):
            results.append((observed_run, failure, worker.stop()))
            worker.start()

        worker._observe_run(run, observer)
        task_release.set()
        run.thread.join(3)
        self.assertFalse(run.thread.is_alive())
        self.assertEqual(results, [(run, None, False)])
        self.assertIs(worker.thread, run.thread)
        self.assertTrue(worker.stop())
        callback.assert_called_once_with()

    def test_late_old_generation_observation_does_not_change_new_run(self):
        worker = self.worker()
        task, task_entered, task_release = self.blocking_task()
        old_error = RuntimeError("old task error")
        worker.post_task(task)
        worker.post_task({"runnable": Mock(side_effect=old_error)})
        worker.start()
        self.wait(task_entered)
        old_run = worker._capture_run()
        task_release.set()
        old_run.thread.join(3)
        self.assertFalse(old_run.thread.is_alive())
        worker.start()
        new_run = worker._capture_run()
        self.assertIsNot(new_run, old_run)
        self.assertIsNotNone(new_run)
        old_observer, new_observer = Mock(), Mock()
        worker._observe_run(new_run, new_observer)
        worker._observe_run(old_run, old_observer)
        old_observer.assert_called_once_with(old_run, old_error)
        new_observer.assert_not_called()
        self.assertIsNone(worker.failure)
        self.assertIs(worker._capture_run(), new_run)
        self.assertTrue(worker.stop())
        new_observer.assert_called_once_with(new_run, None)
        old_observer.assert_called_once_with(old_run, old_error)

    def test_failure_racing_observer_registration_delivers_exactly_once(self):
        worker = self.worker()
        ready = threading.Event()
        race = threading.Barrier(3, timeout=3)
        error = ValueError("registration race")

        def task(_):
            ready.set()
            race.wait()
            raise error

        worker.post_task({"runnable": task})
        worker.start()
        self.wait(ready)
        run = worker._capture_run()
        observer = Mock()
        registered = threading.Event()

        def register():
            race.wait()
            worker._observe_run(run, observer)
            registered.set()

        self.thread(register)
        race.wait()
        self.wait(registered)
        self.assertFalse(worker.stop())
        observer.assert_called_once_with(run, error)
