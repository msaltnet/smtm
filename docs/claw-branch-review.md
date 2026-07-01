# `claw` 브랜치 점검 — main(`master`)과의 차이 및 최종 요구사항 정리

> GitHub Issue [#50](https://github.com/msaltnet/smtm/issues/50) 대응 문서.
> `claw` 브랜치가 `master`와 무엇이 다른지, 최종 목표점과 요구사항 변경이 무엇인지 한 곳에 정리합니다.

- 작성일: 2026-07-01
- 대상 브랜치: `claw`
- 비교 기준: `master` (`v1.8.0`)
- 분기점(merge-base): `84f06e8`

---

## 1. 한 줄 요약

**`claw`는 smtm을 "규칙 기반 알고리즘 트레이딩 시스템"에서 "LLM 에이전트 기반 자율 매매 시스템"으로 통째로 재작성한 브랜치입니다.**

> **"LLM이 판단하고, 규칙이 지키고, 사용자가 대화로 제어하는 자율 매매 시스템"**

`master`는 기존 규칙 엔진(Strategy/Analyzer/Simulator) 계열 코드를 유지한 채 `v1.8.0`으로 버전만 올라간 레거시 라인이고, `claw`는 `v1.7.1` 시점에서 갈라져 나와 아키텍처를 전면 교체했습니다. 두 브랜치는 사실상 **다른 제품**에 가깝습니다.

---

## 2. 브랜치 관계 (숫자)

| 항목 | 값 |
|------|-----|
| 분기점(merge-base) | `84f06e8` |
| `claw`에만 있는 커밋 | 29개 |
| `master`에만 있는 커밋 | 2개 (`v1.8.0` 버전 태깅, CI 의존성 수정) |
| 변경 파일 | 522개 |
| 추가 라인 | ~9,566 |
| 삭제 라인 | ~290,010 (대부분 레거시 전략 테스트 결과 픽스처 `MASS-*.txt`/`.jpg`, 노트북) |
| `master` 버전 | `1.8.0` |
| `claw` 버전 | `1.7.1` |

> 참고: `master`가 갖고 있는 `v1.8.0`은 **레거시 규칙 엔진 라인의 버전업**이며, `claw`의 LLM 재작성 내용은 포함하지 않습니다. `claw`는 `master`가 `v1.8.0`이 되기 이전 지점에서 분기했기 때문에 `master`의 최근 2개 커밋을 갖고 있지 않습니다.

---

## 3. 무엇이 바뀌었나 — 아키텍처 전환

### 3.1 제거된 것 (레거시 규칙 엔진)

`claw`에서 다음이 통째로 삭제되었습니다.

- **Strategy 계열** — `strategy_bnh`, `strategy_rsi`, `strategy_sma_0`, `strategy_sma_ml`, `strategy_sma_dual_ml`, `strategy_hey`, `strategy_sas`, `strategy_factory` 및 관련 단위/통합 테스트.
- **Analyzer 계열** — `analyzer`, `data_analyzer`, `data_repository`, `graph_generator`, `report_generator`, `database`.
- **Simulator 계열** — `simulator`, `mass_simulator`, `simulation_operator`, `virtual_market`, `demo_trader`, 시뮬레이션 데이터 프로바이더.
- **레거시 CLI 모드** — `--mode 2`~`5` (단순 시뮬레이션 / 매스 시뮬레이션 / 설정 생성 / 데모).
- **레거시 텔레그램 커맨드/매니저** — `telegram/commands/*`, `setup_manager`, `ui_manager`.
- **레거시 전략 테스트 결과 픽스처** — `tests/strategy_tests/**/result/*` (삭제 라인 대부분이 여기서 나옴), 각종 `notebook/*.ipynb`.

### 3.2 추가된 것 (LLM 에이전트 스택)

새 패키지 `smtm/llm/`:

- **`LlmOperator`** — 주기 틱(기본 60초)과 사용자 메시지를 **동일한 대화 세션**에서 처리하는 오케스트레이터. 상태 머신(`ready`/`running`/`stopped`) + 타이머 + 대화 이력 관리 + Tool use 루프.
- **`LlmClient` 추상화 + `ClaudeLlmClient`** — 벤더 독립 인터페이스. Anthropic Claude(`claude-sonnet-4-20250514`)가 첫 구현. `LlmResponse(text, tool_calls, stop_reason, usage)`로 응답 정규화.
- **`ToolRouter` + Tool 5종** — `get_market_data`, `execute_trade`, `get_portfolio`, `get_trade_history`, `get_performance`. LLM이 자율적으로 호출.
- **`SafetyGuard` + `SafetyConfig`** — `execute_trade` 실행 **직전**에 1회 거래 금액(기본 10만), 일일 거래 횟수(기본 20), 누적 손실률(기본 -20%)을 강제. LLM이 우회 불가.
- **`SystemMonitor`** — market_data / tool_call / trade_request / trade_result / llm_interaction / safety_event / snapshot 7종을 구조화 로그로 수집(현재 인메모리).
- **전략 지식 문서** — `smtm/strategies/{buy_and_hold,rsi_strategy,sma_crossover}.md`. 기존 코드 전략을 LLM 시스템 프롬프트용 지식으로 이관.

### 3.3 대폭 확장된 것 — DataProvider 카탈로그

`DataProvider` 계약이 **다형 데이터 리스트**로 재정의됐습니다. `get_info()`가 `type` 필드로 구분되는 딕셔너리 리스트를 반환하며, 주 캔들(`type='primary_candle'`) 외에 뉴스/공지/소셜 같은 텍스트 타입을 같은 리스트에 섞어 반환할 수 있습니다. 네트워크/파싱 실패는 빈 리스트로 흡수해 매매 루프를 멈추지 않습니다.

신규 프로바이더(무료·키 불필요 다수):

- **뉴스**: `news_data_provider`, `multi_news_data_provider`, `upbit_news`/`upbit_multi_news`/`upbit_notice`/`upbit_social`, `upbit_full_context`, `news_sources`
- **소셜**: `reddit_data_provider`, `hackernews_data_provider`
- **감정/시총**: `fear_greed`, `coingecko`, `coincap`, `crypto_global`
- **전통시장/매크로**: `yahoo_finance` (DXY·S&P500·VIX·Gold·US10Y·Nasdaq)
- **온체인**: `blockchain_info`, `mempool_fees`, `etherscan_gas`
- **파생/포지셔닝**: `binance_funding_rate`, `binance_open_interest`, `binance_long_short_ratio`
- **환율**: `exchange_rate` (USD→KRW/JPY/EUR/CNY)

### 3.4 테스트 프레임워크 재편

- 신규 **E2E 테스트**(`tests/e2e_tests/`) — `FakeLlmClient` / `FakeDataProvider`로 외부 API 없이 채팅 → Tool → 거래 → 결과 전 구간 검증.
- 레거시 전략/시뮬레이터/analyzer 단위·통합 테스트 삭제, LLM 스택·DataProvider별 단위 테스트 대량 추가.

### 3.5 문서/설정

- `docs/public/` 신설 — `overview`, `requirements`, `architecture`, `data-providers`, `user-guide`, `faq`, `release-notes`. (기존 `doc/` → `docs/`로 이동)
- `README.md` / `README-ko-kr.md` LLM 아키텍처 기준으로 재작성.
- `--mode 2`~`5` 제거, `--mode 0`(CLI 채팅) / `--mode 1`(Telegram)만 유지.
- **신규 필수 환경변수** `SMTM_LLM_API_KEY`.

---

## 4. 최종 요구사항 / 목표점

`claw`의 최종 목표는 `docs/public/requirements.md`에 `[MVP]`/`[후속]`으로 정식화되어 있습니다. 핵심만 요약합니다.

### 4.1 목표(제품 정체성)
- **판단은 LLM에게 위임** — LLM이 시장 데이터를 읽고 필요할 때만 매매 Tool 호출.
- **안전은 코드가 강제** — `SafetyGuard`가 하드 리밋을 강제하며 LLM이 우회 불가.
- **제어는 자연어로** — CLI / Telegram / Jupyter에서 한국어·영어 메시지로 상호작용, `start`/`stop`으로 자동 매매 루프 토글.
- **대상 범위** — 개인 트레이더가 단일 호스트에서 소액(기본 예산 50만 원) 암호화폐 자동매매. (멀티테넌시·웹 대시보드·클라우드 분산·세금 리포팅은 미포함)

### 4.2 이미 충족된 MVP 요구사항(영역별)
- **대화(R-CHAT)** — CLI stdin/stdout 채팅, `start`/`stop`으로 타이머 토글, `q/quit/exit`로 안전 종료, Telegram은 지정 `chat_id`만 수용, Jupyter `JptController` 지원.
- **오케스트레이션(R-ORCH)** — 3-상태 머신, `--term` 주기 프롬프트, 사용자 메시지+틱 동일 이력 공유, Tool use 루프, 대화 이력 상한(`max_conversation_turns*2`).
- **Tool(R-TOOL)** — 기본 5종 등록, `execute_trade`/`get_market_data` 입력 스키마 규정, `ToolResult.to_dict()` 직렬화.
- **안전(R-SAFE)** — `execute_trade` 직전 검사, 3종 한도 강제, 위반 시 실패+한글 사유, `safety_event_log` 기록, 날짜 변경 시 카운터 리셋.
- **데이터(R-DATA)** — 다형 리스트 계약, `UPB/BTH/BNC/UBD/UPN` 등, 실패는 빈 리스트로 흡수.
- **거래소(R-EXEC)** — `Trader` 계약, Upbit/Bithumb 실주문, API 키 환경변수 전용·로그 비노출, `commission_ratio` 주입.
- **관찰(R-OBS)** — 7종 로그, ISO8601 타임스탬프, 토큰 사용량 집계, `log/smtm.log` 2MB×10 롤링, 키 비노출.
- **LLM 추상화(R-LLM)** — `LlmClient` 계약, `LlmResponse` 정규화, Claude 어댑터 기본 포함.
- **설정/실행(R-CFG)** — `--mode/--budget/--currency/--exchange/--term/--token/--chatid/--log/--version`, 민감정보 env 전용.

### 4.3 요구사항 변경(가장 최근) — 가상(모의) 매매 모드 추가

`claw` 후반부(커밋 `d808793`→`302d4cc`→`63cf010`)에서 요구사항이 한 번 확장됐습니다. 설계 문서는 `docs/superpowers/specs/2026-04-26-paper-trading-design.md`.

- **목표** — LLM 매매 파이프라인 전체를 **실시간 시세**에 대해 돌리되 **주문은 모의**로 처리. 실거래 API 호출 없음, 실자금 위험 없음. 카탈로그의 모든 DataProvider(`UPB`/`UMN`/`USC`/`UFC` …)를 거래소 계정 없이 안전하게 E2E로 사용 가능.
- **핵심 설계** — 두 축을 직교 분리:
  - *데이터 소스(where)* = `--exchange CODE` (DataProvider 선택)
  - *거래 목적지(what)* = `--virtual` 플래그 (Trader를 `SimulationTrader`로 교체, `--exchange`와 무관)
- **동작** — 매 틱마다 `LlmOperator`가 `primary_candle.closing_price`를 추출해 `trader.update_quote(currency, price)`로 주입(덕 타이핑). 실거래 트레이더에는 해당 메서드가 없어 no-op. 시뮬레이터는 LLM이 넘긴 `price`를 무시하고 주입된 시세로 체결.
- **명명 변경(주의)** — 설계 단계 명칭은 "paper trading"이었고, 최종 커밋 `63cf010 [ux] rename paper mode to virtual trading`에서 **사용자 노출 명칭을 "virtual trading(가상 매매)"으로 변경**했습니다.
  - CLI 플래그: `--virtual` (구 `--paper`는 별칭으로 유지)
  - 설정 파일 키: `"virtual": true`
  - 내부 식별자는 여전히 `paper`로 남아 있음(`args.paper`, `Controller(paper=...)`, `TraderFactory.create(paper=...)`).
- **설정 파일 지원** — `--config config/virtual-upbit.json` 형태로 JSON 설정 로드 지원(신규). 예시 파일 `config/virtual-upbit.json`:
  ```json
  { "mode": 0, "budget": 500000, "currency": "BTC", "exchange": "UPB", "virtual": true, "term": 60 }
  ```
- **범위 밖(후속)** — 세션 간 잔고/주문 영속화, 부분 체결, 수수료 모델(파라미터만 존재·현재 0 적용), 시뮬레이션 전용 DataProvider(백테스트 리플레이), Telegram(`--mode 1`)에서의 `--virtual` 배선.

### 4.4 남은 후속 과제(로드맵)
- **단기**: SafetyConfig CLI 노출(`--max-trade-amount` 등), Binance Trader 실주문 구현, SystemMonitor 디스크 영속화(JSONL/SQLite).
- **중기**: OpenAI 어댑터, Ollama/로컬 LLM 어댑터, Anthropic prompt caching 적용, systemd/Docker 공식 제공, multimodal `tool_result`.
- **장기**: 웹 대시보드, 다중 계좌/멀티 거래소 동시 운용, 세금/정산 리포트.

---

## 5. Breaking Changes (레거시 → claw)

| 변경 | 마이그레이션 |
|------|-------------|
| `--mode 2`~`5`(시뮬/매스시뮬/설정생성/데모) 제거 | `--mode 0` 또는 `--mode 1`로 대체. 시뮬레이션은 `--virtual` 모드 또는 `tests/e2e_tests/` 구조 활용. |
| `SMTM_LLM_API_KEY` 필수 환경변수 추가 | 실행 전 `.env` 또는 쉘에 Anthropic 키 설정. |
| Analyzer 기반 규칙 엔진 제거, Strategy가 markdown 지식 문서로 이관 | 커스텀 Strategy는 `smtm/strategies/*.md`로 옮기거나 새 Tool로 구현. |

---

## 6. 결론 / 점검 소견

- `claw`는 `master`의 후속 버전이 아니라 **아키텍처 재작성 브랜치**다. 병합 시 `master`의 규칙 엔진 라인은 사실상 대체된다.
- 버전 번호가 역전되어 있다(`master 1.8.0` vs `claw 1.7.1`). 병합 전 **버전 정합성 정리** 필요 — `claw`의 LLM 아키텍처를 살릴 경우 `2.0.0`급(메이저 breaking) 재넘버링이 자연스럽다.
- 최근 요구사항 변경(가상 매매)에서 **사용자 명칭은 "virtual"로 통일됐지만 내부 식별자는 `paper`로 남아 있다.** 혼동 방지를 위해 후속 정리를 고려할 만하다.
- 가상 매매의 Telegram(`--mode 1`) 배선, SafetyConfig CLI 노출, 영속화가 명시적 후속 과제로 남아 있다.

### 근거 문서
- `docs/public/overview.md` — 제품 정체성/기능 요약
- `docs/public/requirements.md` — MVP/후속 요구사항 정식 목록
- `docs/public/architecture.md` — 내부 구조·플로우
- `docs/public/release-notes.md` — 버전별 변경·로드맵
- `docs/superpowers/specs/2026-04-26-paper-trading-design.md` — 가상(모의) 매매 설계
- `docs/superpowers/plans/2026-04-26-paper-trading.md` — 가상 매매 구현 계획
