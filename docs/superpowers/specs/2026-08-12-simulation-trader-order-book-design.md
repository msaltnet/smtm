# SimulationTrader 가상 주문장 및 JptController 제거 설계

- 작성일: 2026-08-12
- 상태: **승인됨**
- 관련 파일: `smtm/trader/simulation_trader.py`, `smtm/trading_operator.py`,
  `smtm/strategy/strategy.py`, `smtm/strategy/strategy_bnh.py`,
  `smtm/strategy/strategy_rsi.py`, `smtm/strategy/strategy_sma.py`,
  `smtm/strategy/strategy_llm.py`, `smtm/controller/jpt_controller.py`,
  `smtm/__init__.py`, README 및 공개 문서
- 선행 스펙: [Paper Trading Mode](2026-04-26-paper-trading-design.md),
  [주문 유형 + BinanceTrader](2026-07-14-order-types-and-binance-trader-design.md)

---

## 1. 배경

`virtual: true`인 세션은 프로파일의 `exchange` 값과 무관하게
`TraderFactory.create(..., paper=True)`를 통해 `SimulationTrader`를 사용한다. `exchange`는
실시간 시세를 가져올 `DataProvider`를 고르는 데만 사용된다. 따라서 `SimulationTrader`는 특정
거래소를 복제하는 클래스가 아니라 모든 데이터 소스와 결합할 수 있는 하나의 인메모리 가상
거래소다.

현재 가상 시장가 주문은 최신 `primary_candle` 종가로 즉시 체결되지만 다음 결함이 있다.

1. 지정가 주문도 주문 가격을 무시하고 현재가로 즉시 체결한다.
2. 손절·익절은 별도의 `pending_conditionals`에 저장되지만 현금·자산을 예약하지 않는다.
3. `cancel_all_requests()`가 no-op이어서 세션을 중지한 뒤에도 남은 조건 주문이 체결될 수 있다.
4. 대기 주문과 사용 가능 잔고를 계좌 조회에서 확인할 수 없다.
5. `SimulationTrader`는 수수료 0을 적용하지만 전략은 체결 결과를 받아 0.05%를 별도로 차감하여
   전략 내부 잔고와 가상계좌 잔고가 달라진다.
6. 프로그램/Jupyter용 `JptController`는 `virtual: False`로 고정되어 있으며 현재의 텔레그램 중심
   실행 모델과 안전한 가상거래 기본값에 맞지 않는다.

## 2. 목표

1. `SimulationTrader` 내부에 전략과 독립적인 가상 주문장을 구현한다.
2. 시장가, 지정가, 매도 손절, 매도 익절의 등록·예약·체결·취소를 일관되게 처리한다.
3. 지정가가 제출 시점에 체결 가능하면 지정가보다 유리한 현재가로 즉시 체결한다.
4. 대기 주문이 같은 현금이나 자산을 중복 사용하지 못하도록 예약 상태를 관리한다.
5. `TradingOperator.stop()`이 모든 가상 대기 주문을 실제로 취소하게 한다.
6. 가상계좌와 전략 내부 회계가 체결 결과의 실제 수수료를 기준으로 일치하게 한다.
7. `JptController` 코드·export·사용자 문서·관련 테스트를 제거한다.
8. 실제 Trader와 가상 Trader의 주문 유형 지원 차이 및 가상 체결의 한계를 README에 명확히
   기록한다.

## 3. 비목표

- Upbit, Bithumb, Binance, OKX 실제 Trader의 주문 구현 변경
- 실제 거래소 네이티브 손절·익절 주문
- OCO(한 주문 체결 시 상대 주문 자동 취소)
- 트레일링 스톱(최고가 또는 최저가를 따라 움직이는 동적 트리거)
- 전략이 자동으로 손절·익절 주문을 생성하는 정책 또는 프로파일 옵션
- 부분 체결, 호가창, 슬리피지, 거래량 기반 체결
- 거래소별 수수료, 최소 주문 금액, 호가 단위, 수량 정밀도 재현
- 대기 주문과 가상계좌의 디스크 영속화
- `notebook/` 아래의 거래소별 실험 노트북 제거

## 4. 검토한 구조와 결정

### A. `SimulationTrader` 내부 주문장 — 선택

`SimulationTrader`를 하나의 가상 거래소로 보고 시장가·지정가·조건부 주문의 전체 수명 주기를
클래스 내부에서 처리한다. 가상거래에만 필요한 동작이 한 경계 안에 모이고 실제 Trader의 안전한
주문 경로를 건드리지 않는다.

### B. 별도 공통 조건 주문 관리자 — 보류

Trader 위에 공통 관리자를 두면 실거래에도 같은 조건 로직을 적용할 수 있지만, SMTM 프로세스가
중지되면 실거래 보호 주문도 사라진다. 현재 요구사항은 가상거래 완성도이므로 별도 계층과 실거래
위험을 추가할 이유가 없다.

### C. 거래소별 네이티브 조건 주문 — 범위 밖

실거래 안전성은 가장 높지만 거래소별 API·주문 상태·취소 의미가 달라 각각 별도 설계와 검증이
필요하다. 이번 작업에서는 실제 Trader가 손절·익절을 지원하지 않는다는 사실만 문서화한다.

## 5. 구성과 책임

```text
Strategy
   │ 표준 주문 요청
   ▼
TradingOperator ── SafetyGuard
   │ 허용된 주문
   ▼
SimulationTrader
   ├─ quotes: 종목별 최신 시세
   ├─ balance/assets: 총 현금·총 자산
   ├─ pending_orders: 예약을 포함한 대기 주문장
   └─ order_history: 완료·실패·취소된 최종 결과
```

- **Strategy**: 매수/매도, 가격, 수량, 주문 유형과 트리거를 요청으로 표현한다. 체결 가능 여부나
  대기 주문 상태를 판단하지 않는다.
- **TradingOperator**: 시장 데이터를 전달하고 최신 `primary_candle` 종가를
  `SimulationTrader.update_quote()`에 주입한다. 실제 체결만 거래 횟수로 기록한다.
- **SimulationTrader**: 검증, 자원 예약, 주문 등록, 시세 조건 평가, 체결, 취소, 계좌 상태의 단일
  진실 공급원이다.

별도 주문장 모듈은 만들지 않는다. `pending_conditionals`는 모든 대기 주문을 다루는
`pending_orders`로 대체한다. Python dict의 삽입 순서를 사용해 주문 등록 순서를 보존하며, 키는
요청의 `id`다. 각 항목은 외부에 노출하지 않는 다음 상태를 가진다.

```python
pending_orders[request_id] = {
    "request": request_copy,
    "callback": callback,
    "reserved_balance": 0.0,
    "reserved_asset": 0.0,
}
```

## 6. 주문 계약

기존 요청 스키마를 유지한다.

```python
{
    "id": "unique-id",
    "type": "buy" | "sell" | "cancel",
    "ord_type": "market" | "limit" | "stop_loss" | "take_profit",
    "price": 50000,
    "amount": 0.1,
    "trigger": 45000,
    "currency": "BTC",
    "date_time": "2026-08-12T12:00:00",
}
```

- `ord_type`이 없거나 falsy이면 기존 규약대로 `limit`다.
- `currency`가 없으면 Trader 생성 시 받은 기본 통화를 사용한다.
- `price`는 지정가 주문에서 필수다. 시장가에서는 체결가로 사용하지 않는다.
- `trigger`는 손절·익절에서 필수다.
- 손절·익절은 현물 보유 자산을 청산하는 **매도 주문만** 지원한다.
- `oco` 및 알 수 없는 주문 유형은 `failed` 결과로 거부한다.
- 트레일링 스톱은 주문 상수와 스키마 자체를 추가하지 않는다.

모든 주문은 다음 공통 검증을 통과해야 한다.

- 비어 있지 않은 고유 `id`
- `buy` 또는 `sell` 주문의 유한한 양수 `amount`
- 지정가 주문의 유한한 양수 `price`
- 손절·익절 주문의 유한한 양수 `trigger`
- 동일한 ID가 대기 주문장에 없어야 함
- 예약분을 제외한 현금 또는 자산이 충분해야 함

NaN과 양·음의 무한대는 양수 비교를 통과시키지 않고 명시적으로 거부한다. 검증 실패는 예외를
외부로 던지지 않고 `state="failed"`, `price=0`, `amount=0`인 콜백 결과로 반환한다.

실패 사유는 테스트와 사용자 메시지가 흔들리지 않도록 다음 문자열로 고정한다.

| 상황 | `msg` |
|---|---|
| ID 누락·빈 값 | `잘못된 주문 ID` |
| 이미 대기 중인 ID | `중복 주문 ID` |
| 미지원 `ord_type` | `지원하지 않는 주문 유형: <ord_type>` |
| 미지원 `type` | `지원하지 않는 매매 유형: <type>` |
| 잘못된 수량 | `잘못된 수량` |
| 잘못된 지정가 | `잘못된 가격` |
| 잘못된 조건 가격 | `잘못된 트리거` |
| 매수형 손절·익절 | `매도 조건 주문만 지원` |
| 사용 가능 현금 부족 | `잔고 부족` |
| 사용 가능 자산 부족 | `보유 수량 부족` |
| 시장가 주문의 시세 누락 | `시세 없음` |

## 7. 체결 규칙

### 7.1 시장가

- 최신 시세가 있으면 현재가로 전량 즉시 체결한다.
- 시세가 없으면 `failed: 시세 없음`으로 종료한다.
- 매수는 예약되지 않은 현금, 매도는 예약되지 않은 자산만 사용할 수 있다.

### 7.2 지정가

| 주문 | 체결 조건 | 체결 가격 |
|---|---|---|
| 매수 | `현재가 <= 지정가` | 현재가 |
| 매도 | `현재가 >= 지정가` | 현재가 |

주문 제출 시 최신 시세가 이미 조건을 만족하면 현재가로 즉시 체결한다. 이는 사용자가 지정한
한도보다 유리한 가격을 받는 가격 개선이다. 조건을 만족하지 않거나 아직 시세가 없으면
`state="requested"` 콜백 후 주문장에 등록한다.

### 7.3 손절·익절

| 주문 | 체결 조건 | 체결 가격 |
|---|---|---|
| 매도 손절 | `현재가 <= trigger` | 현재가 |
| 매도 익절 | `현재가 >= trigger` | 현재가 |

주문 제출 시 최신 시세가 조건을 이미 만족하면 즉시 체결한다. 조건을 만족하지 않거나 시세가
없으면 주문장에 등록한다. 매수형 손절·익절은 `failed: 매도 조건 주문만 지원`으로 거부한다.

손절과 익절은 각각 자산을 예약하므로 같은 보유 수량 전체에 두 주문을 동시에 걸 수 없다. 두
주문이 같은 자산을 공유하고 하나의 체결이 다른 하나를 취소하게 하려면 OCO가 필요하며 이번
범위에서는 지원하지 않는다.

### 7.4 시세 갱신과 처리 순서

`update_quote(currency, price)`는 다음 순서로 동작한다.

1. 유한한 양수 시세인지 검증한다. 잘못된 시세면 계좌와 주문장을 변경하지 않는다.
2. `quotes[currency]`를 갱신한다.
3. 해당 통화의 대기 주문 ID를 등록 순서대로 스냅샷한다.
4. 아직 주문장에 남아 있고 새 시세가 조건을 만족하는 각 주문을 한 번씩 체결한다.
5. 콜백 중 다른 주문이 취소되더라도 스냅샷의 ID를 처리하기 전에 주문장 존재 여부를 다시
   검사한다.

한 캔들 틱에서는 하나의 종가만 알 수 있으므로 부분 체결 없이 전량 체결한다.

## 8. 자원 예약과 계좌 불변식

대기 주문은 등록 시 다음 자원을 예약한다.

- 지정가 매수: `지정가 × 수량`만큼 현금
- 지정가 매도: 매도 수량만큼 자산
- 매도 손절·익절: 매도 수량만큼 자산

총 현금과 총 자산은 실제 체결 전까지 차감하지 않는다. 사용 가능 값은 항상 다음 식으로
계산한다.

```text
available_balance = balance - sum(pending buy reserved_balance)
available_asset[currency] = total_asset[currency] - sum(pending sell reserved_asset)
```

지정가 매수가 더 낮은 현재가로 체결되면 총 현금에서는 `현재가 × 수량`만 차감하고
`(지정가 - 현재가) × 수량`의 남은 예약분은 즉시 해제한다. 매도 체결은 예약 수량을 실제 보유량에서
차감한다. 실패나 취소는 총 현금·총 자산을 바꾸지 않고 예약만 해제한다.

`get_account_info()`는 기존 키를 보존하고 예약 및 주문장 조회 키를 추가한다.

```python
{
    "balance": 500000.0,
    "available_balance": 400000.0,
    "reserved_balance": 100000.0,
    "asset": {"BTC": (50000.0, 1.0)},
    "available_asset": {"BTC": 0.4},
    "reserved_asset": {"BTC": 0.6},
    "quote": {"BTC": 50000.0},
    "open_orders": [
        {
            "request": {"id": "sell-1", "type": "sell", "amount": 0.6},
            "state": "requested",
            "reserved_balance": 0.0,
            "reserved_asset": 0.6,
        }
    ],
    "date_time": "2026-08-12T12:00:00",
}
```

반환값에는 콜백 객체를 포함하지 않으며 요청과 컬렉션을 복사해 호출자가 내부 주문장을 변경하지
못하게 한다.

## 9. 결과, 취소 및 이력

콜백 상태는 기존 `requested`/`done` 계약을 유지한다.

- 대기 등록: `state="requested"`, `msg="success"`
- 체결 완료: `state="done"`, `msg="success"`, 실제 `price`, `amount`, `fee`
- 검증·체결 실패: `state="failed"`, 실패 사유, `price=0`, `amount=0`, `fee=0`
- 취소 완료: `state="done"`, `msg="canceled"`, `price=0`, `amount=0`, `fee=0`

`cancel_request(id)`는 주문을 제거하고 예약을 반환한 뒤 그 주문이 보관한 원래 콜백에 취소 완료
결과를 전달한다. 존재하지 않는 ID는 no-op이다. `send_request()`로 전달된 `type="cancel"` 요청도
같은 메서드에 위임한다.

`cancel_all_requests()`는 현재 대기 ID를 등록 순서대로 스냅샷한 뒤 `cancel_request()`를 호출한다.
따라서 `TradingOperator.stop()`이 호출되면 지정가·손절·익절이 모두 제거되고 이후
`update_quote()`에서 발동하지 않는다.

`order_history`에는 체결, 실패, 취소처럼 종료된 결과만 등록한다. `requested` 중간 결과는
`open_orders`에서 조회하며 이력에 중복 저장하지 않는다.

`TradingOperator`는 `state="done"`, `msg="success"`, 양수 체결 수량인 매수·매도만
`SafetyGuard.record_trade()`에 전달한다. 취소는 일일 거래 횟수를 소비하지 않는다. 실패와 취소는
모니터링 결과에는 남는다.

## 10. 수수료와 전략 회계

`SimulationTrader`의 이번 정책은 기존 문서대로 수수료 0이다. 생성자에 전달된
`commission_ratio`는 적용하지 않고 `self.commission_ratio = 0`을 유지한다. 모든 체결 및 종료
결과에는 실제 적용된 `fee`를 포함한다.

BNH, RSI, SMA, LLM 전략은 체결 결과에 `fee`가 있으면 그 값을 사용한다. 실제 Trader의 기존
결과처럼 `fee`가 없으면 각 전략의 기존 `COMMISSION_RATIO` 계산으로 폴백하여 실제 Trader 코드를
이번 범위에서 변경하지 않는다. 공통 계산은 `Strategy` 기반 클래스의 작은 헬퍼로 모아 네 전략의
중복과 불일치를 방지한다.

이 변경은 전략이 주문 체결을 결정하게 만드는 것이 아니다. 전략이 자기 판단에 필요한 내부
잔고를 갱신할 때 가상 거래소가 보고한 실제 수수료를 신뢰하도록 만드는 회계 일치 작업이다.

## 11. JptController 제거

다음 런타임 표면을 제거한다.

- `smtm/controller/jpt_controller.py` 삭제
- `smtm/__init__.py`의 `JptController` import와 `__all__` 항목 삭제
- 패키지 export를 검증하는 테스트에서 `JptController` 기대값 제거 및 미노출 검증
- 루트 `jupyter_notebook.md` 삭제

현재 사용자 문서에서 `JptController`를 설명하는 다음 파일을 현재 텔레그램 단일 진입점 기준으로
정리한다.

- `docs/public/overview.md`
- `docs/public/user-guide.md`
- `docs/public/architecture.md`
- `docs/public/requirements.md`
- `docs/wiki/SMTM_프로젝트_소개.md`
- `docs/wiki/architecture.md`
- `docs/wiki/how-to-setup-and-run.md`
- `docs/smtm_class.puml`
- `docs/smtm_component.puml`
- `docs/TODO.md`

`notebook/` 디렉터리의 개별 모듈 실험 자료는 전체 시스템 Controller와 다른 용도이므로 유지한다.
과거 구현 의사결정을 기록한 `docs/superpowers/specs/`, `docs/superpowers/plans/`의 기존 문서는
역사 자료이므로 소급 수정하지 않는다. `docs/claw-branch-review.md`와 release notes도 특정 시점의
기록이므로 그대로 유지한다. `docs/smtm_class.png`는 현재 PlantUML 원본과 이미 불일치하는 생성
산출물이므로 삭제하고, 아키텍처 문서는 갱신된 `.puml` 원본을 기준으로 안내한다.

## 12. 문서화

`README.md`, `README-ko-kr.md`, `docs/exchanges-and-trading-ko.md`에 실제 지원 범위를 같은 표로
명시한다.

| 주문 유형 | 실제 Trader | `SimulationTrader` |
|---|---|---|
| 시장가 | Upbit/Bithumb/Binance/OKX 지원 | 지원, 현재가 즉시 체결 |
| 지정가 | Upbit/Bithumb/Binance/OKX 지원 | 지원, 조건 충족까지 대기 |
| 매도 손절 | 미지원 | 지원, 종가 기준 |
| 매도 익절 | 미지원 | 지원, 종가 기준 |
| OCO | 미지원 | 미지원 |
| 트레일링 스톱 | 미지원 | 미지원 |

가상 주문장 문서에는 다음 한계를 함께 기록한다.

- 상태는 메모리에만 존재하고 프로세스 재시작 시 잔고·대기 주문·이력이 사라진다.
- 조건은 `primary_candle` 최신 종가가 주입될 때만 평가된다.
- 60초 주기라면 봉 중간에 트리거에 닿았다가 복귀한 움직임을 놓칠 수 있다.
- 수수료는 0이며 슬리피지·부분 체결·호가 잔량·거래소별 최소 단위를 재현하지 않는다.
- 손절과 익절에 같은 자산을 동시에 예약하는 OCO 시나리오는 지원하지 않는다.
- 실제 Trader는 이번 변경의 수정 범위가 아니며 조건부 주문을 계속 명시적으로 거부한다.

## 13. 테스트 전략

### 13.1 `SimulationTrader` 단위 테스트

- 시장가 매수·매도 현재가 즉시 체결
- 시장가 시세 없음 실패
- 지정가 매수/매도의 즉시 체결 및 가격 개선
- 지정가 매수/매도의 대기, 시세 갱신 후 체결
- 시세 없는 지정가·손절·익절 등록 후 첫 시세 평가
- 매도 손절과 매도 익절의 경계값 발동
- 매수형 손절·익절, OCO, 알 수 없는 주문 유형 거부
- 중복 ID, 0/음수/NaN/무한대 가격·수량·트리거 거부
- 현금과 자산 예약, 중복 사용 차단, 가격 개선 잔여 예약 반환
- 동일 통화의 여러 주문이 등록 순서대로 결정적으로 처리됨
- 개별 취소·전체 취소의 예약 반환, 콜백, 이력, 이후 미발동
- `get_account_info()`가 내부 주문장과 콜백을 노출하지 않음
- 체결 결과 `fee=0` 및 전략/가상계좌 잔고 일치

### 13.2 `TradingOperator` 통합 테스트

- `primary_candle` 종가 주입이 대기 지정가·손절·익절을 체결함
- 전략 코드를 분기하지 않고 `Strategy.get_request()`의 표준 요청을 그대로 전달함
- `stop()`이 모든 대기 주문을 취소함
- 체결만 일일 거래 횟수를 증가시키고 실패·취소는 증가시키지 않음
- 제출된 주문은 거래 요청 로그에 기록되고, filled/failed/canceled 종료 결과는 거래 결과 로그에
  기록됨

### 13.3 E2E 및 전체 회귀

- 텔레그램 프로파일 → 가상 세션 생성 → 틱 → 주문 → 계좌·성과 조회
- 기존 BNH 요청은 `ord_type` 생략 시 지정가로 해석되지만 요청가와 현재가가 같아 즉시 체결됨
- 가상 세션 생성과 체결 동안 실제 거래소 Trader와 인증 주문 API가 생성·호출되지 않음
- 전체 unit/e2e 스위트 통과
- 문서와 패키지에서 활성 `JptController` 참조가 남지 않음

전략별로 주문장 로직을 중복 검증하지 않는다. 주문 의미는 `SimulationTrader` 단위 테스트에서
완전하게 검증하고, 대표 전략 및 표준 요청 스텁을 이용한 통합 테스트로 전략 독립성을 증명한다.

## 14. 완료 조건

- [ ] `JptController` 런타임 코드·export·활성 사용자 문서가 제거된다.
- [ ] 시장가·지정가·매도 손절·매도 익절이 이 문서의 조건과 가격으로 동작한다.
- [ ] 모든 대기 주문이 현금 또는 자산을 예약하고 중복 사용을 막는다.
- [ ] 개별 취소와 전체 취소가 예약을 반환하고 이후 체결을 막는다.
- [ ] 계좌 조회에서 총액·사용 가능액·예약액·대기 주문을 확인할 수 있다.
- [ ] 가상 체결 결과와 전략 내부 잔고가 수수료 0 기준으로 일치한다.
- [ ] 실제 Trader 구현은 변경되지 않고 미지원 주문 범위가 문서에 명시된다.
- [ ] OCO와 트레일링 스톱은 구현하지 않고 명시적으로 미지원으로 남는다.
- [ ] 전체 unit/e2e 테스트가 통과한다.
