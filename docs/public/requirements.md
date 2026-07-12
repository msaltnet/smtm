# smtm — Requirements

smtm이 제공해야 하는 기능을 영역별로 정리한 문서입니다. `[MVP]`는 현재 1.7.x에서 이미 충족 중인 범위, `[후속]`은 향후 릴리스에서 다룰 항목입니다.

- 최종 갱신일: 2026-04-20
- 기준 버전: 1.7.1

---

## 1. 범위

- **대상**: 개인 트레이더가 **단일 호스트**에서 소액(기본 예산 50만 원 수준) 암호화폐 자동매매를 돌릴 때.
- **포함**: LLM 기반 매매 오케스트레이션, 안전장치, 시장 데이터 / 거래소 연동, 대화형 제어(Telegram · Jupyter), 관찰 가능성(로그).
- **미포함**: 멀티 테넌시, 웹 대시보드, 클라우드형 분산 실행, 세금/정산 리포팅.

---

## 2. 영역별 요구사항

### 2.1 대화 인터페이스

- **[MVP] R-CHAT-01** — 유일한 실행 진입점은 텔레그램 챗봇이다. 프로세스는 텔레그램으로 사용자 메시지를 받고 LLM 응답을 텔레그램으로 회신해야 한다.
- **[MVP] R-CHAT-02** — `start` / `stop` 명령은 자동 매매 타이머를 on/off 해야 하며, 대화 세션 자체는 유지돼야 한다.
- **[MVP] R-CHAT-03** — SIGINT / SIGTERM 수신 시 프로세스를 안전하게 종료해야 한다(진행 중 작업은 완료까지 대기).
- **[MVP] R-CHAT-04** — Telegram Bot은 지정된 `chat_id`의 메시지만 수용하고, 그 외 발신자는 무시해야 한다.
- **[MVP] R-CHAT-05** — Jupyter에서는 `JptController`를 통해 동일한 오퍼레이터를 노트북 셀에서 사용할 수 있어야 한다.
- **[후속] R-CHAT-06** — 웹 기반 대화 콘솔 제공.

### 2.2 매매 오케스트레이션

- **[MVP] R-ORCH-01** — `LlmOperator`는 "ready" / "running" / "stopped" 세 상태를 가져야 한다.
- **[MVP] R-ORCH-02** — 자동 매매 중에는 세션의 `term` 설정값 주기(기본 60초)마다 시장 컨텍스트를 담아 매매 판단을 수행해야 한다.
- **[MVP] R-ORCH-03** — 사용자 메시지와 주기 틱은 **동일한 대화 이력**에 합류해 문맥이 공유돼야 한다.
- **[MVP] R-ORCH-04** — Tool use 응답이 오면 해당 Tool을 실행한 결과를 `tool_result`로 이력에 기록하고, LLM이 `tool_calls`가 없는 응답을 반환할 때까지 루프를 반복해야 한다.
- **[MVP] R-ORCH-05** — 대화 이력은 `max_conversation_turns * 2`(기본 100개) 메시지까지 유지하고 초과분은 오래된 것부터 제거해야 한다.
- **[MVP] R-ORCH-06** — LLM 응답의 텍스트 부분은 사용자에게 전달되고, Tool 호출 부분은 내부 루프에서 소비된다.
- **[후속] R-ORCH-07** — 대화 이력·상태를 디스크에 영속 저장하고, 프로세스 재시작 시 복원한다.

### 2.3 Tool 세트

- **[MVP] R-TOOL-01** — 다음 5개 Tool은 기본으로 등록돼야 한다: `get_market_data`, `execute_trade`, `get_portfolio`, `get_trade_history`, `get_performance`.
- **[MVP] R-TOOL-02** — `execute_trade` 입력 스키마는 `{action: "buy"|"sell", currency, price, amount}`를 받는다.
- **[MVP] R-TOOL-03** — `get_market_data` 입력 스키마는 조회 대상 `session`(세션 이름, 기본 `default`)을 받는다 — 통화는 세션 프로파일에 귀속된다.
- **[MVP] R-TOOL-04** — 각 Tool의 `input_schema`는 JSON Schema 형태로 LLM에 그대로 노출된다.
- **[MVP] R-TOOL-05** — Tool 실행 결과는 `ToolResult.to_dict()`으로 직렬화 가능한 dict여야 하며, 실패 시 `success=False`와 `error` 메시지를 담는다.
- **[후속] R-TOOL-06** — Tool 추가·비활성화를 코드 변경 없이 설정 파일로 할 수 있게 한다.

### 2.4 안전 가드레일

- **[MVP] R-SAFE-01** — `SafetyGuard`는 `execute_trade` Tool 실행 **직전**에 호출돼야 하며, LLM 응답만으로 우회되지 않아야 한다.
- **[MVP] R-SAFE-02** — 다음 한도를 검증한다: 1회 거래 금액, 일일 거래 횟수, 누적 손실률.
- **[MVP] R-SAFE-03** — 기본값은 `max_trade_amount=100_000`, `max_daily_trades=20`, `max_loss_ratio=-0.20`, `initial_budget`은 세션의 `budget` 설정값이다.
- **[MVP] R-SAFE-04** — 한도 위반 시 Tool 결과는 실패로 반환되고, 차단 사유는 사람이 읽을 수 있는 문자열("1회 최대 거래금액 초과 (…)")로 제공돼야 한다.
- **[MVP] R-SAFE-05** — 모든 차단 이벤트는 `SystemMonitor.safety_event_log`에 기록돼야 한다.
- **[MVP] R-SAFE-06** — 날짜가 바뀌면 일일 거래 카운터는 자동 리셋돼야 한다.
- **[MVP] R-SAFE-07** — 한도는 프로파일의 `safety` 설정값으로 세션별 조정이 가능해야 한다.
- **[후속] R-SAFE-08** — 실시간 가격 급변(슬리피지, 호가 스프레드) 보호.

### 2.5 시장 데이터 (DataProvider)

- **[MVP] R-DATA-01** — `DataProvider`는 `get_info()`를 통해 `type` 필드로 구분되는 타입별 딕셔너리를 리스트로 반환한다. 주 거래 캔들은 반드시 `type='primary_candle'` 형태로 포함돼야 한다.
- **[MVP] R-DATA-02** — 다음 코드를 지원한다: `UPB`(Upbit), `BTH`(Bithumb), `BNC`(Binance), `UBD`(Upbit+Binance 병합), `UPN`(Upbit+뉴스 RSS).
- **[MVP] R-DATA-03** — `DataProviderFactory`는 `CODE` 속성으로 공급자를 식별한다.
- **[MVP] R-DATA-04** — 캔들 간격은 `Config.candle_interval`(기본 60초)로 설정된다.
- **[MVP] R-DATA-05** — 텍스트형 데이터(`type='news'` 등) 역시 같은 리스트에 섞어 반환할 수 있어야 하며, 네트워크 실패나 파싱 오류는 빈 리스트로 흡수해 매매 루프를 중단시키지 않아야 한다.
- **[후속] R-DATA-06** — 실시간 WebSocket 기반 틱 피드 지원.
- **[후속] R-DATA-07** — 이미지·차트 캡처 등 multimodal 데이터 블록 지원(Tool 결과 경로 확장 포함).

### 2.6 거래소 (Trader)

- **[MVP] R-EXEC-01** — `Trader`는 `send_request(request)`, `get_account_info()` 계약을 제공해야 한다.
- **[MVP] R-EXEC-02** — 현재 지원 거래소: `UPB`(Upbit), `BTH`(Bithumb).
- **[MVP] R-EXEC-03** — 거래소 API 키는 환경변수로만 받고 로그에는 절대 남지 않아야 한다.
- **[MVP] R-EXEC-04** — Trader 생성 시 `commission_ratio`가 주입 가능해야 하며, 기본 0.0005(0.05%).
- **[후속] R-EXEC-05** — Binance Trader 구현 추가.
- **[후속] R-EXEC-06** — 주문 실행 후 체결 확인 재시도 정책(재연결, 타임아웃 재시도).

### 2.7 관찰 가능성 (SystemMonitor / Log)

- **[MVP] R-OBS-01** — `SystemMonitor`는 market_data, trade_request, trade_result, tool_call, llm_interaction, safety_event, snapshot 7종 로그를 분리 관리해야 한다.
- **[MVP] R-OBS-02** — 각 로그 항목은 ISO 8601 타임스탬프를 포함해야 한다.
- **[MVP] R-OBS-03** — LLM 호출 시 input/output 토큰 수를 수집하고, `get_llm_usage()`로 합계를 조회할 수 있어야 한다.
- **[MVP] R-OBS-04** — 파일 로그는 `log/smtm.log`에 남으며 2MB × 10개 롤링이다.
- **[MVP] R-OBS-05** — 거래소 API 키/토큰은 파일 로그에 절대 노출되지 않아야 한다.
- **[후속] R-OBS-06** — SystemMonitor 로그를 디스크(JSONL / SQLite)에 영속 저장.
- **[후속] R-OBS-07** — 메트릭 export(Prometheus 등) 지원.

### 2.8 LLM 벤더 추상화

- **[MVP] R-LLM-01** — `LlmClient` 추상 계층은 `create_message(system_prompt, messages, tools) -> LlmResponse` 계약을 갖는다.
- **[MVP] R-LLM-02** — 응답은 `LlmResponse(text, tool_calls, stop_reason, usage)`로 정규화된다.
- **[MVP] R-LLM-03** — Claude 어댑터(`ClaudeLlmClient`)가 기본 구현으로 포함된다.
- **[후속] R-LLM-04** — OpenAI 어댑터.
- **[후속] R-LLM-05** — Ollama(로컬 LLM) 어댑터.

### 2.9 설정 / 실행

- **[MVP] R-CFG-01** — CLI는 `--token`, `--chatid`, `--log`, `--version` 네 개 옵션만 지원한다. 매매 관련 설정(예산·통화·거래소·주기·전략·가상거래 여부)은 명령행이 아니라 채팅으로 만드는 프로파일/세션 설정값으로 관리한다.
- **[MVP] R-CFG-02** — 민감 정보는 환경변수 또는 `.env`로만 받는다(코드·커밋 금지). 텔레그램 자격증명은 `--token` / `--chatid` 또는 `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`로 주입한다.
- **[MVP] R-CFG-03** — 사용 가능한 텔레그램 토큰이 없으면 안내 메시지("Please check your telegram chat-bot token")를 출력하고 정상 종료한다(가짜 토큰으로 기동하지 않는다).
- **[MVP] R-CFG-05** — 기동 시 생성되는 `default` 세션은 가상거래여야 한다. 실거래는 사용자가 채팅으로 계좌를 등록하고, `virtual: false` + `account`를 가진 프로파일로 세션을 만들어 시작해야만 가능하다.
- **[후속] R-CFG-04** — 설정 파일(YAML/TOML) 지원.

---

## 3. 비기능 요구

### 3.1 안정성
- 한 번의 LLM / 거래소 호출 실패가 전체 프로세스를 종료시키지 않아야 한다. 해당 틱만 실패로 표시하고 다음 틱에 재시도한다.
- 프로세스 종료 시그널(SIGINT/SIGTERM) 수신 시 진행 중 Tool은 완료 후 종료한다.

### 3.2 보안
- API 키는 환경변수로만 전달되며 로그·예외·표준 출력에 노출되지 않아야 한다.
- 텔레그램은 지정 `chat_id` 외 발신자 메시지를 수신하지 않는다.
- 커밋 포함 금지: `.env`, 개인 API 키, 테스트용 토큰.

### 3.3 성능
- 자동 매매 틱 1회당 LLM 호출은 **Tool use 루프 포함 10초 이내**에 마무리되는 것을 목표로 한다(네트워크 RTT 포함).
- 메모리 사용량은 장시간(24h+) 구동 시에도 단조 증가하지 않아야 한다(대화 이력·SystemMonitor 로그는 상한이 있어야 한다).

### 3.4 테스트 가능성
- LLM, 거래소, 시장 데이터 모두 Fake 구현으로 대체 가능해야 하며, 내부 컴포넌트는 실제 코드로 통합 테스트가 가능해야 한다(현 E2E 구조).
- 테스트 분류는 `tests/unit_tests`, `tests/e2e_tests`, `tests/integration_tests`로 분리한다.

### 3.5 호환성
- Python 3.9+ 을 지원 목표 버전으로 유지한다.
- OS 독립(Windows / macOS / Linux 공통). 경로·로그 회전에서 플랫폼 가정을 두지 않는다.

---

## 4. 점검 체크리스트 (QA)

### 4.1 설정
- [ ] `SMTM_LLM_API_KEY` 누락 시 적절한 안내 후 종료되는가
- [ ] 텔레그램 토큰 누락/플레이스홀더 시 안내 메시지 출력 후 정상 종료되는가
- [ ] 기동 시 `default` 세션이 가상거래로 뜨는가 (실주문이 나가지 않는가)
- [ ] 거래소 키 누락 시 실거래 세션 생성/주문에서 명확한 실패 메시지가 반환되는가
- [ ] `exchange` 설정값을 `BNC`처럼 Trader가 없는 코드로 지정하면 안전하게 거부되는가
- [ ] `--version`이 현재 `__version__`과 일치하는가

### 4.2 대화
- [ ] 텔레그램에서 `start` → 60초 주기로 매매 루프 로그가 확인되는가
- [ ] `stop` 입력 시 타이머가 멈추고 이후 사용자 메시지에는 응답하는가
- [ ] 50턴 넘게 대화해도 메모리가 폭증하지 않는가
- [ ] 텔레그램 봇이 다른 사용자 메시지에는 반응하지 않는가

### 4.3 안전장치
- [ ] 10만 원을 초과하는 `execute_trade` 시도 시 차단되고 사유가 돌아오는가
- [ ] 하루 21번째 거래 시도 시 차단되는가 (하루 경계에서 리셋되는가)
- [ ] 누적 손실이 -20%에 도달하면 이후 거래가 모두 차단되는가
- [ ] 모든 차단이 `safety_event_log`에 기록되는가

### 4.4 관찰 가능성
- [ ] `log/smtm.log`가 2MB 근방에서 회전되고 10개까지 남는가
- [ ] `get_llm_usage()`가 누적 토큰을 정확히 반환하는가
- [ ] 파일 로그에 API 키가 섞이지 않는가

---

## 5. 변경 이력

요구사항 변경은 [`release-notes.md`](release-notes.md)에서 버전별로 추적합니다.
