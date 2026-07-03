# 2계층 LLM 아키텍처 + 계좌 프로파일 — 설계

**Status:** Approved
**Date:** 2026-07-03
**Branch:** `claw`
**Author:** msaltnet (brainstorming via Claude)
**관련 문서:** `docs/claw-branch-review.md`, `docs/superpowers/specs/2026-04-26-paper-trading-design.md`

## 1. 목표 (Goal)

claw 브랜치는 규칙 기반 시스템을 "LLM이 Tool을 자율 호출하는 단일 에이전트(`LlmOperator`)"로 통째로 재작성했다. 이 설계는 **LLM 사용을 두 가지 역할로 분리**하여 기존 알고리즘 전략 구조를 되살리면서 확장성을 확보한다.

1. **시스템 운영 LLM (SystemOperator)** — 사용자와 대화하며 시스템 전반을 지휘하는 최상위 컨트롤러. Tool use 방식 유지. **직접 매매는 하지 않고 오케스트레이션만** 담당.
2. **Strategy with LLM (LlmStrategy)** — 기존 `Strategy` 인터페이스를 그대로 따르는 전략. 고정 주기 루프 안에서 매 틱마다 LLM에 **단일 구조화 판단**을 요청.

이렇게 하면:
- 기존 `Strategy` 인터페이스가 복원되어 알고리즘 전략(BnH/RSI/SMA)을 다시 구동할 수 있다.
- 같은 자리에 `LlmStrategy`를 끼워 LLM 기반 매매도 가능하다.
- 매매 경로가 `Strategy → Trader` 하나로 단일화되어 계좌 충돌이 없다.
- 새 전략 추가가 인터페이스 구현만으로 가능해 확장성이 좋다.

## 2. 아키텍처 (Architecture)

3계층 구조. 상위(에이전트)가 하위(트레이딩 루프)를 소유·지휘한다.

```
Controller (CLI / Telegram / Jupyter)
   │  프로파일 로드 (--profile NAME / --config PATH)
   ▼
┌──────────────────────────────────────────────────────────────┐
│ SystemOperator  (시스템 운영 LLM 에이전트 — 현 LlmOperator 리팩터)   │
│  · 채팅 루프 + Tool use 루프 (오케스트레이션 전용, 직접 매매 X)         │
│  · 상태머신 ready / running / stopped                            │
│  · TradingOperator 를 소유하고 제어                                │
│  Tools:                                                        │
│   - list_strategies / describe_strategy                        │
│   - select_strategy(code, params)                              │
│   - start_trading / stop_trading / get_status                  │
│   - get_performance / get_market_data (읽기 전용 분석)            │
│   - list_profiles / describe_profile / create_profile          │
│   - switch_profile / update_profile / delete_profile           │
└───────────────┬────────────────────────────────────────────────┘
                │ 제어(지휘)만 — 직접 주문 없음
                ▼
┌──────────────────────────────────────────────────────────────┐
│ TradingOperator  (고정 주기 루프 — master Operator 복원·슬림)       │
│  timer(term) →                                                 │
│    DataProvider.get_info()                                     │
│    → Strategy.update_trading_info(info)                        │
│    → request = Strategy.get_request()                          │
│    → SafetyGuard 검사 → Trader.send_request(request, cb)        │
│    → cb: Strategy.update_result(result)                        │
│    → Analyzer.put_trading_info / put_requests / put_result     │
└───────┬────────────────────┬────────────────────┬──────────────┘
        ▼                    ▼                    ▼
   DataProvider          Strategy             Trader / Analyzer
   (claw 카탈로그          ├─ AlgorithmicStrategy: BnH / RSI / SMA
    그대로 재사용)          └─ LlmStrategy: 틱마다 단일 구조화 판단
                                             (LlmClient 재사용)
```

**단일 매매 경로 원칙**: 모든 주문은 `Strategy.get_request()` → `Trader.send_request()`를 거친다. 에이전트는 `execute_trade` 류 Tool을 갖지 않는다. 기존 claw의 "LLM Tool 매매"는 폐기가 아니라 `LlmStrategy`로 **이전(relocate)** 된다.

**LLM 호출 지점**은 정확히 두 곳뿐이다: (a) SystemOperator의 대화/오케스트레이션, (b) LlmStrategy의 틱당 판단. 알고리즘 전략만 돌 때 트레이딩 루프는 LLM을 전혀 호출하지 않는다.

## 3. 컴포넌트 (Components)

### 3.1 `Strategy` (추상 인터페이스 복원)

master의 `smtm/strategy/strategy.py` 계약을 복원한다. claw의 다형 DataProvider 리스트(`type='primary_candle'` 등 혼합)를 소비하도록 문서화한다.

```python
class Strategy(metaclass=ABCMeta):
    CODE = "---"
    NAME = "---"

    @abstractmethod
    def initialize(self, budget, min_price=100,
                   add_spot_callback=None, add_line_callback=None,
                   alert_callback=None): ...

    @abstractmethod
    def update_trading_info(self, info): ...   # info: DataProvider 다형 리스트

    @abstractmethod
    def get_request(self):                     # -> list[dict] 거래 요청
        ...

    @abstractmethod
    def update_result(self, result): ...
```

거래 요청 스키마 (master와 동일):
```
{ "id", "type": buy|sell|cancel, "price", "amount", "date_time" }
```

### 3.2 AlgorithmicStrategy 3종

master에서 포팅. LLM/네트워크 의존 없음. 다형 리스트에서 `type == 'primary_candle'` 항목만 추려 기존 로직을 재사용.

- `StrategyBnH` (Buy and Hold) — `smtm/strategy/strategy_bnh.py`
- `StrategyRSI` — `smtm/strategy/strategy_rsi.py`
- `StrategySMA` (SMA 교차) — `smtm/strategy/strategy_sma.py` (master `strategy_sma_0` 기반, ML 의존 제거)

### 3.3 `LlmStrategy`

같은 `Strategy` 인터페이스 구현. 틱당 LLM 1회 호출(Tool 루프 없음).

- `initialize()` — 예산·콜백 저장, `.md` 전략 지식 로드(`smtm/strategies/*.md`).
- `update_trading_info(info)` — 최신 시장 데이터/지표를 내부 버퍼에 축적.
- `get_request()` — `LlmClient`에 **구조화 판단**을 1회 요청하고 결과를 거래 요청 리스트로 변환.
- `update_result(result)` — 직전 판단의 체결 결과를 다음 프롬프트 맥락으로 반영(선택).

구조화 출력 스키마:
```json
{
  "action": "buy" | "sell" | "hold",
  "price": <number|null>,
  "amount": <number|null>,
  "confidence": <0.0~1.0>,
  "reason": "<판단 근거>"
}
```

구현: 단일 `submit_decision` Tool을 정의하고 **forced tool use**(tool_choice로 해당 Tool 강제)로 위 스키마를 반드시 채우게 한다. 이는 기존 `ClaudeLlmClient`의 Tool use 경로를 그대로 활용하는 가장 신뢰도 높은 방식이다. 스키마 검증 실패 시 해당 틱은 안전하게 `hold`로 처리하고 로그를 남긴다. 필요 시 `LlmClient`에 구조화 판단용 헬퍼(`decide(system, messages, schema)`)를 추가한다.

### 3.4 `TradingOperator`

master `Operator`를 복원하되 슬림화. 타이머·`Worker`·틱 파이프라인 담당. claw `LlmOperator`의 타이머/worker 로직을 재사용한다.

- `initialize(data_provider, strategy, trader, analyzer, safety_guard, budget)`
- `start()` / `stop()` / `get_score()` (성과 조회)
- 틱: DataProvider → Strategy → (SafetyGuard) → Trader → Strategy.update_result → Analyzer

SafetyGuard 검사는 `Trader.send_request` 직전에 수행하여 **전략 종류와 무관하게** 하드리밋을 강제한다.

### 3.5 `Analyzer` (경량 신규)

`SystemMonitor` 위에 Strategy 콜백 계약과 최소 성과 집계를 제공하는 얇은 계층.

- Strategy 콜백: `add_drawing_spot`, `add_value_for_line_graph`, `alert_callback` 배선(no-op 또는 SystemMonitor 기록).
- `put_trading_info(info)` / `put_requests(req)` / `put_result(result)` — SystemMonitor로 위임.
- `initialize(get_account_info)` / `make_start_point()` / `get_return_report(...)` — 최소 성과(시작 자산, 현재 자산, 누적 수익률).
- 그래프/PDF 리포트는 **비범위**(후속).

### 3.6 `SystemOperator` (현 `LlmOperator` 리팩터)

현 `LlmOperator`에서 매매 Tool을 제거하고 오케스트레이션·프로파일 Tool을 추가.

- 유지: 채팅 루프, Tool use 루프, 상태머신, 대화 이력 관리, SystemMonitor 연동.
- 제거: `TradeTool`(execute_trade), 직접 매매 관련 배선.
- 추가 Tool: 3.0의 목록(전략 지휘 / 상태·성과 조회 / 프로파일 CRUD).
- `TradingOperator`를 소유. `start_trading`/`stop_trading` Tool이 `TradingOperator.start()/stop()`을 호출.
- 시장 데이터 읽기 전용 조회(`get_market_data`)는 분석 목적으로 유지.

### 3.7 `Profile` + `ProfileStore`

실행 프리셋 번들. 기존 `config/*.json` 로딩의 자연스러운 확장.

```json
{
  "name": "aggressive-btc-virtual",
  "exchange": "UPB",
  "currency": "BTC",
  "budget": 500000,
  "virtual": true,
  "term": 60,
  "strategy": "LLM",
  "strategy_params": { "model": "claude-sonnet-4-20250514" },
  "safety": { "max_trade_amount": 100000, "max_daily_trades": 20, "max_loss_ratio": -0.2 }
}
```

- `ProfileStore` — `config/profiles/*.json` 로드/저장/열거/삭제. 파일 1개 = 프로파일 1개.
- 에이전트 Tool로 CRUD: `create_profile`, `list_profiles`, `describe_profile`, `switch_profile`, `update_profile`, `delete_profile`.
- Controller는 시작 시 `--profile NAME` 또는 `--config PATH`로 프로파일을 로드해 초기 구성을 만든다.
- 하위 호환: 기존 `config/virtual-upbit.json` 형식과 개별 CLI 플래그(`--budget` 등)는 계속 동작. 프로파일은 그 위의 선택적 번들.

## 4. 데이터 플로우 (Data Flow)

1. **틱 사이클 (완전 자동, 에이전트 개입 없음)**
   `TradingOperator` 타이머 만료 → DataProvider.get_info() → Strategy.update_trading_info → Strategy.get_request → SafetyGuard 검사 → Trader.send_request → 콜백에서 Strategy.update_result → Analyzer 기록.

2. **에이전트 제어**
   사용자 채팅 → SystemOperator Tool use → `select_strategy`/`start_trading`/`stop_trading`/`get_status`/`get_performance` → TradingOperator 상태·구성 변경.

3. **프로파일 전환**
   사용자 요청 → 에이전트 `switch_profile(name)` → 실행 중이면 `stop_trading` → Trader/Strategy/DataProvider 재구성 → 사용자 확인 후 `start_trading`.

4. **프로파일 생성**
   사용자 대화 요청 → 에이전트 `create_profile(...)` → `ProfileStore`가 `config/profiles/<name>.json` 기록 → `list_profiles`로 확인.

## 5. 에러 처리 / 안전 (Error Handling & Safety)

- **SafetyGuard 유지·이동**: 검사 지점을 `TradingOperator`의 `Trader.send_request` 직전으로 이동. 알고리즘·LLM 전략 모두 동일하게 1회 거래 금액/일일 횟수/누적 손실률 하드리밋 강제. 위반 시 요청 차단 + 한글 사유 + `safety_event_log` 기록.
- **DataProvider 실패**: 기존대로 빈 리스트로 흡수, 루프 미정지.
- **LlmStrategy 파싱 실패**: 해당 틱 `hold` 처리 + 경고 로그. 루프 지속.
- **프로파일 오류**: 존재하지 않는 프로파일/필드 검증 실패 시 에이전트에 명확한 에러 반환, 현재 구성 유지.

## 6. 테스트 전략 (Testing)

- **단위**: `StrategyBnH/RSI/SMA` 각각 / `LlmStrategy`(FakeLlmClient로 구조화 출력 주입) / `Analyzer` / `ProfileStore` CRUD.
- **통합**: `TradingOperator` 전 틱 사이클(FakeDataProvider + FakeTrader + Fake/Algo Strategy), SafetyGuard 차단 경로.
- **오케스트레이션**: `SystemOperator`의 전략 지휘 Tool / 프로파일 CRUD Tool (FakeLlmClient).
- **E2E**: 기존 `tests/e2e_tests/` 골격 재활용 — 채팅 → 전략 선택 → start → 틱 → 결과.

## 7. 범위 (Scope)

### 7.1 포함 (In Scope)
- `Strategy` 추상 인터페이스 복원.
- AlgorithmicStrategy 3종(BnH/RSI/SMA) 포팅.
- `LlmStrategy` (단일 구조화 판단).
- `TradingOperator` (고정 주기 루프) 복원·슬림.
- 경량 `Analyzer` 신규.
- `SystemOperator` 리팩터(오케스트레이션 전용, 매매 Tool 제거).
- 전략 지휘 + 프로파일 CRUD Tool.
- `Profile` / `ProfileStore` (JSON 영속화, 에이전트 생성 포함).

### 7.2 비범위 (Out of Scope — 후속)
- ML 기반 전략(SMA-ML/dual-ML/hey/sas).
- 그래프/PDF 성과 리포트, 시각화.
- 다중 거래소 자격증명 관리(멀티 계정).
- 프로파일별 독립 장부/포트폴리오 격리.
- 세션 간 잔고/주문 영속화.
- Telegram(`--mode 1`)에서의 프로파일 배선.
- 백테스트/시뮬레이션 리플레이 전용 DataProvider.

## 8. 미해결/주의 (Notes)

- **에이전트가 진입점**이므로 순수 알고리즘 전략만 돌려도 `SMTM_LLM_API_KEY`가 필요하다(제어 UI가 LLM). 트레이딩 루프 자체는 알고리즘 전략일 때 LLM 미호출. 완전 헤드리스(키 불필요) 실행은 후속 과제로 남긴다.
- 명명: 상위 = `SystemOperator`, 하위 루프 = `TradingOperator`. 구현 시 기존 `LlmOperator` 참조를 점진적으로 대체한다.
- 버전: claw의 아키텍처 재정의가 누적되므로 병합 시 `2.0.0`급 재넘버링이 자연스럽다(별도 결정).
