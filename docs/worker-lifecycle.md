# Worker completion and lifecycle

`Worker` is a FIFO task executor, not a trading admission or settlement barrier.
Its existing dictionary task API (`runnable(task)`) and explicit `start()` /
`stop()` reuse remain supported.

- Each dequeued item is accounted for once, after its runnable returns or raises.
  `task_queue.join()` therefore waits for execution to end, but is not evidence
  that tasks succeeded. It can remain blocked when unexecuted work is queued.
- `stop()` appends one generation-owned stop marker and waits for that captured
  thread to exit, including its termination callback. It returns `True` only for
  a clean exit (or a Worker that has never started), and `False` for a failed
  generation. It does not wait for work posted after its marker.
- Calling `stop()` from the worker itself requests shutdown and returns `False`
  immediately. Neither the runnable nor the termination callback can join itself.
- `start()` is a no-op while a prior thread is alive, including during shutdown
  and its callback. After actual exit, explicit start runs the retained backlog.
  An old stop waiter cannot clear a newer generation's thread or use its outcome.
- Posts before first start, while closing, and after stop remain accepted. Tasks
  behind the stop marker are retained for explicit restart, not discarded. The
  legacy `post_task(None)` stop sentinel remains supported. Internal markers left
  by an earlier failed generation do not stop a later generation.
- An unhandled task exception stops that generation. No later runnable executes
  in it and no automatic retry/restart occurs. `failure` exposes its first error;
  a subsequent explicit start resets that latest-generation outcome. The existing
  thread exception signal is retained. A failed runnable itself is not requeued.
- The registered termination callback is attempted once on the worker thread,
  after normal or failed execution. A callback exception is observable as failure;
  if execution already failed, that original error remains the primary failure.
  Lifecycle locks do not surround task execution, callbacks, or thread joins.

A stopped worker can have unfinished queued work. A successful stop does not
prove a trading session is safe to restart, replace, or delete; the application
must add generation checks, trader admission/fences, and unresolved-order guards.
A fence must report its own successful execution or failure, never infer success
from `thread is None`, an empty queue, or queue task accounting alone. Those
application-level changes are intentionally separate from this prerequisite.

There is no timeout or forced interruption here. If a runnable or callback never
returns, an external stop can wait indefinitely. Directly replacing `thread` or
`task_queue` while a generation runs is unsupported.

## Safe verification

Run `python -m pytest tests/unit_tests/worker_test.py -q`, followed by the normal
unit suite in an isolated, dependency-ready environment without real credentials
or outbound networking. Tests use synthetic tasks and Events/Barriers, not real
exchange requests or sleep-based races. No account setup is needed.
