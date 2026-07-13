# smtm — Release Notes

버전별 주요 변경 사항과 앞으로의 방향을 정리한 문서입니다. 최신 버전부터 역순으로 기록하며, 구체적인 커밋 링크는 저장소 루트의 `RELEASE_NOTES.md`를 참고하세요.

- 최종 갱신일: 2026-07-13
- 현재 버전: **2.0.0** (텔레그램 전용, 배포 준비 중)

---

## Headline — v2.0.0

**"규칙 엔진에서 텔레그램 기반 AI 에이전트로."** 2.0.0은 smtm의 실행 모델을 **LLM 기반 오케스트레이션(2계층) + 규칙 기반 전략 실행 + 다중 안전장치**로 재구성하고, 제어 창구를 **텔레그램 채팅 하나**로 통일한 메이저 릴리스입니다.

핵심 변경점:

- **텔레그램 전용 제어** — CLI 대화형 모드가 제거되고 텔레그램 봇이 유일한 진입점(`python -m smtm --token <bot-token> --chatid <chat-id>`). 남은 CLI 플래그는 `--token` / `--chatid` / `--log` / `--version`뿐이며, 예산·통화·거래소·전략·주기는 **채팅 기반 프로파일/세션 설정**입니다.
- **가상거래 기본값** — 부팅 시 `default` 세션은 가상거래로 동작해 실주문이 없습니다. 실거래는 채팅으로 계좌를 등록한 뒤 세션을 만들어 시작합니다.
- **2계층 아키텍처** — `SystemOperator`(채팅 오케스트레이션 전용, 직접 매매 없음) + 세션별 `TradingOperator`(고정 주기 매매 루프: DataProvider → Strategy → SafetyGuard → Trader → Analyzer).
- **플러그블 전략** — `StrategyFactory`에 `BNH` / `RSI` / `SMA` / `LLM` 등록. `LLM` 전략(`StrategyLlm`)은 틱당 1회 구조화된 판단만 수행.
- **멀티세션 병렬 트레이딩** — `SessionManager`로 여러 (계정 × 심볼) 세션 동시 운용, 세션 도구와 `compare_performance` 성과 비교 제공.
- **멀티계정** — `AccountStore`는 자격증명의 환경변수 이름만 저장(원시 키 저장 금지), `AccountGuard` / `CompositeSafetyGuard`가 계정 수준 한도 강제.
- **DataProvider 카탈로그 대확장** — 뉴스·소셜·매크로·온체인·파생 지표 등 빌딩블록 약 26종, 텍스트형 데이터 혼합 지원.
- **벤더 독립 LLM 인터페이스** — `LlmClient` 추상화, Anthropic Claude(`ClaudeLlmClient`)가 첫 구현. OpenAI / Ollama는 로드맵.

---

## 버전별 변경

### v2.0.0 — 최신 (텔레그램 전용 2계층 LLM 아키텍처 + 멀티세션)

- **진입점 · 운영**
  - 텔레그램 봇이 유일한 진입점: `python -m smtm --token <bot-token> --chatid <chat-id>`(생략 시 환경변수 `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`). CLI 플래그는 `--token` / `--chatid` / `--log` / `--version`뿐이며, 설정은 전부 채팅으로 진행.
  - `default` 세션은 가상거래로 부팅(실주문 없음). 실거래는 채팅으로 계좌 등록(`register_account`, 환경변수 *이름*만 저장) → 프로파일 생성(`virtual: false` + `account`) → 세션 생성/시작.
  - 지정한 `chat_id` 메시지만 수용하고 그 외는 무시. `SMTM_LLM_API_KEY`가 없으면 부팅 중단.
- **신규 기능**
  - 2계층 아키텍처: `SystemOperator`(채팅 오케스트레이션) + 세션별 `TradingOperator`(고정 주기 매매 루프, 기본 60초). `execute_trade` 같은 직접 매매 도구는 없으며, 매매는 루프 안에서 Strategy 결정 → Trader 실행으로만 발생.
  - 전략 시스템: `StrategyFactory` + `BNH` / `RSI` / `SMA` / `LLM`. `StrategyLlm`은 틱당 1회 구조화 판단(`tool_choice` 강제 tool use).
  - 오케스트레이션·읽기·프로파일·계정·세션 Tool 20여 종: 전략 선택, 매매 시작/중지, 시장/포트폴리오/이력/성과 조회(세션 인식), 프로파일 CRUD, 계정 등록, 세션 생성/시작/중지/제거/비교. 텔레그램 컨트롤러가 이 전체 도구를 등록.
  - `ProfileStore`: 전략 × 거래소 × 심볼 × 예산 × 계정 프로파일을 `config/profiles/<name>.json`으로 관리(채팅으로 CRUD).
  - 멀티세션 병렬 트레이딩: `SessionManager`가 예산을 실제 계좌 잔고와 대조 검증, (계정, 심볼) 중복 할당 방지, 모니터 로그 세션 태깅.
  - 멀티계정: `AccountStore`(환경변수 이름만 저장, 중복 key-env 쌍·키 값 형태 env 이름 거부), Trader의 계정별 자격증명 env 이름 지원, `AccountGuard` / `CompositeSafetyGuard` 계정 수준 한도.
  - 가상거래(virtual trading): `default` 세션 기본값이며, 프로파일 `virtual` 설정으로 세션별 지정(구 `paper`는 호환 별칭).
  - DataProvider 빌딩블록 약 26종으로 확장(뉴스 RSS, Reddit, Fear & Greed, CoinGecko/CoinCap, 매크로, 온체인, Binance 파생 지표, Upbit 공지, 환율, Hacker News 등) + 텍스트형 데이터를 캔들과 혼합 제공.
  - `SafetyGuard`(1회 금액 10만 / 일일 20회 / 손실률 -20% 기본값) + `SystemMonitor`(독립 활동 기록) + 경량 `Analyzer`.
  - `LlmClient` 추상화와 `ClaudeLlmClient`(Anthropic) 첫 구현.
- **개선 · 버그 수정**
  - 텔레그램 토큰 누락 시 placeholder 부팅 대신 거부, 잘못된 chat-id를 토큰 문제로 오인하지 않고 실제 오류 노출, cp949 안전 부팅 메시지.
  - 완료된 거래만 일일 거래 횟수에 집계, 재설정 시에도 횟수 유지.
  - 세션 생성 실패 시 롤백, 세션별 거래 횟수 리포트 정확화, 한 세션 실패가 전체 중지를 막지 않도록 격리.
  - 가상거래 실패 체결 시 price/amount 0 처리, 부분 프로파일 적용 시 현재 설정 상속.
- **인프라 · 운영 · 문서**
  - E2E 테스트 재구축(`tests/e2e_tests/`): `FakeLlmClient` / `FakeDataProvider` / `SimulationTrader` 경계만 Fake, 채팅 매매·멀티세션 시나리오 검증.
  - 컨트롤러 종료 시 전체 세션 정리(텔레그램 autostart 없음).
  - 사용자 대상 README에서 LLM 에이전트를 "AI Agent"로 명칭 통일.
- **제거**
  - 룰 기반 아키텍처 전면 삭제: `Simulator` · `SimulationOperator` · `MassSimulator` · 데모 모드 · 구 `Operator` · 시뮬레이션/대량시뮬레이션 모드.
  - CLI 대화형 모드 및 설정 플래그 전부(`--mode` / `--budget` / `--currency` / `--exchange` / `--strategy` / `--profile` / `--term` / `--virtual` / `--config`), JSON `config/` 설정 파일.

> **Breaking Change**
> - **CLI 대화형 모드가 제거되어 텔레그램이 유일한 진입점**입니다. 실행을 `python -m smtm --token <bot-token> --chatid <chat-id>`로 갱신하세요. 설정 플래그(`--mode`, `--budget`, `--currency`, `--exchange`, `--strategy`, `--profile`, `--term`, `--virtual`, `--config`)는 모두 **채팅 기반 프로파일/세션 설정**으로 대체되었습니다.
> - **`default` 세션은 가상거래로 부팅**됩니다. 실거래가 필요하면 채팅으로 계좌를 등록한 뒤 세션을 만들어 시작하세요.
> - 시뮬레이션·대량시뮬레이션·데모 모드는 더 이상 없습니다. 실주문 없는 검증은 **가상거래**를 사용하세요.
> - `SMTM_LLM_API_KEY` 환경변수가 새로 필수입니다.

### v1.8.0

- `request_with_retry` 도입: 5xx / `ConnectionError`에 지수 백오프 2회 재시도.
- `BaseExchangeTrader` / `BaseDataProvider` 베이스 클래스 추출로 중복 제거, `TraderFactory` 도입(UPB / BTH 코드).
- 하드코딩된 API 자격증명 기본값 제거 및 호출 시점 검증 추가.
- `is_intialized` → `is_initialized` 오타 수정, 의존성 버전 고정 및 dev 의존성 분리.

### v1.7.1
- 문서·이미지 리뉴얼 및 리팩터링.

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

> v1.0 ~ v1.8 범위의 상세한 커밋 링크는 저장소 루트의 [`RELEASE_NOTES.md`](../../RELEASE_NOTES.md)를 참고하세요.

---

## Roadmap

향후 릴리스에서 다루려는 항목입니다(우선순위 · 일정 미확정, 순서 무관).

### 단기
- [ ] **채팅/프로파일에서 안전 한도 조정** — 1회 금액·일일 횟수·손실률 한도(`SafetyConfig`)를 프로파일 또는 채팅으로 세션별 조정.
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
- [x] **다중 계좌 / 멀티 거래소 동시 운용** — v2.0.0에서 멀티계정 · 멀티세션 병렬 트레이딩으로 제공.
- [ ] **세금 / 정산 리포트 자동 생성**.

---

## Breaking Change 이력

| 버전 | 변경 | 마이그레이션 |
|------|------|-------------|
| 2.0.0 | CLI 대화형 모드 제거, 텔레그램이 유일한 진입점 | 실행을 `python -m smtm --token <bot-token> --chatid <chat-id>`로 변경. 예산·통화·거래소·전략·주기는 채팅으로 프로파일/세션을 만들어 설정. |
| 2.0.0 | 설정용 CLI 플래그(`--mode` / `--budget` / `--currency` / `--exchange` / `--strategy` / `--profile` / `--term` / `--virtual` / `--config`) 제거 | 채팅 기반 프로파일/세션 설정으로 대체. `config/` JSON 설정 파일도 폐기. |
| 2.0.0 | `default` 세션 가상거래 기본값 | 실거래는 채팅으로 계좌 등록(`register_account`) → 프로파일(`virtual: false` + `account`) → 세션 생성/시작. |
| 2.0.0 | 시뮬레이터 · 매스시뮬레이터 · 데모 모드 제거 | 실주문 없는 검증은 가상거래를 사용. |
| 2.0.0 | `SMTM_LLM_API_KEY` 필수 환경변수 추가 | 실행 전 `.env` 또는 쉘에 Anthropic 키 설정. |
| 2.0.0 | 구 규칙 엔진 제거, 전략은 `Strategy` 인터페이스 + `StrategyFactory` 체계로 재편 | 커스텀 전략은 `Strategy` 인터페이스를 구현해 `StrategyFactory`에 등록. 전략 지식 문서는 `smtm/strategies/*.md` 참고. |
| 1.5.0 | `pytest` 기반 테스트 구조로 이관 | `tests/` 하위 구조 사용. unittest 호출 스크립트는 `pytest` 명령으로 대체. |

---

## 참고

- 아키텍처 배경 → [`architecture.md`](architecture.md)
- 사용 가이드 → [`user-guide.md`](user-guide.md)
- 기능 스펙 → [`requirements.md`](requirements.md)
