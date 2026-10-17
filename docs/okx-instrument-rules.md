# Opt-in OKX spot instrument rules

`OkxSpotRulesReader` provides public metadata. `OkxTrader` has a constructor-only,
default-off limit preflight option; existing factory/session paths do not enable it.
Supported currencies remain BTC/ETH/DOGE/XRP-USDT.

## Injection and cache contract

Construct `OkxSpotRulesReader(transport, clock, ttl=60, capacity=128)` with:

- `transport(path, params=...)`, returning a decoded OKX JSON envelope. The only
  requested path is `/api/v5/public/instruments`, with `instType=SPOT` and the
  exact requested `instId`. Authentication and environment lookup are absent.
- A monotonic seconds clock. Construction invokes neither dependency.

`get("BTC-USDT")` returns validated frozen `OkxSpotRules`. Cache entries have a
positive finite TTL and a positive integer maximum capacity; eviction is LRU.
Expiry is inclusive at the deadline and measured from request start. A request
that takes longer than the TTL is returned fresh but not cached. No background
requests occur. The reader is single-owner; serialize access if sharing it.

`get("BTC-USDT", refresh=True)` invalidates any entry before refreshing.
Transport errors propagate; malformed metadata raises `InstrumentRulesError`.
Failed refreshes never restore a previous cached result. An expired entry is
never used as a fallback. Returned rules cannot be mutated and do not retain a
mutable reference to the transport's JSON response.

## Metadata and units

Responses must contain exactly one matching SPOT instrument and coherent
base/quote currencies. `tickSz`, `lotSz`, and `minSz` must be positive finite
ASCII decimal strings (scientific notation is accepted; whitespace, digit
separators, and Unicode digits are rejected). They become immutable `Decimal` values. A well-formed suspended
instrument or non-USDT spot pair remains representable.

`is_live_usdt_spot` expresses only public metadata eligibility. It is not account
readiness, exchange permission, order authorization, or a guarantee of execution.
Unknown nonempty instrument states are representable but not eligible.

`validate_price(price)`, `validate_base_quantity(quantity)`, and
`validate_limit_order(price, base_quantity)` raise `InstrumentRulesError` on
invalid values. Price must be an exact tick multiple; base quantity must be an
exact lot multiple and meet the independent minimum. Exact integer-ratio checks
support increments such as `0.25` and `0.003`, without ambient Decimal-context
rounding. Inputs are neither rounded nor modified. Use strings or Decimal when
exact source precision matters; already-rounded float inputs cannot be recovered.

These checks do not check eligibility and do not accept or validate quote-currency
market-buy budgets. `lotSz` and `minSz` are base-currency quantities, so applying
them directly to USDT budgets would be a unit error.

## Strict snapshots and opt-in limit preflight

`get_snapshot(instId, refresh=False)` returns an immutable `OkxRulesSnapshot`
with rules, request-start time and expiry. Unlike legacy `get`, a slow response
at or after expiry raises `InstrumentRulesError`, and is never cached. Invalid,
nonfinite or backward-during-request clock readings fail closed. `require_fresh`
rechecks the snapshot. Strict calls serialize transport/cache access using a
separate reader lock; do not mix concurrent legacy `get` and strict calls.

`OkxTrader(..., limit_preflight=True, rules_reader=reader)` opts in explicitly.
The flag is keyword-only and must be a real boolean. A reader alone does not
activate it. Without injection, enabling constructs a per-trader public reader
with a monotonic clock and 60-second TTL; construction makes no requests. Public
instrument reads are unsigned. There is no environment or factory activation.

Enabled limit orders parse positive finite Decimal price/base amount once,
check the exact matching live USDT SPOT instrument, tick, lot and independent
minimum, and serialize those same values as fixed-point strings. No float or
eight-decimal rounding is applied to this payload. Local balance checks use
exact rational comparisons. Markets retain their existing formatting/units and
never read metadata. Numeric zero-price hold, cancel and unsupported order
handling precede metadata. Booleans and nonfinite values are rejected.

A failed metadata read/validation produces one standard local rejection with no
creation dispatch, balance/asset change, or order registration. After signing,
freshness is checked again immediately before the existing admission/dispatch
mark. This is a local boundary check, not an exchange-side freshness guarantee:
time may pass between the check and exchange receipt. Admission closure still
prevents dispatch. No order lock is held across public transport. Immutable
prepared payload values and thread-local context isolate concurrent submissions;
duplicate ownership and unknown-outcome retention are unchanged. A timeout after
creation remains unknown, without rejection or automatic resend.

## Follow-on work, separately reviewable

Factory/session activation remains a separate decision. This constructor-only
option is not permission to enable live trading. USDT strategy work is separate: BNH, SMA, RSI,
and LLM settlement paths round cash changes to whole units, while several
strategies floor base quantities to four decimals. Minimum budgets (often 5000)
and session quote-currency handling need exchange-aware policies before broader
asset support. This helper changes none of those behaviors. Maximum sizes,
notional limits, private instruments, fees, account readiness, and live/demo
trading are outside this slice.

## Offline verification

`tests/unit_tests/okx_order_rules_test.py` and `okx_limit_preflight_test.py` use synthetic envelopes, a fake
transport, and an injected deterministic clock. It needs no exchange account.
Run it with existing OKX regressions, then `python -m pytest tests/unit_tests -q`
in a credential-free process with network access blocked.

References: [public instruments](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments)
and [place order](https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order).
