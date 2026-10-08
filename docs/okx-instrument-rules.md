# Opt-in OKX spot instrument rules

`OkxSpotRulesReader` is a standalone public metadata helper. No existing trader,
factory, supported-currency list, formatting, or submission path calls it.

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

## Follow-on work, separately reviewable

Runtime activation needs an explicit failure/refresh/rounding policy and must
preserve submission ownership. USDT strategy work is separate: BNH, SMA, RSI,
and LLM settlement paths round cash changes to whole units, while several
strategies floor base quantities to four decimals. Minimum budgets (often 5000)
and session quote-currency handling need exchange-aware policies before broader
asset support. This helper changes none of those behaviors. Maximum sizes,
notional limits, private instruments, fees, account readiness, and live/demo
trading are outside this slice.

## Offline verification

`tests/unit_tests/okx_order_rules_test.py` uses synthetic envelopes, a fake
transport, and an injected deterministic clock. It needs no exchange account.
Run it with existing OKX regressions, then `python -m pytest tests/unit_tests -q`
in a credential-free process with network access blocked.

References: [public instruments](https://www.okx.com/docs-v5/en/#public-data-rest-api-get-instruments)
and [place order](https://www.okx.com/docs-v5/en/#order-book-trading-trade-post-place-order).
