# smtm — Release Notes

버전별 주요 변경 사항과 앞으로의 방향을 정리한 문서입니다. 최신 버전부터 역순으로 기록하며, 구체적인 커밋 링크는 저장소 루트의 `RELEASE_NOTES.md`를 참고하세요.

- 최종 갱신일: 2026-04-20
- 현재 버전: **1.7.1**

---

## Headline — v1.7.x

**"규칙 엔진에서 LLM 에이전트로."** 1.7.x는 smtm의 실행 모델을 **LLM 기반 자율 매매 + 규칙 기반 안전장치**로 재구성한 메이저 변경입니다.

핵심 변경점:

- **`LlmOperator` 도입** — 주기 틱·사용자 메시지를 동일한 대화 세션에서 다루는 새 오케스트레이터.
- **Tool use 5종** — `get_market_data`, `execute_trade`, `get_portfolio`, `get_trade_history`, `get_performance`. 모두 LLM이 자율 호출.
- **`SafetyGuard` 분리** — 거래 Tool 실행 직전에 1회 금액·일일 횟수·누적 손실률을 강제. LLM이 우회 불가.
- **`SystemMonitor` 도입** — LLM 호출·Tool 실행·시장 데이터·차단 이벤트·포트폴리오 스냅샷을 구조화 로그로 수집(현재는 인메모리).
- **벤더 독립 LLM 인터페이스** — `LlmClient` 추상화, Anthropic Claude가 첫 구현. OpenAI / Ollama는 로드맵.
- **CLI 모드 단순화** — 과거의 시뮬레이션·매스 시뮬레이션 모드가 제거되고 `--mode 0`(CLI 채팅) / `--mode 1`(Telegram)만 남음.
- **E2E 테스트 프레임워크** — `FakeLlmClient` / `FakeTrader` / `FakeDataProvider`를 활용해 외부 API 없이 전체 플로우 검증.

---

## 버전별 변경

### v1.7.1 — 최신 (LLM 기반 아키텍처)

- **신규 기능**
  - `LlmOperator` 도입: 상태 머신(ready / running / stopped) + 주기 타이머 + 대화 이력 관리.
  - `ToolRouter`와 Tool 5종(`get_market_data`, `execute_trade`, `get_portfolio`, `get_trade_history`, `get_performance`).
  - `SafetyGuard` + `SafetyConfig`: 1회 금액(10만), 일일 횟수(20), 누적 손실률(-20%) 기본값.
  - `SystemMonitor`: 7종 인메모리 로그(market_data · tool_call · trade_request · trade_result · llm_interaction · safety_event · snapshots).
  - `ClaudeLlmClient`: Anthropic Claude 어댑터(`claude-sonnet-4-20250514`).
- **개선**
  - 대화 이력 최대 크기 상한(`max_conversation_turns * 2`) 추가로 장시간 구동 시 메모리·토큰 폭증 방지.
  - Strategy 지식(`sma_crossover.md`, `rsi_strategy.md`, `buy_and_hold.md`)을 시스템 프롬프트에 주입.
  - DataProvider 계약을 다형 데이터 리스트로 명시화: 캔들 외에 `news`·`notice` 같은 텍스트 타입을 같은 리스트에 혼합 가능. 실구현으로 `NewsDataProvider`와 `UpbitNewsDataProvider`(`CODE=UPN`)를 추가하고 `MarketDataTool` description을 다중 타입 반영해 확장.
- **인프라 · 운영**
  - E2E 테스트 도입(`tests/e2e_tests/`): 외부 API 없이 채팅 → Tool → 거래 → 결과 전 구간 검증.
  - 루트 README와 `README-ko-kr.md`를 LLM 아키텍처 기준으로 재작성.
- **제거**
  - 시뮬레이터·매스 시뮬레이터·레거시 설정 생성 모드(`--mode 2`~`5`).
  - 레거시 Analyzer 기반 규칙 엔진(지식 문서로 이관).

> **Breaking Change**
> - `--mode 2` 이상은 동작하지 않습니다. 과거 스크립트·Cron·문서를 `--mode 0` 또는 `--mode 1`로 갱신해야 합니다.
> - `SMTM_LLM_API_KEY` 환경변수가 새로 필수입니다.

### v1.6.2
- `setup.py`, `setup.cfg` 버그 수정.

### v1.6.1
- README 이미지 링크 수정.

### v1.6.0
- **Telegram Controller 다국어 지원**: 영어 메시지 추가.

### v1.5.0
- `alert_callback` 인터페이스 추가: 코어 → 컨트롤러 알림 전송.
- `StrategyHey` 추가: 이동평균 붕괴 / 변동성 돌파 이벤트 알림.
- `pytest` 전면 도입, `tests/`로 단위·통합 테스트 통합.
- 경고 문구 제거 및 코드 정리.

### v1.4.0
- `Analyzer` 라인 콜백 추가.
- `BinanceDataProvider` 추가.
- `StrategySmaDualMl` 추가.

### v1.3.0
- 전역 인터벌 설정을 위한 `Config` 모듈 도입.

### v1.2.0
- 시뮬레이션 성능 3× 향상.
- `StrategySmaMl` 추가.

### v1.1.1
- `StrategyFactory` 도입.
- 로그 디렉터리 관리 개선.

### v1.1.0
- 데모 기능 추가.
- RSI 전략 추가.
- 그래프 주석 기능 추가.

### v1.0.0
- 최초 릴리스.
- 시뮬레이션, 매스 시뮬레이션, 실거래, Telegram, Jupyter 모드 제공.

> v1.0 ~ v1.6 범위의 상세한 커밋 링크는 저장소 루트의 [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md)를 참고하세요.

---

## Roadmap

향후 릴리스에서 다루려는 항목입니다(우선순위 · 일정 미확정, 순서 무관).

### 단기
- [ ] **SafetyConfig CLI 노출** — `--max-trade-amount`, `--max-daily-trades`, `--max-loss-ratio`로 하드 리밋을 CLI에서 조정.
- [ ] **Binance Trader 구현** — 현재는 데이터만 가능한 `BNC` 코드를 실주문까지 확장.
- [ ] **SystemMonitor 영속화** — JSONL 또는 SQLite로 디스크 저장, 재시작 복원.

### 중기
- [ ] **OpenAI 어댑터**(`LlmClient` 구현).
- [ ] **Ollama / 로컬 LLM 어댑터** — 자체 호스팅 환경 지원.
- [ ] **Prompt 캐싱 활용** — 시스템 프롬프트·전략 지식 문서에 Anthropic prompt caching 적용으로 비용 절감.
- [ ] **운영용 systemd 유닛 / Docker 이미지** 공식 제공.
- [ ] **Multimodal tool_result** — 이미지·차트 캡처를 Tool 결과에 직접 태워 보내는 경로(ToolResult 스키마 + ClaudeLlmClient content 블록 처리 확장).

### 장기
- [ ] **웹 대시보드** — SystemMonitor 로그와 포트폴리오 스냅샷을 시각화하는 웹 UI.
- [ ] **다중 계좌 / 멀티 거래소 동시 운용**.
- [ ] **세금 / 정산 리포트 자동 생성**.

---

## Breaking Change 이력

| 버전 | 변경 | 마이그레이션 |
|------|------|-------------|
| 1.7.0 | 시뮬레이터·매스시뮬레이터·설정 생성 모드(`--mode 2`~`5`) 제거 | 해당 모드를 사용하던 스크립트는 `--mode 0` 또는 `--mode 1`로 대체. 시뮬레이션이 필요하면 `tests/e2e_tests/` 구조(Fake 컴포넌트)를 응용. |
| 1.7.0 | `SMTM_LLM_API_KEY` 필수 환경변수 추가 | CLI / Telegram 실행 전 `.env` 또는 쉘에 Anthropic 키 설정. |
| 1.7.0 | Analyzer 기반 규칙 엔진 제거, Strategy 지식이 markdown 문서로 이관 | 커스텀 Strategy 클래스가 있었다면 `smtm/strategies/*.md` 포맷으로 내용을 옮기거나, 새 Tool로 구현. |
| 1.5.0 | `pytest` 기반 테스트 구조로 이관 | `tests/` 하위 구조 사용. unittest 호출 스크립트는 `pytest` 명령으로 대체. |

---

## 참고

- 아키텍처 배경 → [`architecture.md`](architecture.md)
- 사용 가이드 → [`user-guide.md`](user-guide.md)
- 기능 스펙 → [`requirements.md`](requirements.md)
