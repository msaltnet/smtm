# 다양한 주문 유형 지원 + BinanceTrader 설계

- 작성일: 2026-07-14
- 상태: **초안 (사용자 리뷰 대기)**
- 관련 파일: `smtm/trader/*`, `smtm/strategy/*`, `smtm/llm/safety_guard.py`, `smtm/trading_operator.py`, `smtm/analyzer.py`

> ⚠️ 이 문서는 사용자가 자리를 비운 동안 "최선의 판단"으로 작성한 초안입니다.
> 뒤쪽 **8. 확정 필요한 결정** 섹션의 가정들을 먼저 확인해 주세요.

---

## 1. 배경 (현재 상태)

smtm은 채팅 기반 AI Agent가 세션을 오케스트레이션하고, 각 세션의 `TradingOperator`가
고정 주기 루프(`DataProvider → Strategy → SafetyGuard → Trader → Analyzer`)로 매매를 수행한다.

주문 요청은 파이프라인 전 구간이 공유하는 단일 계약을 따른다:

```python
{
    "id": "1607862457.560075",
    "type": "buy" | "sell" | "cancel",
    "price": 거래 가격,
    "amount": 거래 수량,
    "date_time": 요청 시간,
}
```

현재 한계:

- `type`은 `buy`/`sell`/`cancel` 세 가지뿐 — 조건부 주문 개념이 없음.
- Upbit/Bithumb은 실질적으로 **지정가(limit)** 만 사용. 시장가 코드는 있으나
  `upbit_trader._execute_order`에서 `price == 0`이면 `"market price is not supported now"`로 막아둠.
- Binance(`BNC`)는 **데이터 제공자만 존재하고 주문 실행 Trader가 없음**.

### 중요한 하위호환 함정 (설계 제약의 근거)

- **`price == 0`은 이미 "거래 없음(hold) 신호"로 사용 중**이다.
  (`strategy_rsi`가 시뮬레이션에서 `{type:buy, price:0, amount:0}`을 no-op으로 반환,
  `strategy_llm._decision_to_request`도 `price > 0`을 요구.)
  → **시장가를 `price == 0`으로 표현하면 기존 동작과 충돌**. 신규 유형은 별도 필드로 구분해야 한다.
- `BaseExchangeTrader._create_success_result`가 `request["price"]`, `request["amount"]`를
  직접 참조 → 이 두 키는 반드시 유지되어야 한다(additive 확장이라 문제없음).
- `SafetyGuard.check_request`는 `cancel`이 아닌 모든 요청을 `price * amount`로 한도 검사한다
  → 조건부 주문의 금액 계산 규칙을 명시해야 한다.

---

## 2. 목표 / 비목표

### 목표

1. 거래소가 제공하는 **다양한 주문 유형**(시장가, 지정가, 손절, 익절, OCO)을 파이프라인이 표현·처리.
2. Binance 현물(spot) **주문 실행 Trader 신규 구현** — Binance 네이티브 주문 유형 활용.
3. 리스크 관리 자동화(손절/익절)를 **세션 정책**으로 제공.
4. **기존 인터페이스 하위호환 유지** — 시그니처·기존 요청 스키마를 깨지 않고 additive 확장만.

### 비목표 (이번 범위 밖)

- Binance **선물(futures)** — 레버리지/청산/마진 개념이 기존 현물 가정과 충돌 → 별도 과제.
- 트레일링 스탑 — OCO 이후 후속 과제로 남김.
- 전략 알고리즘(RSI/SMA/BnH)이 손절가를 자체 계산하도록 수정 — Phase 2 이후 선택.

---

## 3. 하위호환 원칙 (최우선)

| 대상 | 원칙 |
|------|------|
| 인터페이스 시그니처 | `Trader.send_request`, `Strategy.get_request`, `SafetyGuard.check_request` **전부 불변** |
| 요청 스키마 | 기존 5개 키 유지. 신규는 **모두 선택 필드**, 없으면 오늘과 100% 동일 동작 |
| 기존 거래소 | Upbit/Bithumb 기존 동작 불변. 새 주문 유형은 "역량 선언"으로 opt-in |
| 신규 컴포넌트 | 설정이 없으면 비활성 — 기존 세션 동작에 영향 없음 |

---

## 4. 설계 개요

두 개의 산출물로 구성된다:

1. **주문 유형 파이프라인** — 거래소 무관한 공통 기반 (스키마 + 역량 모델 + SafetyGuard + 시뮬레이터).
2. **BinanceTrader** — Binance 현물 주문 실행 Trader.

핵심 아이디어: **거래소 역량 모델(Capability Model)**.
각 Trader가 자신이 지원하는 주문 유형을 선언하고, 조건부 주문의 "감시 주체"는 거래소 역량에 따라 갈린다.

| 거래소 | 조건부 주문(손절/익절/OCO) 처리 방식 |
|--------|--------------------------------------|
| **Binance (신규)** | **트리거 감시만** 거래소에 위임(로컬 감시 루프 불필요). 주문 등록·추적·체결확인·취소·정합성은 smtm이 관리 |
| **Simulation** | **로컬 에뮬레이션** — 대기 조건 보관 후 매 틱 시세로 검사·발동 (가상거래 검증용) |
| **Upbit/Bithumb** | 시장가/지정가만 추가. 조건부는 "미지원" 선언 (후속에 로컬 감시 추가 가능) |

> **"던지고 잊기" 아님**: 거래소에 위임하는 것은 *트리거 조건 감시*(가격 도달 여부)뿐이다.
> 제출한 예약 주문의 **수명주기 관리(추적·체결 확인·취소·정합성)는 smtm이 그대로 수행**한다.

---

## 5. 상세 설계

### 5.1 요청 스키마 확장 (additive)

```python
{
    # ── 기존 (불변) ──
    "id": ...,
    "type": "buy" | "sell" | "cancel",
    "price": ...,        # 지정가. 시장가/조건부에서 의미는 ord_type에 따름
    "amount": ...,
    "date_time": ...,

    # ── 신규 (모두 선택, 없으면 기존 동작) ──
    "ord_type": "limit",  # "limit"(기본) | "market" | "stop_loss" | "take_profit" | "oco"
    "trigger": 48000000,  # stop_loss / take_profit 발동 기준가 (절대값)
    "oco": {              # ord_type == "oco" 일 때만
        "take_profit_price": 55000000,  # 익절 지정가(LIMIT_MAKER)
        "stop_trigger": 48000000,       # 손절 발동가(STOP)
        "stop_limit_price": 47900000,   # 손절 지정가 (없으면 시장가 손절)
    },
}
```

- `ord_type` 부재 ⇒ `"limit"` ⇒ 오늘과 동일.
- `type`은 여전히 매수/매도/취소 **방향**을 의미. `ord_type`이 **실행 방식**을 의미.
  (예: 손절 매도 = `type:"sell", ord_type:"stop_loss", trigger:...`)

### 5.2 거래소 역량 모델

각 Trader에 클래스 속성 추가:

```python
class Trader:
    SUPPORTED_ORD_TYPES = {"limit"}  # 기본값(하위호환): 지정가만

class UpbitTrader:   SUPPORTED_ORD_TYPES = {"limit", "market"}
class BithumbTrader: SUPPORTED_ORD_TYPES = {"limit", "market"}
class BinanceTrader: SUPPORTED_ORD_TYPES = {"limit", "market", "stop_loss", "take_profit", "oco"}
class SimulationTrader: SUPPORTED_ORD_TYPES = {"limit", "market", "stop_loss", "take_profit", "oco"}  # 에뮬레이션
```

각 Trader의 실행 진입점에서:

```python
ord_type = request.get("ord_type", "limit")
if ord_type not in self.SUPPORTED_ORD_TYPES:
    # 오실행 대신 명확히 실패 처리 (callback error), 로그 경고
    return self._reject(request, callback, f"unsupported ord_type: {ord_type}")
```

→ 미지원 유형이 옛 거래소로 흘러가도 **오실행 없이 안전하게 거부**. 하위호환 안전장치.

**기존 UpbitTrader/BithumbTrader에 대한 정확한 변경 (전부 additive):**

- 공개 인터페이스(추상 `Trader` 메서드 시그니처)는 **변경 없음**
  — `send_request`/`cancel_request`/`cancel_all_requests`/`get_account_info`.
- 추가되는 것: (1) 클래스 속성 `SUPPORTED_ORD_TYPES`, (2) `_execute_order` 내부에서
  `ord_type == "market"`일 때만 시장가 분기.
- **신규 필드가 없는 기존 요청은 지정가 경로 그대로** 실행되고, `price == 0` no-op 신호도 보존.
  → 기존 동작 100% 동일, 새 기능은 새 필드 사용 시에만 활성화.

### 5.3 BinanceTrader (현물)

`BaseExchangeTrader`를 상속하되, 인증/엔드포인트가 Upbit과 다르므로 재정의:

- **인증**: HMAC SHA256 서명 (`timestamp` + query → `signature`), 헤더 `X-MBX-APIKEY`.
  (Upbit의 JWT와 다름 — `_create_jwt_token` 재사용 불가, 별도 서명 메서드 필요.)
- **엔드포인트**: `POST /api/v3/order`, `POST /api/v3/orderList/oco`(또는 신규 OCO 엔드포인트),
  `GET /api/v3/account`, `DELETE /api/v3/order`, `GET /api/v3/ticker/price`.
- **마켓/통화 매핑**: Upbit `KRW-BTC` → Binance `BTCUSDT`. 예산·`min_price`가 **USDT 기준**.
  → `AVAILABLE_CURRENCY = {"BTC": ("BTCUSDT","BTC"), "ETH": ("ETHUSDT","ETH"), ...}`
- **주문 유형 매핑**:

  | smtm `ord_type` | Binance `type` |
  |-----------------|----------------|
  | `limit` | `LIMIT` |
  | `market` | `MARKET` |
  | `stop_loss` | `STOP_LOSS` / `STOP_LOSS_LIMIT` |
  | `take_profit` | `TAKE_PROFIT` / `TAKE_PROFIT_LIMIT` |
  | `oco` | OCO order list (LIMIT_MAKER + STOP_LOSS_LIMIT) |

- **주문 수명주기 관리** (트리거 감시만 거래소에 위임, 나머지는 smtm이 관리):
  - 제출한 주문/OCO를 `order_map`에 `orderId`/`clientOrderId`로 추적.
  - 기존 `_update_order_result` 폴링 패턴으로 체결 감지 → 콜백 → 잔고·자산 반영.
  - `cancel_request`/`cancel_all_requests`로 대기 중 예약 주문 취소.
  - OCO 정합성: 한 다리 체결 시 나머지는 Binance가 자동 취소 → 그 상태를 폴링으로 반영.

### 5.4 SimulationTrader — 시장가 + 조건부 에뮬레이션

- **시장가/지정가**: 시뮬레이터는 이미 요청 가격을 무시하고 `quotes[currency]`로 체결 →
  `market`은 그대로 동작. `limit`도 현재는 즉시 체결(단순화 유지).
- **조건부 에뮬레이션**: 대기 조건 목록(`pending_conditionals`)을 보관.
  `update_quote()`가 호출될 때마다 각 조건의 `trigger`/`op`를 검사, 돌파 시 즉시 매도 체결 후 콜백.
- OCO는 두 다리 중 하나가 발동하면 나머지 취소(로컬).

### 5.5 SafetyGuard 변경 (additive)

- `check_request`: 조건부 주문(`ord_type in {stop_loss, take_profit, oco}`)의 "거래 금액"은
  `trigger * amount`(또는 OCO는 손절가 기준)로 계산해 `max_trade_amount` 한도에 반영.
- `cancel`은 기존대로 검사 제외.
- 시그니처·기존 buy/sell 검사 로직 불변.

### 5.6 생성 주체 — 세션 손절/익절 정책 (producer)

프로파일에 선택적 정책 설정 추가:

```python
"stop_policy": {
    "stop_loss_ratio": -0.05,    # 평균단가 대비 -5% → 매도
    "take_profit_ratio": 0.10,   # 평균단가 대비 +10% → 매도
    "mode": "oco",               # "oco"(Binance 권장) | "separate"
    "exit_ord_type": "market",
}
```

- 부재 ⇒ 기능 off ⇒ 기존 세션 동작 불변.
- **동작**: 매수 체결 후, 정책이 평균단가 기준으로 `trigger` 가격을 계산해 조건부 주문을 생성.
  - Binance: OCO 예약 주문 1건 제출.
  - Simulation/Upbit(에뮬레이션): `ConditionalOrderManager`에 조건 등록, 매 틱 검사.
- **SafetyGuard의 `max_loss_ratio`와 구분**: `max_loss_ratio`는 누적 손실 시 *거래 차단*(수동적).
  `stop_policy`는 포지션을 *능동적으로 청산*. 문서/README에 차이 명시.
- 전략/LLM이 거래별로 직접 손절가를 지정하는 방식은 **Phase 3 이후 선택** (스키마는 이미 지원).

### 5.7 ConditionalOrderManager (로컬 감시 — 비네이티브 거래소용)

- `TradingOperator` 루프에서 시세 업데이트 직후 조건 검사:
  `DataProvider → (조건 검사) → Strategy → SafetyGuard → Trader → Analyzer`
- 발동된 주문도 **동일 경로**(SafetyGuard→Trader→Analyzer)로 전송 — 별도 실행 경로 없음.
- 트리거 기준가: MVP는 `primary_candle` **종가**. (고가/저가 기반은 후속 개선.)
- 한계 명시: 감시 지연 = 폴링 주기, 프로세스 종료 시 감시 중단(로컬 감시의 본질적 제약).

---

## 6. 하위 프로젝트 분해 (각각 spec → plan → 구현)

범위가 크므로 독립 검증 가능한 3단계로 분해한다.

- **① 기반 (Binance 불필요, 가상거래로 완결 검증)**
  요청 스키마 확장 + 역량 모델 + SafetyGuard 확장 + SimulationTrader 시장가/조건부 에뮬레이션
  + Upbit/Bithumb 시장가 활성화(Phase 0).

- **② BinanceTrader 코어**
  HMAC 인증 + 계좌 조회 + 시장가/지정가 주문 + `TraderFactory` 등록 + USDT 마켓/통화 매핑.

- **③ 고급 주문 + 생성 주체**
  Binance 네이티브 stop/take-profit/OCO 매핑 + 세션 `stop_policy` producer
  + `ConditionalOrderManager`(에뮬레이션 거래소용).

의존: ② → ③. ①은 독립. 각 하위 프로젝트는 자체 구현 계획을 별도로 작성.

---

## 7. 테스트 전략

- **단위**: 스키마 파싱, 역량 모델 거부 로직, SafetyGuard 조건부 금액 계산, Binance 서명/매핑(mock).
- **E2E (가상거래)**: `SimulationTrader` 조건부 에뮬레이션으로 손절/익절 발동 시나리오 검증
  — 외부 API 없이 전체 파이프라인 통과.
- **통합 (선택, 키 필요)**: Binance testnet에 실제 주문/OCO 제출·취소.
- **회귀**: 신규 필드 없는 기존 요청이 기존 경로와 동일하게 동작함을 명시적으로 assert.

---

## 8. 확정 필요한 결정 (초안 가정)

| # | 항목 | 초안 가정 | 대안 |
|---|------|-----------|------|
| 1 | Binance 시장 | **현물(spot)** | 선물(futures) |
| 2 | Binance 예산 통화 | **USDT** | (현물이면 USDT 고정) |
| 3 | 손절/익절 주체 | **세션 정책 우선** (전략/LLM 지정은 후속) | 처음부터 전략/LLM 지정 |
| 4 | 트리거 기준가 | **캔들 종가** | 캔들 고가/저가 |
| 5 | 청산 방식 | **전량 매도** | 부분 청산 |
| 6 | 지원 통화 | 기존과 동일(BTC/ETH/DOGE/XRP) USDT 페어 | 확장 |

---

## 9. 리스크 & 한계

- **로컬 감시의 지연/중단**: Simulation/Upbit 에뮬레이션은 폴링 주기만큼 지연되고 프로세스 종료 시 멈춤.
  Binance 네이티브는 이 문제가 없음(거래소가 감시).
- **Binance 현물 KRW 불가**: USDT 기준 예산 → 기존 KRW 전제 코드와의 경계를 Trader 내부로 캡슐화.
- **인증 방식 차이**: Binance HMAC은 Upbit JWT와 달라 서명 로직을 공유하지 못함.
- **OCO 세부 규칙**: Binance OCO는 가격 관계 제약(예: LIMIT_MAKER > 현재가 > STOP)이 있어
  정책 계산 시 검증 필요.

---

## 10. ②③ 착수 전 반드시 반영할 통합 이슈 (① 최종 리뷰에서 발견)

하위 프로젝트 ①(기반)은 완결·병합되었으나, 조건부/시장가 주문을 **파이프라인으로 실제
생성하는 producer가 아직 없어** 아래 이슈들은 ①에서는 비활성(dormant)이다. ②③에서
producer(세션 정책/LLM, BinanceTrader)를 붙이기 전에 반드시 설계에 반영해야 한다.

1. **전략의 cancel-and-replace가 무장된 조건부 주문을 자동 취소한다 (최우선).**
   조건부 주문 등록 시 콜백이 `state:"requested"`로 오고, `StrategyLlm`/`StrategyRsi`의
   `update_result`가 그 id를 `waiting_requests`에 저장한다. 다음 틱에 `get_request`가
   `waiting_requests`의 **모든** id에 대해 `cancel`을 발행 → 방금 건 손절/익절이 발동 전에
   취소된다. **대응**: "무장된 조건부"와 "체결 대기 중인 지정가(교체 대상)"를 구분해야 함
   — 조건부는 `waiting_requests`에 넣지 않거나, 자동 취소 루프에서 조건부 id를 제외.

2. **시장가 매수 의미가 거래소마다 다르다.** 동일한 `{type:buy, ord_type:market, price, amount}`에
   대해 Upbit은 `price*amount` KRW를 지출(amount가 KRW 총액 승수), Bithumb/Simulation은
   `amount` **코인 수량**을 매수한다. `price ≈ 현재가`일 때만 일치. **대응**: 시장가 매수
   계약(`price`/`amount`의 의미)을 확정·문서화하거나 Upbit을 코인 수량 기준으로 정규화.

3. **SafetyGuard가 `market`/`oco` 금액을 제한하지 못한다.** `market`은 `price==0`이면 거래금액이
   0으로 계산되어 `max_trade_amount`를 통과하고, `oco`는 trigger 기반 추정이 아닌 `price*amount`
   분기로 빠진다(스펙 §5.5가 요구하는 것과 다름). ②③에서 producer와 함께 보완.

4. **조건부 발동 시점에는 SafetyGuard 재검증이 없다** (등록 시점에만 한도 검사). 리스크 축소형
   손절/익절에는 합리적이나, ②③에서 정책 설계 시 명시적으로 고려.

5. **Binance 주문 수량/가격의 심볼 필터 정밀 라운딩** (②에서 발견). ②의 `BinanceTrader._format_number`가
   지수표기를 막고 소수 8자리로 반올림하지만, 심볼별 `LOT_SIZE`(stepSize)·`PRICE_FILTER`(tickSize)·
   `MIN_NOTIONAL` 준수는 `exchangeInfo` 조회가 필요하다. ③에서 producer가 실제 주문 수량/가격을 만들 때
   심볼 필터 기반 라운딩을 적용해야 실주문 거부(-1111 등)를 방지한다.

6. **금액 기반 안전장치의 통화 기본값** (②에서 발견). `SafetyConfig` 기본값(`max_trade_amount=100000`,
   `initial_budget`)은 KRW 전제다. Binance(USDT) 세션은 프로파일 `safety`에서 USDT 기준 값을 지정해야 하며,
   ③에서 거래소별 통화 인지형 기본값을 도입하는 것이 바람직하다. (②에서는 README 경고로 대응.)
