# Fractional strategy cash accounting

`cash_accounting` is an opt-in, **virtual-only** profile setting for the cash
balance maintained by a strategy. It removes whole-unit rounding from execution
cash deltas. It does not change order sizing, exchange rules, or live accounting.

## Profile contract

| Top-level field | Accepted value | Behavior |
| --- | --- | --- |
| `cash_accounting` | omitted or `"legacy"` | Preserve existing whole-unit rounding of each cash delta. |
| `cash_accounting` | `"fractional"` | Apply each cash delta without whole-unit rounding; requires explicit `"virtual": true`. |

The values are exact, case-sensitive strings. `null`, booleans, numbers, and
other strings are invalid. Fractional mode requires the actual boolean `true`;
omitting `virtual`, using `false`, or supplying a truthy string such as `"true"`
does not qualify. Existing legacy handling of `virtual` is unchanged.

Set the field at the top level, alongside `budget` and `virtual`:

```json
{
  "name": "sim-fractional-cash",
  "exchange": "UPB",
  "currency": "BTC",
  "budget": 500000,
  "strategy": "RSI",
  "term": 60,
  "virtual": true,
  "cash_accounting": "fractional"
}
```

This is profile configuration, not a command-line option. It is not inferred
from the exchange, currency, or budget. Placing it inside `strategy_params`
does not enable it: that existing mapping is still not forwarded to strategies
by session assembly.

Profile save/load validates the configuration. Session creation also validates
it independently before account lookup or Trader construction. Nonvirtual
fractional sessions are rejected, including OKX exchange-demo sessions that
still use the live adapter. Only `virtual: true` selects the in-memory simulator.
The selected market-data provider is unchanged; virtual mode alone does not
make market-data fetching offline.

## Cash arithmetic and fees

For a callback with `total = price * amount`, all four built-in strategies
(`BNH`, `SMA`, `RSI`, and `LLM`) use the selected accounting mode:

| Result | Legacy delta | Fractional delta |
| --- | --- | --- |
| Buy: cash deducted | `round(total + fee)` | `total + fee` |
| Sell: cash added | `round(total - fee)` | `total - fee` |

Legacy rounding remains Python's existing `round`, including ties-to-even. It
rounds the transaction delta, not the resulting balance or starting budget.

Fee selection is unchanged: an explicitly supplied callback `fee`, including
zero, takes precedence. If the fee field is absent, the strategy uses
`price * amount * commission_ratio` (the built-in default ratio is `0.0005`).
This change does not add fee-input validation or change how existing null/empty
fee values are handled.

`SimulationTrader` continues to use **zero fees**, regardless of its constructor
commission argument. Nonzero-fee examples below describe synthetic strategy
callbacks, not newly enabled simulator fees.

Each example starts independently with cash 300 and a fill notional of 10.25:

| Callback | Legacy cash | Fractional cash |
| --- | ---: | ---: |
| Buy, explicit fee 0 | 290 | 289.75 |
| Sell, explicit fee 0 | 310 | 310.25 |
| Buy, fee absent, ratio 0.0005 | 290 | 289.744875 |
| Sell, fee absent, ratio 0.0005 | 310 | 310.244875 |
| Buy, explicit fee 0.01 | 290 | 289.74 |

These illustrate callback arithmetic only. They are not a runnable small-budget
trading recipe. Requested callbacks remain pending without cash mutation, and
zero-value terminal callbacks with explicit fee zero do not change cash.

Fractional mode uses ordinary binary floating-point arithmetic. It does not
introduce `Decimal`, select a fixed number of currency decimal places, or
guarantee exact financial arithmetic. Compare calculated balances with an
appropriate floating-point tolerance. With the same zero-fee fills, fractional
strategy cash can be compared with the simulator's fractional cash ledger.

## Applying or changing the mode

Existing profiles need no rewrite; omission retains `legacy`. Saving an updated
profile does **not** change a running session's accounting mode or balances.
Create a fresh session from the profile, or stop the existing session and use
the existing stopped-session replacement flow. Simply stopping and starting the
same session does not select a new mode.

The default session also preserves the selection through `SystemOperator`
setup, `switch_profile`, and subsequent strategy replacement. An explicitly
present invalid value, including `null`, reaches the existing validation and
fails rather than silently selecting legacy accounting.

Default-session profile switching follows the existing **overlay** rule:
omitted fields inherit the current configuration. If the current default
session is fractional, switching a profile that omits `cash_accounting` keeps
fractional mode. Supply `"cash_accounting": "legacy"` explicitly to reset it.
This differs from creating an independent fresh session, where omission selects
legacy. Switching `virtual` to `false` while fractional mode is inherited is
rejected before account or Trader access; no live accounting mode is enabled.
Failed replacement leaves the previous session and configuration unchanged.
These are profile/API behaviors, not new command-line options.

The fresh session starts from its configured budget. This is not a balance
migration: historical rounding is not reconstructed or repaired, and old
positions, pending orders, and cash are not carried into the fresh virtual
Trader. Virtual state remains in memory and disappears on process restart.
Failed session replacement preserves the existing session and its allocation
under the existing rollback behavior.

For code integrations, `Strategy.initialize` and the four built-in implementations
accept the trailing optional argument `cash_accounting="legacy"`.
`TradingOperator.initialize` accepts the same trailing option. Existing
positional arguments retain their meaning. Reinitializing an already initialized
strategy remains a no-op and cannot switch its accounting mode.

The operator preserves the old strategy initialization call when the mode is
omitted or `legacy`, so custom strategies with old initialization signatures
continue to work in that mode. Fractional mode passes the new keyword explicitly;
an incompatible custom strategy fails rather than silently downgrading. Direct
fractional operator assembly also requires a `SimulationTrader` and validates
the mode and Trader before assigning its components. An already initialized
built-in strategy must have the same accounting mode as the requested operator
mode; a conflict is rejected without resetting its budget or balances. An already
initialized custom `Strategy` without a stored accounting mode remains supported
in legacy mode but is rejected for fractional mode, because its no-op initializer
cannot confirm the opt-in.

## Deliberately unchanged

- Live Traders, live balances, exchange API behavior, and live fee handling.
  OKX has a separate cash ledger; this option does not establish live OKX parity.
- Strategy minimum-order thresholds: BNH/SMA/LLM initialization defaults remain
  5000 and RSI remains 100. This feature does not make a 300-USDT session
  operational across strategies.
- Order sizing, including BNH request-notional rounding and SMA budget rounding.
- Existing four-decimal order-quantity flooring and six-decimal holdings rules;
  exchange-specific tick, lot, and minimum-notional validation is not activated.
- LLM balance display precision and other reporting/presentation rules.
- `SafetyGuard` defaults and profile safety limits. Binance/OKX amounts are in
  USDT; the existing KRW-oriented monetary defaults still require explicit
  USDT-appropriate limits.
- Callback lifecycle, result history, waiting-request behavior, and existing
  duplicate-callback or concurrency concerns.

See the [exchange guide](exchanges-and-trading-ko.md) for virtual-trading and
currency limitations, and the [user guide](public/user-guide.md) for profile
setup.
