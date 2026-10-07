# Order creation: one attempt and explicit uncertainty

The built-in Upbit, Binance, OKX and Bithumb traders retain the owner of each
logical new-order request before preparation begins. This is an in-process
transport prerequisite, not a complete session-stop or reconciliation protocol.
Paper trading and the public `Trader` abstract interface are unchanged.

## Creation-only transport policy

These creation requests use `retries=0` and `allow_redirects=False`:

- Upbit: POST `/v1/orders`
- Binance: POST `/api/v3/order`
- OKX: POST `/api/v5/trade/order`
- Bithumb legacy: POST `/trade/place`, `/trade/market_buy`, `/trade/market_sell`

A logical submission entering a built-in `_execute_order` may enter its creation
transport boundary at most once. Disabling redirects prevents a 307/308 from
replaying the POST. Non-2xx responses do not establish a usable acknowledgement.
Connection errors, timeouts, HTTP errors, malformed JSON, absent/invalid IDs and
unclassified exchange error responses remain uncertain after entering that
boundary. There is no new timeout setting and no automatic resubmission.

GET/query retries and cancellation policy are unchanged, including Bithumb's
POST queries and OKX/Bithumb POST cancellation. `request_with_retry` itself is
unchanged. Private sending helpers called directly still use one transport
attempt per call, but do not create a logical request/callback owner; managed
callers must use `send_request`, not call the private transport helpers.

## Ownership and diagnostics

Each built-in trader keeps an internal `_submissions` ledger, separately from
its known-ID `order_map`. Reservation and state updates use the adapter's order
lock; neither network calls nor client callbacks run under that lock. A
thread-local execution context identifies the correct submission across
concurrent invocations and callback reentry.

`get_submission_status()` returns a detached map keyed by local request ID.
Each value contains `state`, `dispatched`, and `exchange_id`:

- `preparing`: the request/callback is owned; no creation transport was entered
- `not_dispatched`: execution ended before creation transport was entered,
  including local rejection, hold/no-op, missing credentials or preparation error
- `unknown`: creation transport was entered, but no usable exchange ACK is known
- `known`: a usable ACK has been registered in known-ID order tracking
- `settling`: existing terminal validation claimed the order; terminal
  accounting/callback is still executing
- `settled`: the terminal accounting/callback attempt returned normally
- `settlement_failed`: that terminal accounting/callback attempt raised; no
  automatic retry or restoration of the claimed terminal order occurs

`dispatched` means the creation transport boundary was entered, not proof that
the exchange received or accepted an order. The flag is set immediately before
the physical request, after adapter validation, signing and price-optimization
reads. An exception after entry cannot safely prove nonexecution. This is a
conservative possible-dispatch boundary, not wire-level instrumentation;
HTTP-library-local failures after entry can also remain unknown.

Unknown submissions retain their original request and callback references.
They are never polled/cancelled with the local ID as if it were an exchange ID.
No success, rejection, terminal failure, or new `unknown` result dictionary is
sent to the strategy for an ambiguous submission: existing result consumers
could mistake a new result state for accounting. Local rejection behavior and
valid `requested`/terminal result shapes remain compatible.

Usable IDs are nonblank strings for Upbit, OKX and Bithumb, and positive int64
IDs for Binance (booleans are excluded). Bithumb requires status `"0000"`. OKX
creation requires exactly one data item and explicit envelope/item success;
integer `0` and string `"0"` success codes remain accepted. Query/cancel envelope
handling is unchanged. A missing/malformed acknowledgement is never interpreted
as confirmed nonexecution. Contradictory Upbit error/ID and Binance error-code/ID
ACKs also remain unknown.

The original callback stays attached to a known order. Its initial `requested`
result is a shallow snapshot taken before publication so concurrent terminal
settlement cannot turn it into a duplicate `done` callback. Polling is scheduled
in a finally block even if the initial callback raises. This does not guarantee
future Worker progress after a callback exception; existing Worker behavior is
unchanged. A known order is marked ACK-pending until that callback exits.
Concurrent/reentrant terminal observations are deferred (the order remains
tracked for polling), so a terminal callback cannot overtake the initial
requested callback. Reentrant cancellation can therefore complete its HTTP
request while its terminal callback waits for a later poll. Existing terminal
validation and exact-entry claiming still control accounting and terminal
callback attempts.

Local request IDs identify a logical submission for the lifetime of the trader.
Repeated or concurrent use of any reserved ID is suppressed, including a changed
payload, callback reentry and replay after settlement. A new logical request
must have a new ID. Finished/local-rejected records release request and callback
references but retain diagnostic ID tombstones; storage therefore grows with
unique request IDs. There is no persistence, pruning or force-clear API in this
patch. Unknown and failed-settlement ownership is not silently discarded.

## Explicit limits

An empty `order_map` does **not** mean safe, settled, or reusable. This diagnostic
ledger does not count queued work, establish an admission fence, close producer
generations, or prove that every callback has exited. In particular `settled`
only describes the terminal accounting/callback attempt, not global trader or
Worker completion. It must not be used alone as permission to
restart, replace, remove a session, or release its budget.

These records are lost when the process/trader is discarded. There is no
exactly-once exchange guarantee, exchange idempotency key, durable callback
delivery, automatic unknown-order recovery, manual resolution command, or
fail-closed session lifecycle activation. Those require separate integration.
The Worker completion work in merged #67 is present in the base; this
creation-policy patch adds no Worker lifecycle changes.

## Safe verification

`tests/unit_tests/order_submission_test.py` uses synthetic ACKs, patched physical
transport and deterministic Events/Barriers. It covers creation modes, transient
failure, redirects, malformed ACKs, pre-dispatch failure, duplicate ownership,
concurrent/reentrant callbacks, known terminal settlement and unchanged safe
query/cancel retries. Run focused adapter/retention tests first, then:

```sh
python -m pytest tests/unit_tests -q
```

Use an empty environment and no live account credentials. Do not run exchange
integration tests for this contract. Local guarded stdlib-harness results are
reported separately when pytest is unavailable; normal CI remains the full-suite
verification.

## References

- [Requests API: redirects](https://docs.python-requests.org/en/stable/api/)
- [Upbit order API](https://docs.upbit.com/kr/reference/new-order)
- [Binance spot new order](https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/trade)
- [OKX API v5](https://www.okx.com/docs-v5/en/)
- [Bithumb legacy limit order](https://apidocs.bithumb.com/v1.2.0/reference/지정가-주문하기)
- [Bithumb legacy market buy](https://apidocs.bithumb.com/v1.2.0/reference/시장가-매수하기)
- [Bithumb legacy market sell](https://apidocs.bithumb.com/v1.2.0/reference/시장가-매도하기)
