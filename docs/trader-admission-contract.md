# Opt-in exchange admission and submission fences

This is an **inactive capability**, available on the built-in Upbit, Binance,
OKX and Bithumb traders. `TradingOperator` and `SessionManager` do not call it.
Existing unmanaged callers keep their current API and behavior. There is no
production lifecycle activation, automatic restart, cancellation sweep or
unknown-order recovery in this change.

## API and outcomes

`Trader.get_admission_control()` is optional and non-abstract. Its default is
`None` (unsupported), so existing custom implementations remain instantiable.
`SimulationTrader` also returns `None`: quote-driven fills and `send_request`
must share a real coordination boundary before simulation can participate.

For participating exchange traders, retrieving the controller is inert:

```python
control = trader.get_admission_control()
handle = control.open_run()           # explicit opt-in, existing live Worker
accepted = handle.submit(requests, callback)
fence = handle.close()                # closes now; never waits for the worker
outcome = fence.wait()                # optional external wait; no timeout promise
```

The immutable handle identifies one run. `submit` returns whether the entire
batch was admitted to the queue, not whether an exchange accepted it. Closing is
idempotent. A closed handle never reopens, including after explicit Worker
restart. `open_run` refuses an overlapping open/pending run or an inactive Worker;
it never starts a Worker. A later explicit run gets a different identity. This
low-level operation is **not permission to restart a session or reuse budget**.

A fence exposes `outcome`, `done`, and `failure`:

- `admission_closed`: admission is closed; its queued prefix is still pending
- `submission_fence_reached`: its FIFO fence task executed, after its admitted
  submission prefix was processed or rejected
- `execution_failure`: that generation failed or stopped before reaching the
  fence; the prefix is not proven processed. `failure` carries the recorded
  exception when available. A clean early stop has no exception

Only the latter two are complete. `close()` never waits. `wait()` has no bounded
completion guarantee and can block on a queued task or its callback. On the
owning Worker thread, it returns the current outcome without self-waiting;
`admission_closed` from a reentrant callback is still pending, not success.
Repeated `close()` calls return views of the same outcome.

## Ordering and dispatch

One admission lock serializes whole-batch enqueue, closure/fence enqueue, and the
final possible-dispatch mark. Requests queued by a handle carry that original
identity. Closed or stale work is rejected when execution begins, even if a later
Worker generation encounters it. Rejection creates no synthetic exchange-result
callback and performs no creation request.

The same gate is checked again at `_mark_creation_dispatch`, after price reads,
payload preparation and signing. Closing during those operations prevents the
later creation request. The mark is the conservative possible-dispatch boundary
introduced in [the order-submission contract](order-submission-contract.md).
If it wins the race with close, that creation remains dispatched/owned even if
the physical HTTP call starts slightly later. Network calls and strategy
callbacks run outside the admission and ownership locks.

Once `open_run()` explicitly selects managed mode, it is permanent for that
trader. Legacy `send_request()` then raises instead of admitting unbound work.
Legacy queued/direct `_execute_order` work is rejected, and direct private
creation helpers cannot bypass the dispatch gate. Merely obtaining the
controller does not enable this restriction. Cancellation/query transports keep
their existing policy; this is a submission fence, not a cancellation protocol.

Requests already dispatched retain the existing ledger/callback owner, whether
the exchange ID is known, the result is unknown, or settlement is in progress.
There is no retry, deletion or automatic resolution of those records.

## Generation completion and limitations

A small private Worker observer captures one active generation. Registration is
atomic with cached first failure/task-loop termination; late registration cannot
miss either. Notification runs outside the Worker lifecycle lock. First failure
or clean task-loop end explicitly fails any pending fence before the public
termination callback can block. The public callback is still attempted once,
with its existing failure and `stop()` semantics. A later callback error remains
available in the Worker generation's cached failure; a fence already failed at
clean loop end need not contain that later exception.

Observers are one-shot and retained until that Worker generation ends; repeated
open/close cycles on a long-lived generation therefore retain small observation
records. Submission-ledger tombstones also retain their run identity. This slice
has no observer/tombstone pruning or durable recovery policy.

Old-generation notifications affect only their captured
admission run. Already reached fences stay reached if later unrelated work
fails. Notification describes inability to execute more tasks, **not physical
thread exit**; actual joining remains `Worker.stop()`'s responsibility. A blocked
runnable still has no bounded completion guarantee.

A reached fence proves only the submission prefix. It does **not** prove exchange
settlement, callback quiescence for polling/cancellation, safe restart, safe
replacement/removal, or permission to release a budget. Neither empty
`order_map`, a `settled` ledger entry, `queue.join()`, nor `Worker.stop() == True`
substitutes for those application-level checks.

## Before lifecycle activation

Operator producer generations and minimum session restart/replacement/removal
protections must activate together in a separate change. Simulation needs actual
quote/fill coordination. Requiring this capability from custom traders is a
compatibility/product decision that must be made separately.

A custom `BaseExchangeTrader` subclass is **not certified merely by inheriting**
the accessor. It must route all new-order executions through `track_submission`
and every physical creation through `_mark_creation_dispatch` after preparation,
without side transport paths or retries. It must preserve ownership after that
boundary. These assumptions are tested for the four built-in adapters here.
The existing cancellation deep-copy limitation is separate and must be handled
before cancellation joins a managed lifecycle protocol.

## Safe verification

`trader_admission_test.py` and `worker_test.py` use Events/Barriers, synthetic
credentials, patched transport and no sleeps for race ordering. They cover
batch/close serialization, stale generations, preparation/dispatch races,
known/unknown ownership, cached failure, early termination, reentrant close and
unchanged unmanaged capability behavior. Run focused tests first, then:

```sh
python -m pytest tests/unit_tests -q
```

Do not use live credentials or exchange integration tests. Hermetic local
stdlib-harness checks are limited verification, reported separately from the
normal Python 3.9/3.10/3.11 CI suite.
