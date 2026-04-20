# smtm — Overview

> **"LLM이 판단하고, 규칙이 지키고, 사용자가 대화로 제어하는 자율 매매 시스템"**

smtm은 **LLM(대규모 언어 모델)이 시장을 분석하고 매매를 실행**하며, **규칙 기반 안전장치**가 거래 한도를 강제하고, **CLI 또는 텔레그램 채팅**으로 제어하는 오픈소스 암호화폐 자율매매 시스템입니다.

> 이 문서는 smtm의 정체성·해결 문제·핵심 가치·주요 기능·기술 스택을 한 페이지로 요약합니다. 실제 사용 방법은 [`user-guide.md`](user-guide.md), 내부 구조는 [`architecture.md`](architecture.md)를 참조하세요.

- 최종 갱신일: 2026-04-20
- 기준 버전: 1.7.1

---

## 1. 무엇을 해결하는가

**문제**: 전통적인 규칙 기반 자동매매는 조건 분기를 일일이 설계해야 하고, 시장 상황 변화에 따라 유지보수 비용이 빠르게 커집니다. 또한 매매 로직과 사용자 인터페이스가 강하게 결합돼, "분석 결과 보여줘", "지금 매수해" 같은 자연어 제어가 어렵습니다.

**해결**
- **판단은 LLM에게 위임**: LLM이 시장 데이터를 읽고, 필요할 때만 매매 Tool을 호출하여 주문을 실행합니다.
- **안전은 코드가 강제**: `SafetyGuard`가 Tool 실행 직전에 한도(1회 거래 금액, 일일 거래 횟수, 누적 손실률)를 검사하며 LLM이 우회할 수 없습니다.
- **제어는 자연어로**: CLI 또는 텔레그램 메신저에서 한국어·영어 메시지를 보내면 LLM이 해석하고 도구를 호출합니다.

---

## 2. 핵심 가치

- **LLM 자율성**: 시장 분석·매매 판단·포트폴리오 관리·성과 확인을 LLM이 Tool use로 직접 수행합니다.
- **규칙 기반 안전장치**: LLM의 판단과 별개로 하드 리밋이 항상 동작합니다. 한도 초과 시 해당 거래는 거부되고 사유가 기록됩니다.
- **벤더 독립 LLM 인터페이스**: `LlmClient` 추상 계층이 있고 현재 Anthropic Claude가 구현돼 있습니다. OpenAI / Ollama 어댑터는 예정 항목입니다.
- **관찰 가능성**: `SystemMonitor`가 LLM 호출, Tool 실행, 시장 데이터, 거래 요청·결과, 안전장치 차단 이벤트까지 모두 구조화된 로그로 남깁니다.
- **대화형 온보딩**: "BTC 시장 분석해줘"처럼 평소 말투로 상호작용하며, `start` / `stop` 같은 명령으로 자동 매매 루프를 토글합니다.

---

## 3. 주요 기능

### 3.1 매매 오케스트레이션
- 주기적 틱(기본 60초)마다 LLM에 시장 컨텍스트를 전달해 분석·매매 판단을 요청
- LLM이 자율적으로 도구 호출 → 시장 데이터 조회 → 필요 시 주문 실행
- 사용자 메시지도 동일한 대화 세션에 합류해 상호 개입 가능

### 3.2 Tool 세트 (LLM이 호출)
| Tool 이름 | 설명 |
|-----------|------|
| `get_market_data` | 지정 통화의 최근 OHLCV 캔들 조회 |
| `execute_trade` | 매수/매도 주문 실행 (SafetyGuard 통과 시에만) |
| `get_portfolio` | 현금·자산·현재가 조회 |
| `get_trade_history` | 최근 N건 거래 이력 조회 |
| `get_performance` | 수익률, 총 거래 횟수, 현재 포트폴리오 가치 |

### 3.3 안전 가드레일
- `max_trade_amount` — 1회 최대 거래 금액 (기본 100,000 KRW)
- `max_daily_trades` — 일일 최대 거래 횟수 (기본 20)
- `max_loss_ratio` — 누적 손실 한도 (기본 -20%)
- 위반 시 해당 Tool 호출은 거부되고 LLM에게 사유가 전달됩니다.

### 3.4 제어 채널
- **CLI 인터랙티브 모드 (`--mode 0`)** — 터미널에서 메시지를 주고받음
- **텔레그램 챗봇 모드 (`--mode 1`)** — 텔레그램 메신저로 원격 제어
- **Jupyter Notebook (`JptController`)** — 노트북 셀에서 직접 `operator.chat()` 호출

### 3.5 데이터 / 거래소 연동
- **DataProvider**: Upbit, Bithumb, Binance, Upbit+Binance 병합 4종
- **Trader**: Upbit, Bithumb 2종 (실주문 가능)
- 동일 코드(`--exchange UPB`/`BTH` 등)로 데이터 소스와 거래소를 함께 선택

---

## 4. 기술 스택

| 레이어 | 구성 |
|--------|------|
| 언어 / 런타임 | Python 3.9+ |
| LLM 벤더 | Anthropic Claude (`claude-sonnet-4-20250514`) — SDK: `anthropic>=0.25` |
| 거래소 API | Upbit, Bithumb, Binance REST |
| 인증 | PyJWT (거래소 서명), 환경변수 기반 API 키 |
| HTTP | `requests` |
| 설정 | `python-dotenv` |
| 제어 채널 | stdin(CLI), python-telegram-bot 계열(텔레그램), ipykernel(Jupyter) |
| 로그 / 모니터링 | `logging` + `RotatingFileHandler` (파일 로그), `SystemMonitor` (인메모리 구조화 로그) |
| 테스트 | pytest (unit / e2e / integration) |

---

## 5. 차별점 요약

- **LLM = 의사결정자, 코드 = 안전망**: "하라는 대로만 하는" 챗봇이 아니라 안전장치가 있는 에이전트입니다.
- **같은 대화 세션, 두 가지 호출자**: 주기적 틱과 사용자 메시지가 동일한 대화 히스토리에 섞여 문맥을 공유합니다.
- **도구 레벨 감사**: `SystemMonitor`가 LLM 응답·Tool 입력/출력·SafetyGuard 결정까지 추적합니다.
- **플러그형 거래소**: `DataProviderFactory` / `TraderFactory`로 새로운 거래소를 코드 한 개 추가로 연결할 수 있습니다.

---

## 6. 다음으로 볼 문서

- 실제 사용법은 [`user-guide.md`](user-guide.md)
- 자주 막히는 지점·설정 상세는 [`faq.md`](faq.md)
- 기능 스펙 전체 목록은 [`requirements.md`](requirements.md)
- 시스템 구조·플로우·확장 포인트는 [`architecture.md`](architecture.md)
- 버전별 변경·로드맵은 [`release-notes.md`](release-notes.md)
- 레거시 구조·옛 모드 관련 상세는 `docs/wiki/` 내부 문서
