# 멀티 세션 실거래 분산 운용 — 설계

**Status:** Approved
**Date:** 2026-07-06
**Branch:** `master`
**Author:** msaltnet (brainstorming via Claude)
**선행 문서:** `docs/superpowers/specs/2026-07-03-two-layer-llm-strategy-design.md` (2계층 아키텍처 — 구현 완료, v2.0.0)

## 1. 목표 (Goal)

여러 전략 × 여러 계좌 × 여러 심볼을 **동시에 병렬 운영**하고, 그 전체를 LLM 오케스트레이터(SystemOperator)가 대화로 지휘한다.

- **세션(Session)** = 프로파일의 실행 인스턴스. 프로파일(전략+거래소+심볼+예산+안전장치+계좌)을 독립 `TradingOperator`로 기동한 것.
- 에이전트는 세션을 생성·시작·중지·제거하고, 세션별/통합 성과를 보고한다.
- 실거래 세션과 가상(모의) 세션을 혼용할 수 있다.
- 계좌(API 자격증명)는 별칭으로 등록하며, **키 원문은 환경변수에만** 존재한다.

v2.0.0의 "SystemOperator가 TradingOperator 1개 소유" 제약을 "SessionManager가 N개 소유"로 확장한다. `TradingOperator`가 자기 완결적(전략/트레이더/애널라이저/세션 SafetyGuard 소유)이므로 병렬화는 구조적으로 자연스럽다.

## 2. 아키텍처 (Architecture)

```
Controller (CLI / Telegram / Jupyter)
   ▼
┌────────────────────────────────────────────────────────────────┐
│ SystemOperator  (LLM 오케스트레이터 — 유일한 제어점, 직접 매매 없음)      │
│  Tools:                                                          │
│   계좌  : register_account / list_accounts / delete_account       │
│   세션  : create_session / start_session / stop_session           │
│          / remove_session / list_sessions                         │
│   성과  : compare_performance / get_performance(session)          │
│   상태  : get_status (인자 없음=전체 요약, session 지정=상세)          │
│   레거시: select_strategy / start_trading / stop_trading           │
│          / get_status / switch_profile  (→ "default" 세션에 위임)   │
│   프로파일: 기존 CRUD 6종 유지 (account 필드 추가)                    │
└──────────────────────┬─────────────────────────────────────────┘
                       ▼
┌────────────────────────────────────────────────────────────────┐
│ SessionManager                                                   │
│  · {name: TradingSession} 보유                                    │
│  · 세션 생성 검증: 이름 유일성 / 계좌 존재 / (계좌,심볼) 실거래 충돌      │
│    / 계좌별 소프트 예산 총합 ≤ 실잔고                                 │
│  · AccountGuard(계좌 수준 안전장치) 계좌별 1개 공유                    │
└──────┬──────────────────┬──────────────────┬────────────────────┘
       ▼                  ▼                  ▼
  TradingSession     TradingSession     TradingSession
  "rsi-btc-main"     "llm-eth-main"     "bnh-virtual"
  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
  │TradingOperator│  │TradingOperator│  │TradingOperator│
  │ RSI / UPB    │    │ LLM / UPB    │    │ BnH / SIM    │
  │ main / BTC   │    │ main / ETH   │    │ (가상)       │
  │ 예산 30만     │    │ 예산 50만     │    │ 예산 50만     │
  └─────────────┘    └─────────────┘    └─────────────┘
       각 세션: 자기 전략 / 자기 Trader / 자기 Analyzer /
       CompositeSafetyGuard(세션 가드 + 계좌 AccountGuard)
```

**불변 원칙 (v2.0.0 승계)**
- 매매 경로는 세션 내부의 `Strategy.get_request() → Trader.send_request()` 단일 경로. 에이전트에 `execute_trade` 류 Tool 없음.
- 알고리즘 전략 세션의 틱은 LLM 호출 0회.
- 안전은 코드가 강제하며 LLM이 우회 불가 — 세션 전환/재생성으로 카운터가 리셋되지 않는다.

## 3. 컴포넌트 (Components)

### 3.1 `AccountStore` — 계좌 자격증명 레지스트리 (신규)

`ProfileStore`와 동일 패턴. `config/accounts/<alias>.json`, 파일 1개 = 계좌 1개.

```json
{
  "name": "main",
  "exchange": "UPB",
  "access_key_env": "SMTM_KEY_1",
  "secret_key_env": "SMTM_SECRET_1"
}
```

- **키 원문은 절대 저장·노출하지 않는다.** 파일과 대화에는 환경변수 *이름*만 존재한다.
- 허용 필드 4종 고정: `name`, `exchange`, `access_key_env`, `secret_key_env`. `name` 패턴 `^[A-Za-z0-9_-]{1,64}$`.
- API: `list_accounts() -> list[dict]`, `load(name) -> dict`, `save(account) -> dict`, `delete(name) -> bool`, `validate(account)`.
- 등록 시 환경변수 **존재 여부만** 검증(값은 읽지 않음). 미설정이면 저장은 허용하되 응답에 경고 포함 — 사용자가 나중에 env를 넣는 흐름 허용. Trader 생성 시점에는 미설정이면 **하드 실패**.

### 3.2 Trader 자격증명 주입 (기존 확장)

- `UpbitTrader`/`BithumbTrader` 생성자에 `access_key_env=None, secret_key_env=None` 파라미터 추가. 지정 시 해당 환경변수에서 키를 읽고, 미지정 시 기존 기본 환경변수명 사용(**하위 호환**).
- `TraderFactory.create(..., account: dict|None)` — account가 있으면 env 이름을 트레이더에 전달.
- **`cancel_all_requests`는 자기 인스턴스가 낸 주문만 취소한다** (계좌 전체 취소 금지). 같은 계좌의 다른 세션 주문을 건드리면 안 된다. 기존 구현이 자기 주문 추적 기반인지 확인하고, 아니면 수정한다.

### 3.3 프로파일 스키마 확장

- `ProfileStore.ALLOWED_FIELDS`에 `account` 추가 (계좌 별칭 참조).
- `virtual: true` 세션은 `account` 불필요(무시).
- 프로파일 Tool 스키마(`PROFILE_PROPERTIES`)에 `account` 추가.

### 3.4 `AccountGuard` — 계좌 수준 안전장치 (신규, 최소형)

같은 계좌의 모든 실거래 세션이 **공유**하는 가드. 세션 재생성·전환으로 리셋되지 않는다.

```python
@dataclass
class AccountGuardConfig:
    max_daily_trades: int = 60      # 계좌 전체 일일 거래 횟수 상한
    max_total_allocation: float = 10_000_000  # 세션 소프트 예산 총합 상한

class AccountGuard:
    def check_request(self, request) -> SafetyResult   # 일일 총 횟수 검사 (cancel 제외)
    def record_trade(self, result)                     # 스레드 안전 (Lock)
    def can_allocate(self, amount) -> SafetyResult     # 세션 생성 시 할당 검사
    def allocate(self, session_name, amount) / release(self, session_name)
```

- 여러 세션의 워커 스레드가 동시에 접근하므로 `threading.Lock`으로 카운터/할당 보호.
- 계좌 통합 손실률 한도는 **후속** (세션별 손실률은 기존 SafetyGuard가 담당).

### 3.5 `CompositeSafetyGuard` (신규, 얇음)

`TradingOperator`는 기존처럼 `safety_guard.check_request/record_trade/update_portfolio_value`만 호출한다. 실거래 세션에는 세션 가드와 계좌 가드를 묶은 컴포지트를 주입한다 — **TradingOperator 코드는 변경 없음**.

```python
class CompositeSafetyGuard:
    def __init__(self, guards: list): ...
    def check_request(self, request):   # 모든 가드 통과 시 허용, 첫 차단 사유 반환
    def record_trade(self, result):     # 모든 가드에 전파
    def update_portfolio_value(self, v) # 세션 가드에만 전파 (계좌 가드는 무시)
```

### 3.6 `TradingSession` + `SessionManager` (신규 — 핵심)

```python
@dataclass
class TradingSession:
    name: str
    profile: dict            # 생성 시점 스냅샷
    operator: TradingOperator
    trader: Trader
    account: str | None      # 계좌 별칭 (가상이면 None)
    created_at: str
    # state는 operator.state 위임
```

```python
class SessionManager:
    def __init__(self, account_store, llm_client, system_monitor): ...

    def create_session(self, profile: dict, name: str = None) -> dict
    def start_session(self, name) -> dict
    def stop_session(self, name) -> dict
    def remove_session(self, name) -> dict     # running이면 stop 후 제거, 할당 반환
    def stop_all(self) -> dict                  # 종료 시그널 처리용
    def list_sessions(self) -> list[dict]       # 요약: name/state/strategy/account/currency/budget/virtual
    def get_session_status(self, name) -> dict
    def get_performance(self, name) -> dict     # analyzer.get_return_report()
    def compare_performance(self) -> list[dict] # 전 세션 성과 나란히
```

**`create_session` 검증 순서** (모두 통과해야 생성):
1. 세션 이름 유일성 (기본값: 프로파일 `name`, 충돌 시 에러 — 명시적 이름 요구)
2. 프로파일 유효성 (전략 코드, 거래소 코드)
3. 실거래(`virtual: false`)인 경우:
   a. `account` 별칭이 AccountStore에 존재 + 프로파일 `exchange`와 계좌 `exchange` 일치
   b. 키 환경변수 실존재 (미설정 시 거부)
   c. **(계좌, 심볼) 충돌**: 같은 계좌·같은 currency의 실거래 세션이 이미 있으면 거부
   d. **소프트 예산 검증**: `AccountGuard.can_allocate(budget)` — 기존 할당 총합 + 신규 예산이 `max_total_allocation`과 **실계좌 잔고**(trader `get_account_info()` 1회 조회)를 넘지 않아야 함. 조회 실패 시 생성 거부(안전 우선)
4. 컴포넌트 조립: DataProvider / Trader(계좌 주입) / Strategy / Analyzer / 세션 SafetyGuard / (실거래면 CompositeSafetyGuard) / TradingOperator — 기존 `_build_trading_components` 로직을 SessionManager로 이관·일반화

- 가상 세션: 검증 3을 건너뜀. 개수 제한 없음.
- 세션 생성은 **생성만** 한다(자동 시작 안 함). 시작은 `start_session` 명시 호출.
- `remove_session`은 stopped 상태만 허용(running이면 먼저 stop) + AccountGuard 할당 해제.

### 3.7 `SystemOperator` 개편

- `self.trading_operator` 단일 보유 → `self.session_manager` 보유로 교체.
- **신규 Tool 9종**: `register_account`/`list_accounts`/`delete_account`, `create_session`/`start_session`/`stop_session`/`remove_session`/`list_sessions`/`compare_performance`.
- `get_session_status(name)`는 `get_status`에 통합: 인자 없으면 전체 요약(세션 목록+계좌별 할당), `session` 인자를 주면 해당 세션 상세.
- **레거시 호환 ("default" 세션)**: 부팅 config(`--strategy`/`--profile`)로 `"default"` 세션을 자동 *생성*(시작은 안 함). default 세션은 특례를 가진다 —
  - `account` 미지정 실거래를 허용하며 이때 Trader는 레거시 기본 환경변수(`SMTM_UPBIT_ACCESS_KEY` 등)를 사용한다. (계좌,심볼) 충돌·AccountGuard 계산에서는 별칭 `"legacy"`로 취급.
  - 부팅이 거래소 API에 의존하지 않도록, `account` 미지정 default 세션은 실잔고 검증(3.6-3d)을 생략한다(기존 v2.0.0 부팅 동작 유지). 계좌를 참조하는 세션은 항상 전체 검증을 거친다.
  - 기존 Tool은 default 세션에 위임 —
  - `select_strategy(code)` → default 세션이 stopped일 때 전략 교체(재생성)
  - `start_trading`/`stop_trading` → `start_session("default")`/`stop_session("default")`
  - `switch_profile(name)` → default 세션을 해당 프로파일로 재생성
- 읽기 Tool(`get_market_data`/`get_portfolio`/`get_trade_history`/`get_performance`)에 optional `session` 인자 추가(기본 `"default"`).
- 시스템 프롬프트를 멀티 세션 지휘 역할로 갱신 (세션 목록/계좌 현황 요약 포함).
- 종료 시 `session_manager.stop_all()` (Controller `_terminate` 배선).

### 3.8 SystemMonitor / Analyzer

- `SystemMonitor`는 프로세스 전역 1개 유지(로그 통합)하되, 모든 기록에 `session` 필드를 추가해 세션별 조회 가능하게 한다. (`log_*` 메서드에 optional `session=None` 파라미터 — 하위 호환)
- `Analyzer`는 세션당 1개(기존 구조). `put_*` 호출 시 자신의 세션 이름을 SystemMonitor에 전달.

### 3.9 Controller / CLI

- CLI 플래그 변경 없음. 부팅 시 default 세션 생성(기존 UX 동일: "start" 입력 → default 세션 시작).
- `TelegramController`의 **부팅 자동 시작 제거** — 세션 모델에서 자동 실거래 시작은 위험(최종 리뷰 지적 사항). "start" 명령으로만 시작.

## 4. 데이터 플로우 (Data Flow)

1. **계좌 등록**: 사용자가 env에 키 설정 → 채팅 "sub1 계좌 등록해줘, SMTM_KEY_2 사용" → `register_account` → `config/accounts/sub1.json` 기록 (env 이름만).
2. **세션 기동**: "RSI로 BTC 30만원 main 계좌에서 돌려줘" → 에이전트가 `create_profile`(또는 기존 프로파일) → `create_session(profile, name)` → 검증 통과 → `start_session(name)` (에이전트는 시작 전 사용자 확인).
3. **병렬 틱**: 각 세션의 TradingOperator가 자기 타이머/워커로 독립 틱. 주문 직전 CompositeSafetyGuard(세션→계좌 순) 검사.
4. **성과 비교**: "지금 뭐가 제일 잘 벌어?" → `compare_performance` → 세션별 누적 수익률 표 → 에이전트가 해설.
5. **중지/제거**: `stop_session` → 타이머 취소·자기 주문만 취소. `remove_session` → 할당 반환.

## 5. 에러 처리 / 안전 (Error Handling & Safety)

- **키 비노출**: AccountStore/Tool/로그 어디에도 키 값이 나타나지 않는다. Tool 결과에는 env 변수 이름과 "설정됨/미설정"만 포함.
- **세션 생성 실패 = 무부작용**: 검증 실패 시 어떤 컴포넌트도 남기지 않고 명확한 한국어 에러 반환. 할당도 검증 통과 후에만 기록.
- **계좌 카운터 영속**: AccountGuard의 일일 카운터는 세션 재생성과 무관하게 유지(SystemOperator 수준에서 계좌별 1개 보유). 프로세스 재시작 시 리셋은 알려진 한계(후속: 디스크 영속화).
- **동시성**: AccountGuard는 Lock 보호. 세션 간 다른 공유 상태 없음(SystemMonitor append는 GIL 하 list.append로 안전, 필요 시 Lock).
- **한 세션의 장애는 다른 세션에 전파되지 않는다**: 틱 예외는 세션 내부에서 흡수(기존 동작).
- **rate limit**: 같은 거래소를 여러 세션이 폴링하면 호출량 증가 — MVP는 소수 세션 전제로 허용, 문서에 명시. 공유 캐시는 후속.

## 6. 테스트 전략 (Testing)

- **단위**: AccountStore CRUD/검증(env 미설정 경고 포함) / AccountGuard(할당·일일 카운터·Lock 동작) / CompositeSafetyGuard(전파·차단 순서) / SessionManager 생성 검증 5경로(이름 충돌, 계좌 없음, env 미설정, (계좌,심볼) 충돌, 예산 초과 — 실잔고는 mock).
- **통합**: 가상 세션 2개 병렬 생성·시작 → 각자 독립 틱·독립 장부 확인 → 성과 비교. 같은 계좌 2세션의 AccountGuard 일일 한도 공유 검증(fake trader).
- **오케스트레이션**: 신규 Tool 9종 + 레거시 Tool의 default 세션 위임 (FakeLlmClient).
- **E2E**: 채팅으로 계좌 등록 → 프로파일 생성 → 세션 2개(가상) 기동 → 틱 → compare_performance → 개별 중지.
- 실거래 경로(키 주입, 잔고 조회)는 mock으로 검증. 유닛 테스트에서 실 네트워크 호출 금지(기존 원칙).

## 7. 범위 (Scope)

### 7.1 포함 (In Scope)
- `AccountStore` + 계좌 Tool 3종 (env 이름 참조 방식).
- Trader 자격증명 주입 + `cancel_all_requests` 자기 주문 한정 보장.
- 프로파일 `account` 필드.
- `AccountGuard`(일일 총 횟수 + 할당 총액) + `CompositeSafetyGuard`.
- `TradingSession`/`SessionManager` + 생성 검증(소프트 예산 합계 ≤ 실잔고, (계좌,심볼) 충돌 방지).
- `SystemOperator` 세션 Tool 6종 + 레거시 default 위임.
- SystemMonitor 세션 태깅.
- TelegramController 자동 시작 제거.

### 7.2 비범위 (Out of Scope — 후속)
- 런타임 예산 재배분 Tool.
- 계좌 통합 손실률 한도.
- 세션 자동 복구(프로세스 재시작 시) / AccountGuard 카운터 디스크 영속화.
- DataProvider 공유 캐시(거래소 rate limit 최적화).
- 같은 (계좌,심볼) 복수 세션 허용(포지션 분리 회계).
- 암호화 키스토어(마스터 패스프레이즈).
- YAML 설정 지원(JSON으로 통일; YAML은 필요 시 후속).
- Binance 실주문 트레이더.

## 8. 결정 기록 (Decisions)

| 결정 | 선택 | 근거 |
|------|------|------|
| 자격증명 | 별칭 환경변수(`SMTM_KEY_n`) + JSON 참조 파일 | 키 원문 비저장·비노출, 동적 등록 가능 (사용자 결정) |
| 자금 규율 | 세션별 소프트 예산, 생성 시 합계 ≤ 실잔고 검증 | 예측 가능·전략 자기-회계 유지 (추천안 승인) |
| (계좌,심볼) 충돌 | 실거래 세션 1개 제한 | 자기-회계 충돌 방지 (승인) |
| 계좌 안전장치 | 일일 총 횟수 + 할당 총액 최소형 | MVP 단순성 (승인) |
| 세션 시작 | 생성과 시작 분리, 자동 시작 금지 | 실거래 안전 (에이전트가 시작 전 확인) |
