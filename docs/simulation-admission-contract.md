# Opt-in synchronous simulation admission

This capability is inactive until explicitly selected. `TradingOperator` and
`SessionManager` do not use it. Existing unmanaged simulation remains synchronous
and keeps its public order, quote, cancellation and result behavior. No additional
Worker, queue, timer, network call or background thread is created.

## API and execution model

```python
control = trader.get_admission_control()  # inert
handle = control.open_run()              # explicit, permanent managed opt-in
handle.update_quote("BTC", 100)
admitted = handle.submit(requests, callback)
fence = handle.close()                   # never waits for callbacks
outcome = fence.wait()                   # external wait, no timeout promise
```

The handle is an immutable identity for one run. Unlike exchange handles,
simulation calls execute inline on their caller's thread; they do not require or
fabricate a Worker generation. `submit` and `update_quote` return `False` when
admission is closed/stale, without a synthetic result callback. `True` means the
call was admitted, not that every request filled or was processed before closure.
An execution/callback exception is recorded and re-raised. Request iteration is
materialized before admission, outside the controller lock.

Managed request snapshots contain plain scalar/dict/list data (tuple values are
copied as lists); numeric order fields are converted before the final gate.
Custom metadata objects are rejected before accounting rather than invoking
their copy/hash/equality hooks under the state lock. Legacy payload handling is
unchanged.

Getting the controller changes nothing. First `open_run` refuses legacy calls or
callbacks still active, and legacy pending orders: it cannot silently adopt work
without a run owner. Resolve those orders through the existing cancellation API
before opting in. After opt-in, unbound `send_request` and `update_quote` raise;
all new submissions and quotes must use the captured handle. There is no downgrade.
Opening also validates inherited account state: plain currency/map keys, finite
nonnegative balances/assets/commission and positive quotes. It refuses custom
Python objects rather than executing their hooks under the accounting lock.
Direct mutation of internal account maps while managed is unsupported.

## Final claims and closure

One admission/state lock serializes close with quote-cache updates and each
individual registration/accounting claim. Request copying, numeric conversion
and validation occur before the final claim. Callbacks run outside the lock.

For quote processing, snapshot exact `(id, entry, owner run)` identities in
registration order. Before each fill, recheck that the handle is still open and
that the exact entry still belongs to it. Deliver that entry's callback before
examining the next entry, preserving callback-driven cancellation/interleaving.

If close wins before a claim, no new reservation/fill occurs. If a fill already
claimed accounting before close, its original callback may finish afterward.
For example, close during callback 1 prevents a new claim for entry 2; entry 2
stays pending with its reservation and original callback. There is no fresh
post-close quote API, and queued producer work carrying an old handle cannot
update the quote cache or affect a later run.

The initial `requested` callback must exit before a terminal callback for that
entry. A cancellation during that callback records a deferred cancellation;
the cancellation call can return before the terminal callback. A qualifying quote
during that callback retains its first eligible price on the exact entry. On
initial callback exit, deferred cancellation takes precedence. Otherwise the
deferred fill must pass the same final open-run gate. Closure or callback failure
prevents that unclaimed fill. No callback is retried automatically.

## Fence outcomes and limits

Simulation shares the exchange `AdmissionOutcome` values:

- `admission_closed`: the gate is closed but admitted calls/callbacks are active
- `submission_fence_reached`: admitted calls returned or rejected their remaining
  work; no failure occurred in that prefix
- `execution_failure`: an admitted call failed; `failure` retains its first error

Close is idempotent and never waits. Counts include nested calls and callbacks.
`wait` from a thread currently executing that run returns its current outcome
instead of deadlocking on itself. A blocked call/callback has no bounded wait.
A failure fence may become complete while another admitted call is still active;
`open_run` independently rejects until **all** prior calls/callbacks have exited.

Later low-level handles may be opened after this quiescence; this does not grant
permission to restart a session or reuse its budget. Their quotes target only
their own entries. Prior pending orders remain frozen and explicitly cancelable,
with their original owners and reservations. No old order is adopted or erased.

`cancel_request` and `cancel_all_requests` remain usable after close. They claim
exact entries and invoke the original callback outside locks. A cancellation
begun after a reached fence is not part of its proven prefix. A later failure
cannot turn an already reached fence into failure. When a new handle explicitly
submits cancellation of an older order, an escaping callback error also fails
that new admitted call's run; it does not transfer the order's callback ownership.

Neither a reached fence nor an empty pending map proves all callbacks succeeded,
settlement, safe restart/replacement/removal, or permission to release a budget.
Future lifecycle activation must close producers/admission, establish the call
prefix, cancel/check retained ownership, and apply session-level fail-closed
guards together. This patch does not activate any of those session policies.

## Simulation ownership diagnostics

Managed logical request IDs are unique for the trader's lifetime. Repeated IDs
are suppressed, including replay after settlement; existing unmanaged ID behavior
is unchanged. `get_submission_status()` returns a detached map with `state` and
`callback_failed` for each valid managed ID:

- `preparing`: owned before validation/final claim
- `not_dispatched`: stopped before an accounting/registration claim (the name is
  shared vocabulary only; simulation performs no exchange dispatch)
- `pending`: reservation and original callback remain owned
- `settling`: terminal accounting is claimed and publication is in progress
- `settled`: the terminal callback attempt returned normally
- `settlement_failed`: terminal processing or its callback raised

An initial callback error leaves its order pending and sets `callback_failed`.
The flag is sticky, even if a later explicit cancellation callback succeeds.
Failed records retain their original request/callback, known result and error;
successful records may release those references but keep ID/run tombstones.
These are in-memory simulation outcomes, never fabricated exchange `unknown`
states. There is no persistence, pruning, retry or manual-clear/recovery API.

## Safe verification

`simulation_admission_test.py` exercises deterministic Events/Barriers, synthetic
quotes/orders, reentry, failure, exact ownership and stale producer Worker tasks.
Run it and the existing simulation/admission/Worker tests first, then:

```sh
python -m pytest tests/unit_tests -q
```

Do not load secrets or run live exchange/integration tests. A guarded local
stdlib harness is limited verification and is reported separately from normal
Python 3.9/3.10/3.11 CI. The optional capability does not certify custom traders.
