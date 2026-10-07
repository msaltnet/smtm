"""Opt-in submission admission, not settlement or session-lifecycle safety."""
from dataclasses import dataclass, field
from enum import Enum
import threading


class AdmissionOutcome(str, Enum):
    ADMISSION_CLOSED = "admission_closed"
    SUBMISSION_FENCE_REACHED = "submission_fence_reached"
    EXECUTION_FAILURE = "execution_failure"


class _AdmissionClosed(RuntimeError):
    """Internal rejection before creation transport; never an exchange result."""


class _AdmissionRun:
    def __init__(self, generation):
        self.generation = generation
        self.open = True
        self.closed = False
        self.outcome = None
        self.failure = None
        self.completed = threading.Event()


@dataclass(frozen=True, eq=False)
class SubmissionFence:
    """Read-only view of a closed run's submission prefix.

    Reached means queued submissions were processed/rejected, not that any order
    settled. A blocked task can block wait forever. On the owning worker thread,
    wait returns the current outcome instead of waiting for itself.
    """
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
        if threading.current_thread() is not self._run.generation.thread:
            self._run.completed.wait()
        return self.outcome


@dataclass(frozen=True, eq=False)
class AdmissionHandle:
    """Opaque, immutable identity for exactly one explicitly opened run."""
    _control: object = field(repr=False)
    _run: object = field(repr=False)

    def submit(self, request_list, callback):
        """Return whether the whole batch was admitted; no rejection callback."""
        return self._control._submit(self._run, request_list, callback)

    def close(self):
        """Close immediately and return a fence; never wait for the worker."""
        return self._control._close(self._run)


class ExchangeAdmissionControl:
    """Internal capability implementation for participating exchange adapters.

    Merely retrieving this object is inert. open_run permanently selects managed
    submission for this trader; there is no downgrade to legacy admission.
    """
    def __init__(self, trader):
        self._trader = trader
        self._lock = threading.Lock()
        self._managed = False
        self._active = None

    def open_run(self):
        """Create a fresh identity on an already running Worker.

        No automatic restart or recovery. Opening a new run after a fence says
        nothing about old exchange orders or permission to reuse their budget.
        """
        generation = self._trader.worker._capture_run()
        with self._lock:
            if self._active is not None and not self._active.completed.is_set():
                raise RuntimeError("Previous admission run has not completed its fence")
            if generation is None:
                raise RuntimeError("Admission requires a running Worker generation")
            run = _AdmissionRun(generation)
            self._managed = True
            self._active = run
        # Worker caches terminal state, so completion between capture and this
        # registration cannot be lost. Never call it while holding our lock.
        self._trader.worker._observe_run(
            generation, lambda captured, failure: self._generation_ended(run, failure)
        )
        return AdmissionHandle(self, run)

    def _allows_locked(self, run):
        return not self._managed or (run is self._active and run.open)

    def _allows(self, run):
        with self._lock:
            return self._allows_locked(run)

    def _submit(self, run, request_list, callback):
        # Materialize caller iteration outside the lock: no user iterator code
        # can reenter close while we serialize enqueue with the fence.
        requests = list(request_list)
        with self._lock:
            if not self._allows_locked(run):
                return False
            for request in requests:
                self._trader.worker.post_task({
                    "runnable": self._trader._execute_order,
                    "request": request, "callback": callback,
                    "_admission_run": run,
                })
            return True

    def _close(self, run):
        with self._lock:
            if not run.closed:
                run.open = False
                run.closed = True
                if run.outcome is None:
                    run.outcome = AdmissionOutcome.ADMISSION_CLOSED
                if not run.completed.is_set():
                    self._trader.worker.post_task({
                        "runnable": lambda task: self._reach_fence(run),
                    })
            return SubmissionFence(self, run)

    def _finish_locked(self, run, outcome, failure=None):
        if not run.completed.is_set():
            run.open = False
            run.outcome = outcome
            run.failure = failure
            run.completed.set()

    def _reach_fence(self, run):
        with self._lock:
            self._finish_locked(run, AdmissionOutcome.SUBMISSION_FENCE_REACHED)

    def _generation_ended(self, run, failure):
        with self._lock:
            self._finish_locked(run, AdmissionOutcome.EXECUTION_FAILURE, failure)
