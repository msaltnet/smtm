"""Synchronous simulation admission; no queue, Worker or settlement guarantee."""
from contextlib import contextmanager
from dataclasses import dataclass, field
import threading

from .admission import AdmissionOutcome


class _SimulationRun:
    def __init__(self):
        self.open = True
        self.closed = False
        self.calls = 0
        self.threads = {}
        self.outcome = None
        self.failure = None
        self.completed = threading.Event()


@dataclass(frozen=True, eq=False)
class SimulationSubmissionFence:
    """The admitted call prefix only; later cancellation is not covered."""
    _control: object = field(repr=False)
    _run: object = field(repr=False)

    @property
    def outcome(self):
        with self._control._lock:
            return self._run.outcome

    @property
    def failure(self):
        with self._control._lock:
            return self._run.failure

    @property
    def done(self):
        return self._run.completed.is_set()

    def wait(self):
        with self._control._lock:
            executing = self._run.threads.get(threading.get_ident(), 0)
        if not executing:
            self._run.completed.wait()
        return self.outcome


@dataclass(frozen=True, eq=False)
class SimulationAdmissionHandle:
    """Immutable identity; execution and callbacks stay on the calling thread."""
    _control: object = field(repr=False)
    _run: object = field(repr=False)

    def submit(self, request_list, callback):
        requests = list(request_list)
        return self._control._call(
            self._run,
            lambda: self._control._trader._submit_managed(
                self._run, requests, callback),
        )

    def update_quote(self, currency, price):
        return self._control._call(
            self._run,
            lambda: self._control._trader._quote_managed(
                self._run, currency, price),
        )

    def close(self):
        return self._control._close(self._run)


class SimulationAdmissionControl:
    """Inert until open_run; permanent opt-in, with no new executor thread."""
    def __init__(self, trader):
        self._trader = trader
        self._lock = threading.Lock()
        self._managed = False
        self._active = None
        self._calls = 0
        self._legacy_calls = 0

    def open_run(self):
        with self._lock:
            if self._calls or self._legacy_calls:
                raise RuntimeError("Simulation calls or callbacks are still active")
            if self._active is not None and not self._active.completed.is_set():
                raise RuntimeError("Previous admission run has not completed its fence")
            self._trader._validate_managed_state()
            if not self._managed and self._trader.pending_orders:
                raise RuntimeError("Resolve legacy pending orders before managed admission")
            self._managed = True
            self._active = _SimulationRun()
            return SimulationAdmissionHandle(self, self._active)

    @contextmanager
    def _legacy(self):
        with self._lock:
            if self._managed:
                raise RuntimeError("Managed simulation requires an admission handle")
            self._legacy_calls += 1
        try:
            yield
        finally:
            with self._lock:
                self._legacy_calls -= 1

    @contextmanager
    def _existing(self):
        # Cancellation remains usable after close. Count even its lookup/snapshot
        # window so first opt-in or a later run cannot overlap an old callback.
        with self._lock:
            managed = self._managed
            self._calls += 1
        try:
            yield managed
        finally:
            with self._lock:
                self._calls -= 1

    def _allows_locked(self, run):
        return run is self._active and run.open

    def _call(self, run, action, require_open=True):
        thread = threading.get_ident()
        with self._lock:
            if require_open and not self._allows_locked(run):
                return False
            self._calls += 1
            run.calls += 1
            run.threads[thread] = run.threads.get(thread, 0) + 1
        try:
            action()
            return True
        except BaseException as error:
            with self._lock:
                self._finish_locked(run, AdmissionOutcome.EXECUTION_FAILURE, error)
            raise
        finally:
            with self._lock:
                self._calls -= 1
                run.calls -= 1
                run.threads[thread] -= 1
                if not run.threads[thread]:
                    del run.threads[thread]
                if run.closed and not run.calls:
                    self._finish_locked(run, AdmissionOutcome.SUBMISSION_FENCE_REACHED)

    def _close(self, run):
        with self._lock:
            run.open = False
            run.closed = True
            if run.outcome is None:
                run.outcome = AdmissionOutcome.ADMISSION_CLOSED
            if not run.calls:
                self._finish_locked(run, AdmissionOutcome.SUBMISSION_FENCE_REACHED)
            return SimulationSubmissionFence(self, run)

    @staticmethod
    def _finish_locked(run, outcome, failure=None):
        if not run.completed.is_set():
            run.open = False
            run.outcome = outcome
            run.failure = failure
            run.completed.set()
