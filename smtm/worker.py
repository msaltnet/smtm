import queue
import threading
import traceback
from typing import Dict, Any, Callable, Optional
from .log_manager import LogManager


class _WorkerRun:
    """Generation-local outcome and stop marker; never a runnable task."""

    def __init__(self, task_queue):
        self.task_queue = task_queue
        self.thread = None
        self.stopping = False
        self.failure = None
        self.terminal = False
        self.observers = []


class Worker:
    """Run FIFO dictionary tasks on one background thread at a time.

    A task's ``runnable`` receives the task itself. Posts remain accepted before
    start, during stop and after stop, for compatibility. Work after a stop marker
    stays queued for an explicit restart; this Worker is NOT an admission fence.
    Queue completion means execution ended (possibly with an error), not success.
    """

    def __init__(self, name: str) -> None:
        self.task_queue = queue.Queue()
        self.thread = None
        self.name = name
        self.logger = LogManager.get_logger(name)
        self.on_terminated = None
        self._lifecycle_lock = threading.Lock()
        self._run = None

    @property
    def failure(self) -> Optional[BaseException]:
        """First error from the latest generation, reset by explicit start only."""
        with self._lifecycle_lock:
            return None if self._run is None else self._run.failure

    def register_on_terminated(self, callback: Optional[Callable[[], None]]) -> None:
        """Register a callback attempted once on the worker thread as it exits.

        Also called after a task fails. The thread is still alive during this
        callback; stop() from here only requests shutdown and returns False.
        """
        with self._lifecycle_lock:
            self.on_terminated = callback

    def post_task(self, task: Optional[Dict[str, Any]]) -> None:
        """Enqueue a task even while stopped; None retains its legacy stop meaning."""
        self.task_queue.put(task)

    def _capture_run(self):
        """Capture the active generation, or None when it cannot accept a fence."""
        with self._lifecycle_lock:
            run = self._run
            if (run is None or run.stopping or run.terminal
                    or run.failure is not None or not run.thread.is_alive()):
                return None
            return run

    def _observe_run(self, run, callback):
        """Observe one captured generation once, never under the lifecycle lock.

        callback(run, error) reports its first failure or task-loop end (None).
        Clean loop end is reported before the public termination callback and
        does not establish fence success. Late observers receive cached state
        synchronously, including any later termination-callback failure.
        """
        with self._lifecycle_lock:
            if run is not None and not run.terminal and run.failure is None:
                run.observers.append(callback)
                return
            failure = None if run is None else run.failure
        self._notify_observers(run, [callback], failure)

    def _notify_observers(self, run, observers, failure):
        for callback in observers:
            try:
                callback(run, failure)
            except BaseException:
                # Internal observation cannot change execution outcome or
                # prevent the public termination callback from being attempted.
                self.logger.error(traceback.format_exc())

    def _record_failure(self, run, error):
        observers = []
        with self._lifecycle_lock:
            if run.failure is None:
                run.failure = error
                observers, run.observers = run.observers, []
        self._notify_observers(run, observers, error)
        self.logger.error(traceback.format_exc())

    def _looper(self, run):
        # Thread.start is serialized with stop; leave that startup critical
        # section before invoking any task or termination callback.
        with self._lifecycle_lock:
            pass
        try:
            while True:
                task = run.task_queue.get()
                try:
                    if task is None or task is run:
                        break
                    if isinstance(task, _WorkerRun):
                        # A failed/legacy-stopped generation can leave its marker
                        # queued. It must not terminate a later explicit restart.
                        continue
                    task["runnable"](task)
                except BaseException as error:
                    # Publish failure before accounting for this finished task.
                    self._record_failure(run, error)
                    raise
                finally:
                    run.task_queue.task_done()
        except BaseException as error:
            if run.failure is None:
                self._record_failure(run, error)
        finally:
            with self._lifecycle_lock:
                run.stopping = True
                run.terminal = True
                observers, run.observers = run.observers, []
                failure = run.failure
                callback = self.on_terminated
            self._notify_observers(run, observers, failure)
            try:
                if callback is not None:
                    callback()
            except BaseException as error:
                self._record_failure(run, error)

        if run.failure is not None:
            # Preserve fail-stop and the existing thread exception signal. No
            # queued runnable is retried or executed after this generation fails.
            raise UserWarning("Worker caught exception. Force stop!") from run.failure

    def start(self) -> None:
        """Start explicitly, or do nothing while the previous thread is alive.

        A clean or failed generation can be restarted after actual thread exit.
        This preserves queued work, including work posted after the stop marker.
        Application-level admission/recovery decisions belong to the caller.
        """
        with self._lifecycle_lock:
            if self._run is not None and self._run.thread.is_alive():
                return
            run = _WorkerRun(self.task_queue)
            run.thread = threading.Thread(
                target=lambda: self._looper(run), name=self.name, daemon=True
            )
            previous_run, previous_thread = self._run, self.thread
            self._run = run
            self.thread = run.thread
            try:
                run.thread.start()
            except Exception:
                # Thread creation failed before there was anything to join.
                self._run, self.thread = previous_run, previous_thread
                raise

    def stop(self) -> bool:
        """Request stop after earlier FIFO tasks and join the captured generation.

        True means that generation exited without a task/termination-callback
        error (or no thread was started). False means failure, or a self-stop that
        only requested shutdown. Inspect failure for the latest generation.
        This does not wait for late queued work, stop producers, or prove orders
        settled. A blocked runnable/callback can block an external stop.
        """
        with self._lifecycle_lock:
            run = self._run
            if run is None:
                return True
            if run.thread.is_alive() and not run.stopping:
                run.stopping = True
                run.task_queue.put(run)

        if run.thread is threading.current_thread():
            return False
        run.thread.join()
        with self._lifecycle_lock:
            # A concurrent explicit start may already own a newer generation.
            if self._run is run:
                self.thread = None
            return run.failure is None
