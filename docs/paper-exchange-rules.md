# Opt-in public exchange rules for PAPER BNH

This is a **PAPER-only, default-OFF** static minimum-order/size validation path.
It does not activate live trading, change OKX live preflight defaults, or change
legacy PAPER profiles. Legacy BNH still has its historical KRW minimum and sizing.

Enable explicitly in a saved profile (or `SessionManager.create_session`):

```json
{"name":"paper-btc-rules","exchange":"BNC","currency":"BTC","budget":100,
 "virtual":true,"strategy":"BNH","cash_accounting":"fractional",
 "paper_exchange_rules":true}
```

`OKX` is the other public metadata provider. `virtual: true`, fractional cash
accounting and BNH are mandatory. Other strategies and order types require their
own sizing/market-applicability work and are rejected, not silently approximated.
Existing live paths and generic `SimulationTrader` remain unchanged.

## Verified scope

- Binance (`BNC`): public `GET /api/v3/exchangeInfo?symbol=BTCUSDT`; require matching
  base/quote/symbol, TRADING, spot allowed and LIMIT supported. Apply LOT_SIZE
  min/max/step, PRICE_FILTER tick and nonzero bounds, MIN_NOTIONAL and/or NOTIONAL
  (both minima must hold, and NOTIONAL maximum applies).
- OKX: public `GET /api/v5/public/instruments?instType=SPOT&instId=BTC-USDT`;
  require live matching USDT SPOT. minSz and lotSz are **base quantities**, tickSz
  is price increment. There is no invented fixed quote minimum. Pending instrument
  changes (`upcChg`) fail closed until this implementation supports effective dates.
- Upbit (`UPB`) and Bithumb (`BTH`): public market/ticker/price-increment endpoints
  are not sufficient minimum-order metadata. The orders/chance endpoints require
  authentication. Strict PAPER blocks with an explicit unavailable reason and
  never accesses them; it does not substitute a guessed 5,000 KRW rule.

BNH budgets one fifth per request and floors price/quantity to the supported grid,
never increasing an undersized order to meet a minimum. Decimal text is evaluated
with exact rational arithmetic, then checked again at the simulator float boundary.
A failed rule produces no strategy order, with `strategy.blocked_reason`; direct
invalid submissions return `state=failed` and `PAPER rules blocked: ...`.

Metadata is fetched at construction and refreshed at each trading tick when the
60-second monotonic request-start window expires. Fetches are public GETs with a
five-second timeout and redirects disabled. Errors clear cached rules; there is no
stale fallback. Submission and pending fills recheck freshness and bounds without
network calls under the admission lock. Cancels remain available. Pending fills
that become invalid fail without changing balances and release their reservations.

## Limits, not an exchange emulator

Only **limit** orders are supported in this strict path. Market orders have separate
market-lot/notional-average-price applicability; stop/take-profit rules are likewise
not inferred. Static checks do not reproduce percent-price bands, account-specific
limits, queue priority, liquidity, partial fills, maker/taker fees or real approval.
The existing PAPER no-fee convention remains (fee=0); no live fee settings change.
The strict simulator preserves sub-micro quantities instead of rounding assets to
six decimals, but float accounting remains an approximation, not exchange accounting.
A candle quote is not an executable order book. Off-grid/too-small simulated fills
fail conservatively. Minimum constraints based on today's metadata are not historical
exchange rules, so a historical replay is a software regression, not profitability
or historical execution-fidelity evidence.

## Verification

Run focused tests then the suite without private credentials:

```sh
PYTHON_DOTENV_DISABLED=1 python -m pytest tests/unit_tests/test_paper_exchange_rules.py -q
PYTHON_DOTENV_DISABLED=1 python -m pytest tests/unit_tests tests/e2e_tests -q
```

Unit metadata fixtures are synthetic documented shapes, not claims about current Binance values.
The separately preserved OKX public replay is identified below.
Tests require nonzero successful fills for BNC/OKX at 100 and 1,000 USDT, check
quantity/notional/tick boundaries, missing/malformed/expired metadata and unavailable
Korean-exchange rules. Live transport, real orders and LLM calls are not test needs.

## Official sources

- https://developers.binance.com/en/docs/catalog/core-trading-spot-trading/api/rest-api/general
- https://developers.binance.com/en/docs/products/spot/filters
- https://www.okx.com/docs-v5/en/
- https://docs.upbit.com/kr/reference/list-orderbook-instruments
- https://docs.upbit.com/kr/reference/available-order-information
- https://apidocs.bithumb.com/reference/주문-가능-정보

## 검증 자료 (2026-10-25)

`tests/fixtures/paper_rules`는 이번에 새로 공개 GET으로 확보한 OKX BTC-USDT
메타데이터와 1분 캔들입니다. 오전 실행 자료를 복구한 것이 아닙니다.
확정 캔들 199개(10:12–13:30 UTC)만 오름차순으로 재생하면 100/1000 USDT
각각 5건이 체결됩니다. 잔돈은 최소 수량 미달로 추가 주문이 차단됩니다.
미확정 캔들 1개는 제외합니다. `replay-result.json`에 원본 SHA-256 및 결과를
기록했습니다. 고정 메타데이터/시계를 사용하는 오프라인 재생이므로 당시의
거래소 규칙 이력이나 실시간 지연·슬리피지 검증은 아닙니다.
Binance 공개 API는 이 실행 환경에서 HTTP 451을 반환하여 현재 규칙 검증은
하지 못했습니다. Binance 성공 경로는 명시적 합성 fixture 검증입니다.
Upbit/Bithumb는 공개 API만으로 필수 최소 규칙을 확인할 수 없어 차단됩니다.

자원 비교는 strict PAPER 경로에서 legacy epsilon을 사용하지 않습니다.
유효한 작은 lot을 잔고 없이 체결하거나 잔량을 삭제하지 않으며, float 경계에서
자원이 조금이라도 부족하면 차단합니다. 원장 자체는 기존 float 방식입니다.
