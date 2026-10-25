# Binance / OKX local USDT cash accounting

BinanceTrader and OkxTrader preserve fractional USDT when settling a completed
buy or sell into their local balance. Buy settlement subtracts notional plus
the configured commission; sell settlement adds notional minus that commission.
The previous whole-unit rounding is not appropriate for USDT amounts.

For example, with 100 USDT, a 10.25 USDT buy and commission_ratio=0.001,
the local balance becomes 89.73975 rather than 90. A same-price round trip
costs both configured fees. This remains float-based local bookkeeping, not an
exact exchange ledger or a guarantee of exchange-account reconciliation.

Buy admission also requires the quoted notional plus the same configured
commission to fit the local balance. Thus a 99.95 USDT buy with a 0.1%
commission is rejected against 100 USDT before dispatch. This is an affordability
check, not an order resizing or concurrent-order reservation policy. The OKX
opt-in limit preflight retains exact rational comparisons.

The change does not alter order payloads, quantity rounding, lifecycle
ownership, callback ordering, commission rates, actual fee-asset handling,
KRW adapters, or strategy cash accounting. The PAPER-only
cash_accounting=fractional setting has not been enabled for live profiles.
Live strategy accounting therefore remains a separate limitation.

The BNH default minimum of 5000 and its quantity sizing are also unchanged.
In particular, this cash correction does not make small-budget USDT BNH
sessions ready: exchange-specific order rules need a separately specified
policy. Existing OKX metadata/preflight defaults remain off.

Offline regression tests use constructor-free traders and synthetic terminal
results, without credentials, HTTP or real orders. Run:

    python -m pytest tests/unit_tests/usdt_cash_accounting_test.py -q
    python -m pytest tests/unit_tests -q

Exchange-reported commission currency, discounts, real account balances,
long-running float drift, and production execution are not established by
these tests. No deployment or real-money test is required for this change.
