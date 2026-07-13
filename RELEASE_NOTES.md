## v2.0.0

Major rewrite: the rule-based simulation/trading engine is replaced by an AI-Agent-powered two-layer trading system that is driven **entirely through Telegram chat**. It adds pluggable strategies, multi-account and multi-session parallel trading, and virtual trading that is on by default.

### Breaking Changes
- **Rule-based trading architecture removed**: `Simulator`, `SimulationOperator`, `MassSimulator`, demo mode, the legacy `Operator`, and the simulation / mass-simulation modes are all deleted. To validate a strategy without real orders, use the new virtual trading mode instead.
  - https://github.com/msaltnet/smtm/commit/d46f60c501d5119c67733209b4d030ca0ab8ce19
  - https://github.com/msaltnet/smtm/commit/c4be87024828610dcae10214b16662cdd7c58771
- **CLI interactive mode removed — Telegram is the only entry point**: the interactive CLI controller is gone. smtm now launches solely as a Telegram bot (`python -m smtm --token <bot-token> --chatid <chat-id>`, or via the `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` environment variables). The only CLI flags left are `--token`, `--chatid`, `--log`, and `--version`; every configuration flag — `--mode`, `--budget`, `--currency`, `--exchange`, `--strategy`, `--profile`, `--term`, `--virtual`, `--config` — has been removed. Budget, currency, exchange, strategy, and interval are now **chat-driven profile / session settings**: you ask the agent in chat to create or edit a profile and to create and start sessions.
  - https://github.com/msaltnet/smtm/commit/cd359d4ece6a75c8f14204864a98d49146d81ea0
- **Virtual trading is the default session's default; real trading is opt-in via chat**: on boot the `default` session runs in virtual mode, so no real orders are ever sent. To trade for real, register an account in chat with `register_account` (which stores only the credential env-var *name*), create a profile with `virtual: false` and an `account`, then `create_session` and `start_session`.
  - https://github.com/msaltnet/smtm/commit/0ae432782b377b82c76ad0caa3cf45b59212024b
- **`SMTM_LLM_API_KEY` environment variable is now required**: the chat agent and the `LLM` strategy run on Anthropic Claude through the vendor-independent `LlmClient` abstraction, and boot aborts if the key is missing. `ClaudeLlmClient` is the first implementation, with forced tool use via `tool_choice`.
  - https://github.com/msaltnet/smtm/commit/a049670d67354b7250975a206719147691c606a3
  - https://github.com/msaltnet/smtm/commit/45d8af713993a8dd2749bc16fc36e115baddece9
  - https://github.com/msaltnet/smtm/commit/8b87a83094e71e2a7ce37acfba5bd4d9a4b5fcb6

### New Features
- **Two-layer architecture: SystemOperator + TradingOperator**: `SystemOperator` is a chat-only orchestration agent — it registers accounts, manages profiles, and creates/starts/stops/compares trading sessions via tools, but never places orders itself (there is no `execute_trade` tool). Each session runs its own `TradingOperator`, a fixed-interval (default 60s) loop of DataProvider → Strategy → SafetyGuard → Trader → Analyzer.
  - https://github.com/msaltnet/smtm/commit/892eceadb8b3c03ee151a2adf1f574495bce4f04
  - https://github.com/msaltnet/smtm/commit/80f9de1427077bb0397580a53bc8f493d6ba82d2
  - https://github.com/msaltnet/smtm/commit/f0cb67d4dbbaac5903c9b86436ed379209b83c7d
  - https://github.com/msaltnet/smtm/commit/7be519e69cefca0c5ad6e1479c2b7c9059637da6
- **Pluggable strategies with StrategyFactory**: the `Strategy` interface is back, with `BNH` (buy-and-hold), `RSI`, and `SMA` strategies registered in a `StrategyFactory` registry. Strategies are selected via chat.
  - https://github.com/msaltnet/smtm/commit/3dde9573a574af6806c1d75163fbd93b78c17854
  - https://github.com/msaltnet/smtm/commit/e63992aa11bf7014ffc9da55a1b59107933ad90e
  - https://github.com/msaltnet/smtm/commit/4fe6896b465f844d318cc9cac1c7d3e5e67013fb
  - https://github.com/msaltnet/smtm/commit/380f815d423a50ea06b22ddf457298bc455f74d3
- **StrategyLlm — one structured LLM decision per tick**: the `LLM` strategy asks the model for a single structured buy/sell/hold decision on each tick (forced tool use), keeping LLM usage inside the trading loop bounded and predictable.
  - https://github.com/msaltnet/smtm/commit/7fe587d3da58a06d1e5385f3d88df5a4d4130335
- **Safety and monitoring layer**: `SafetyGuard` validates every order before execution (defaults: max trade amount 100,000 / max daily trades 20 / max loss ratio -20%), `SystemMonitor` independently records market data, trade requests/results, safety events, and LLM usage, and a lightweight `Analyzer` produces performance reports on top of it.
  - https://github.com/msaltnet/smtm/commit/eb4d1b262753dda5f228cc755d5356c7cf0a4d82
  - https://github.com/msaltnet/smtm/commit/385572d039ecc7d29d9b1974cbb8bd26483af720
  - https://github.com/msaltnet/smtm/commit/c7433fd1a680c8503302f4c9f85863d6efe4cb97
  - https://github.com/msaltnet/smtm/commit/dd15524a3aa30a8fd6f555963faff2f5bfd3a701
- **Account profiles (ProfileStore + CRUD tools)**: a profile (`config/profiles/<name>.json`) captures strategy × exchange × symbol × budget × account. Profiles are managed entirely in chat (`list/describe/create/update/delete/switch_profile`).
  - https://github.com/msaltnet/smtm/commit/b471a05f8fee3f23b531c42c50dfd3dfd7b7ac3a
  - https://github.com/msaltnet/smtm/commit/448747cb1e3c8f9ba2ddf07f5a134313c8d20a44
- **Multi-session parallel trading**: `SessionManager` runs multiple trading sessions concurrently, validating budgets against real account balances and preventing duplicate (account, symbol) allocations. Session tools (`create_session`, `start_session`, `stop_session`, `remove_session`, `list_sessions`, `compare_performance`) let the agent operate and compare sessions from chat, monitor logs are tagged with the session name, and controllers shut all sessions down cleanly on exit (no Telegram autostart).
  - https://github.com/msaltnet/smtm/commit/13628fba926253c7f7452b1e5cb0334b5d6e3821
  - https://github.com/msaltnet/smtm/commit/afd5e90dcef35205136e4b3c7fd1c64b4bed195b
  - https://github.com/msaltnet/smtm/commit/66886cff49f58ff148a0745d0e1e8b1bca396196
  - https://github.com/msaltnet/smtm/commit/aa278ba643e53172b69c9d818fd487c954ac31ad
  - https://github.com/msaltnet/smtm/commit/18cdc4684296d0de9a6a19277505984433df0d5e
- **Multi-account support with env-name-only credentials**: `AccountStore` stores only environment-variable *names* for exchange credentials (raw keys are never persisted), rejecting duplicate key-env pairs and key-value-shaped env names. Account tools (`register_account`, `list_accounts`, `delete_account`) manage accounts from chat, exchange traders accept per-account credential env names, and `AccountGuard` + `CompositeSafetyGuard` enforce account-level limits across all sessions sharing one account.
  - https://github.com/msaltnet/smtm/commit/11d9491cbb77ac2203b96c2adeba32c41b339d0b
  - https://github.com/msaltnet/smtm/commit/03dd452770cf9f49ef450b9f88a5c5bfedba78f7
  - https://github.com/msaltnet/smtm/commit/71470f08619f0cdb091cbbfa85d810ab611777fc
  - https://github.com/msaltnet/smtm/commit/9dae19d8372e394b6b90b6e2a1caa64b0500861e
  - https://github.com/msaltnet/smtm/commit/7425d9490d6b392178db19f8a3a24238f9ca26f1
- **Profile and session tools available in Telegram**: the Telegram controller now registers the full account/profile/session toolset (previously orchestration-only), so accounts, profiles, and parallel sessions can all be managed directly from Telegram chat.
  - https://github.com/msaltnet/smtm/commit/0ae432782b377b82c76ad0caa3cf45b59212024b
- **Virtual trading mode (default for the `default` session)**: run any strategy against live market data without placing real orders. Formerly named "paper trading" — `paper` is kept as a compatibility alias.
  - https://github.com/msaltnet/smtm/commit/302d4cca3c7e74b1dbdeec6eb95b3ca11745e313
  - https://github.com/msaltnet/smtm/commit/63cf010a93f625d0a1e8bbda5a6f2ea5026d9d91
- **Massively expanded DataProvider catalog (~26 building-block sources)**: news RSS feeds, Reddit, Fear & Greed index, CoinGecko/CoinCap, macro data (Yahoo Finance), on-chain metrics (Blockchain.info, Mempool, Etherscan gas), Binance derivatives positioning (funding rate, open interest, long/short ratio), Upbit notices, exchange rates, Hacker News, and more — composed into exchange codes such as `UPN`, `UMN`, `USC`, `UFC`.
  - https://github.com/msaltnet/smtm/commit/e5ecc165b80d7a80378eead7ac15bf269bbb476b
- **Text-type data support in DataProvider**: `get_info()` now returns a list of typed entries, so text data (news, notices, social posts) can be mixed with candle data in a single payload for LLM consumption.
  - https://github.com/msaltnet/smtm/commit/109075c1f421e8a9776eb5ca7db882ac04d62195

### Fixed Bugs
- **Telegram token and chat-id error handling**: a missing token is rejected at boot instead of silently booting with a placeholder, and a bad chat-id now surfaces the actual error instead of being misreported as a token problem.
  - https://github.com/msaltnet/smtm/commit/c5fc984e9cc5b21bd5a0ab74bf20f59a832ee7b4
  - https://github.com/msaltnet/smtm/commit/40f9d2b0fe62edb9e47a0f05b90d43586f1a43aa
- **cp949-safe boot messages**: dropped an ineffective sleep patch and replaced a cp949-breaking em-dash so console/boot messages encode cleanly on Windows (cp949) consoles.
  - https://github.com/msaltnet/smtm/commit/a193ba67789fbf2b6899b130fd9f4bd8eb41e0cd
- **Trading loop robustness**: only completed trades count toward the daily quota, tick execution is guarded on running state, the daily trade count is preserved across reconfiguration, and non-dict trader results no longer break the trade callback.
  - https://github.com/msaltnet/smtm/commit/d60cce4183d64639b3d3b81b7a942bfb4147bbde
  - https://github.com/msaltnet/smtm/commit/6e57e980b00364623d4eb052733d7f36d06bcdc3
  - https://github.com/msaltnet/smtm/commit/64f363a4be0946e8b345cde3ec09d5a558fb48f0
- **Session lifecycle fixes**: `create_session` rolls back cleanly when trader construction fails, per-session trade counts appear correctly in performance reports, and a failure in one session no longer aborts stopping the others.
  - https://github.com/msaltnet/smtm/commit/63b8e90c755f3e146f68af353b8f6e557ff92808
  - https://github.com/msaltnet/smtm/commit/fda0fd30752e9338c10db3821f1181f3d56fe0d7
  - https://github.com/msaltnet/smtm/commit/59fc8d434466be94df06fbf8324255824f1d8db8
- **Virtual trading fills**: failed simulated fills now report zero price/amount instead of phantom values.
  - https://github.com/msaltnet/smtm/commit/db68d4562336e9c6902457fc77d88f7875669085
- **Partial profile application**: applying a profile that specifies only some fields now inherits the current config for the rest instead of resetting them.
  - https://github.com/msaltnet/smtm/commit/2d1420d411f6cf423960b1b2ad886e16b60f8326

### Docs & Testing
- **"AI Agent" naming**: user-facing READMEs now refer to the LLM agent as an "AI Agent" for consistency.
  - https://github.com/msaltnet/smtm/commit/9371b40cf915ad833091280bb79cd6076a99fecf
- **E2E test framework without external APIs**: `tests/e2e_tests/` fakes only the boundaries (`FakeLlmClient`, `FakeDataProvider`, `SimulationTrader`) and runs the real internals, covering chat-driven trading and multi-session scenarios end to end.
  - https://github.com/msaltnet/smtm/commit/bd48cf77a178727a760f926e4c4c0a329dacffc1
  - https://github.com/msaltnet/smtm/commit/a8d7645275cefe669a58a3fd61b1dc33e647a610
  - https://github.com/msaltnet/smtm/commit/435ade0c75b4ebe4a53352aa70156683bdef64c5

## v2.0.0 (한국어)

메이저 재작성: 룰 기반 시뮬레이션/매매 엔진을 AI 에이전트 기반 2계층 트레이딩 시스템으로 교체하였으며, **전 과정을 텔레그램 채팅으로 제어**합니다. 플러그블 전략, 멀티계정·멀티세션 병렬 트레이딩, 기본 활성화된 가상거래를 지원합니다.

### 주요 변경 (Breaking Changes)
- **룰 기반 트레이딩 아키텍처 제거**: `Simulator`, `SimulationOperator`, `MassSimulator`, 데모 모드, 구 `Operator`, 시뮬레이션/대량시뮬레이션 모드가 모두 삭제되었습니다. 실주문 없이 전략을 검증하려면 새로운 가상거래 모드를 사용하세요.
  - https://github.com/msaltnet/smtm/commit/d46f60c501d5119c67733209b4d030ca0ab8ce19
  - https://github.com/msaltnet/smtm/commit/c4be87024828610dcae10214b16662cdd7c58771
- **CLI 대화형 모드 제거 — 텔레그램이 유일한 진입점**: 대화형 CLI 컨트롤러가 사라졌습니다. 이제 smtm은 텔레그램 봇으로만 실행됩니다(`python -m smtm --token <bot-token> --chatid <chat-id>`, 또는 환경변수 `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` 사용). 남은 CLI 플래그는 `--token`, `--chatid`, `--log`, `--version` 4개뿐이며, 설정용 플래그 — `--mode`, `--budget`, `--currency`, `--exchange`, `--strategy`, `--profile`, `--term`, `--virtual`, `--config` — 는 전부 제거되었습니다. 예산·통화·거래소·전략·주기(interval)는 이제 **채팅 기반 프로파일/세션 설정**입니다. 채팅으로 에이전트에게 프로파일을 만들거나 수정하고 세션을 생성·시작하도록 요청합니다.
  - https://github.com/msaltnet/smtm/commit/cd359d4ece6a75c8f14204864a98d49146d81ea0
- **가상거래가 default 세션의 기본값 — 실거래는 채팅으로 opt-in**: 부팅 시 `default` 세션은 가상 모드로 동작하므로 실제 주문이 전송되지 않습니다. 실거래를 하려면 채팅으로 `register_account`(자격증명 환경변수 *이름*만 저장)로 계정을 등록하고, `virtual: false`와 `account`를 지정한 프로파일을 만든 뒤 `create_session`·`start_session`을 실행합니다.
  - https://github.com/msaltnet/smtm/commit/0ae432782b377b82c76ad0caa3cf45b59212024b
- **`SMTM_LLM_API_KEY` 환경변수 필수화**: 채팅 에이전트와 `LLM` 전략은 벤더 독립 `LlmClient` 추상화를 통해 Anthropic Claude로 동작하며, 키가 없으면 부팅이 중단됩니다. 첫 구현체는 `ClaudeLlmClient`이고 `tool_choice`를 통한 강제 tool use를 지원합니다.
  - https://github.com/msaltnet/smtm/commit/a049670d67354b7250975a206719147691c606a3
  - https://github.com/msaltnet/smtm/commit/45d8af713993a8dd2749bc16fc36e115baddece9
  - https://github.com/msaltnet/smtm/commit/8b87a83094e71e2a7ce37acfba5bd4d9a4b5fcb6

### 기능 추가
- **2계층 아키텍처: SystemOperator + TradingOperator**: `SystemOperator`는 채팅 오케스트레이션 전용 에이전트로, 계정 등록·프로파일 관리·세션 생성/시작/중지/비교를 Tool로 수행하며 직접 주문하지 않습니다(`execute_trade` 도구 없음). 각 세션은 자체 `TradingOperator`가 고정 주기(기본 60초)로 DataProvider → Strategy → SafetyGuard → Trader → Analyzer 루프를 실행합니다.
  - https://github.com/msaltnet/smtm/commit/892eceadb8b3c03ee151a2adf1f574495bce4f04
  - https://github.com/msaltnet/smtm/commit/80f9de1427077bb0397580a53bc8f493d6ba82d2
  - https://github.com/msaltnet/smtm/commit/f0cb67d4dbbaac5903c9b86436ed379209b83c7d
  - https://github.com/msaltnet/smtm/commit/7be519e69cefca0c5ad6e1479c2b7c9059637da6
- **StrategyFactory 기반 플러그블 전략**: `Strategy` 인터페이스가 복원되었고 `BNH`(매수 후 보유), `RSI`, `SMA` 전략이 `StrategyFactory` 레지스트리에 등록되었습니다. 전략은 채팅으로 선택합니다.
  - https://github.com/msaltnet/smtm/commit/3dde9573a574af6806c1d75163fbd93b78c17854
  - https://github.com/msaltnet/smtm/commit/e63992aa11bf7014ffc9da55a1b59107933ad90e
  - https://github.com/msaltnet/smtm/commit/4fe6896b465f844d318cc9cac1c7d3e5e67013fb
  - https://github.com/msaltnet/smtm/commit/380f815d423a50ea06b22ddf457298bc455f74d3
- **StrategyLlm — 틱당 1회 구조화된 LLM 판단**: `LLM` 전략은 매 틱마다 모델에 구조화된 매수/매도/보류 판단을 1회만 요청(강제 tool use)하여, 매매 루프 안의 LLM 사용량을 예측 가능하게 유지합니다.
  - https://github.com/msaltnet/smtm/commit/7fe587d3da58a06d1e5385f3d88df5a4d4130335
- **안전장치 및 모니터링 계층**: `SafetyGuard`가 모든 주문을 실행 전에 검증하고(기본값: 1회 최대 거래금액 100,000 / 일일 최대 20회 / 손실률 한도 -20%), `SystemMonitor`가 시장 데이터·거래 요청/결과·안전 이벤트·LLM 사용량을 독립적으로 기록하며, 그 위에서 경량 `Analyzer`가 성과 리포트를 생성합니다.
  - https://github.com/msaltnet/smtm/commit/eb4d1b262753dda5f228cc755d5356c7cf0a4d82
  - https://github.com/msaltnet/smtm/commit/385572d039ecc7d29d9b1974cbb8bd26483af720
  - https://github.com/msaltnet/smtm/commit/c7433fd1a680c8503302f4c9f85863d6efe4cb97
  - https://github.com/msaltnet/smtm/commit/dd15524a3aa30a8fd6f555963faff2f5bfd3a701
- **계정 프로파일 (ProfileStore + CRUD 도구)**: 프로파일(`config/profiles/<name>.json`)은 전략 × 거래소 × 심볼 × 예산 × 계정 조합을 담습니다. 프로파일은 채팅으로 관리합니다(`list/describe/create/update/delete/switch_profile`).
  - https://github.com/msaltnet/smtm/commit/b471a05f8fee3f23b531c42c50dfd3dfd7b7ac3a
  - https://github.com/msaltnet/smtm/commit/448747cb1e3c8f9ba2ddf07f5a134313c8d20a44
- **멀티세션 병렬 트레이딩**: `SessionManager`가 여러 트레이딩 세션을 동시에 운용하며, 예산을 실제 계좌 잔고와 대조 검증하고 (계정, 심볼) 중복 할당을 방지합니다. 세션 도구(`create_session`, `start_session`, `stop_session`, `remove_session`, `list_sessions`, `compare_performance`)로 채팅에서 세션을 운용·비교할 수 있고, 모니터 로그에 세션 이름이 태깅되며, 컨트롤러 종료 시 모든 세션이 정리됩니다(텔레그램 autostart 없음).
  - https://github.com/msaltnet/smtm/commit/13628fba926253c7f7452b1e5cb0334b5d6e3821
  - https://github.com/msaltnet/smtm/commit/afd5e90dcef35205136e4b3c7fd1c64b4bed195b
  - https://github.com/msaltnet/smtm/commit/66886cff49f58ff148a0745d0e1e8b1bca396196
  - https://github.com/msaltnet/smtm/commit/aa278ba643e53172b69c9d818fd487c954ac31ad
  - https://github.com/msaltnet/smtm/commit/18cdc4684296d0de9a6a19277505984433df0d5e
- **환경변수 이름만 저장하는 멀티계정 지원**: `AccountStore`는 거래소 자격증명의 환경변수 *이름*만 저장하며(원시 키는 절대 저장하지 않음), 중복 key-env 쌍과 키 값 형태의 env 이름을 거부합니다. 계정 도구(`register_account`, `list_accounts`, `delete_account`)로 채팅에서 계정을 관리하고, 거래소 Trader는 계정별 자격증명 env 이름을 지원하며, `AccountGuard`와 `CompositeSafetyGuard`가 같은 계정을 공유하는 모든 세션에 계정 수준 한도를 강제합니다.
  - https://github.com/msaltnet/smtm/commit/11d9491cbb77ac2203b96c2adeba32c41b339d0b
  - https://github.com/msaltnet/smtm/commit/03dd452770cf9f49ef450b9f88a5c5bfedba78f7
  - https://github.com/msaltnet/smtm/commit/71470f08619f0cdb091cbbfa85d810ab611777fc
  - https://github.com/msaltnet/smtm/commit/9dae19d8372e394b6b90b6e2a1caa64b0500861e
  - https://github.com/msaltnet/smtm/commit/7425d9490d6b392178db19f8a3a24238f9ca26f1
- **텔레그램에서 프로파일·세션 도구 사용 가능**: 텔레그램 컨트롤러가 이제 계정/프로파일/세션 전체 도구를 등록하여(기존에는 오케스트레이션 도구만), 계정·프로파일·병렬 세션을 텔레그램 채팅에서 직접 관리할 수 있습니다.
  - https://github.com/msaltnet/smtm/commit/0ae432782b377b82c76ad0caa3cf45b59212024b
- **가상거래(virtual trading) 모드 (`default` 세션 기본값)**: 실주문 없이 실시간 시장 데이터로 전략을 운용합니다. 기존 "paper trading"에서 개명되었으며 `paper`는 호환 별칭으로 유지됩니다.
  - https://github.com/msaltnet/smtm/commit/302d4cca3c7e74b1dbdeec6eb95b3ca11745e313
  - https://github.com/msaltnet/smtm/commit/63cf010a93f625d0a1e8bbda5a6f2ea5026d9d91
- **DataProvider 카탈로그 대확장(빌딩블록 약 26종)**: 뉴스 RSS 피드, Reddit, Fear & Greed 지수, CoinGecko/CoinCap, 매크로 데이터(Yahoo Finance), 온체인 지표(Blockchain.info, Mempool, Etherscan gas), Binance 파생 포지셔닝(펀딩비, 미결제약정, 롱/숏 비율), Upbit 공지, 환율, Hacker News 등이 추가되어 `UPN`, `UMN`, `USC`, `UFC` 같은 거래소 코드로 조합됩니다.
  - https://github.com/msaltnet/smtm/commit/e5ecc165b80d7a80378eead7ac15bf269bbb476b
- **DataProvider 텍스트형 데이터 지원**: `get_info()`가 type이 부여된 항목의 리스트를 반환하도록 변경되어, 텍스트 데이터(뉴스, 공지, 소셜 게시글)를 캔들 데이터와 하나의 페이로드에 혼합해 LLM에 전달할 수 있습니다.
  - https://github.com/msaltnet/smtm/commit/109075c1f421e8a9776eb5ca7db882ac04d62195

### 버그 수정
- **텔레그램 토큰·chat-id 오류 처리**: 토큰 누락 시 placeholder로 부팅하지 않고 거부하며, 잘못된 chat-id는 토큰 문제로 오인 보고하지 않고 실제 오류를 정확히 노출합니다.
  - https://github.com/msaltnet/smtm/commit/c5fc984e9cc5b21bd5a0ab74bf20f59a832ee7b4
  - https://github.com/msaltnet/smtm/commit/40f9d2b0fe62edb9e47a0f05b90d43586f1a43aa
- **cp949 안전 부팅 메시지**: 효과 없는 sleep 패치를 제거하고 cp949에서 깨지는 em-dash를 교체하여, 콘솔/부팅 메시지가 Windows(cp949) 콘솔에서 정상 인코딩되도록 하였습니다.
  - https://github.com/msaltnet/smtm/commit/a193ba67789fbf2b6899b130fd9f4bd8eb41e0cd
- **매매 루프 견고성 개선**: 완료된 거래만 일일 거래 횟수에 집계하고, 틱 실행을 running 상태로 가드하며, 재설정 시에도 일일 거래 횟수를 유지하고, dict가 아닌 Trader 결과가 거래 콜백을 깨뜨리지 않도록 수정하였습니다.
  - https://github.com/msaltnet/smtm/commit/d60cce4183d64639b3d3b81b7a942bfb4147bbde
  - https://github.com/msaltnet/smtm/commit/6e57e980b00364623d4eb052733d7f36d06bcdc3
  - https://github.com/msaltnet/smtm/commit/64f363a4be0946e8b345cde3ec09d5a558fb48f0
- **세션 생명주기 수정**: Trader 생성 실패 시 `create_session`이 깔끔하게 롤백하고, 성과 리포트에 세션별 거래 횟수가 정확히 표시되며, 한 세션의 실패가 다른 세션들의 중지를 막지 않도록 수정하였습니다.
  - https://github.com/msaltnet/smtm/commit/63b8e90c755f3e146f68af353b8f6e557ff92808
  - https://github.com/msaltnet/smtm/commit/fda0fd30752e9338c10db3821f1181f3d56fe0d7
  - https://github.com/msaltnet/smtm/commit/59fc8d434466be94df06fbf8324255824f1d8db8
- **가상거래 체결 처리**: 실패한 모의 체결이 유령 값 대신 price/amount 0을 보고하도록 수정하였습니다.
  - https://github.com/msaltnet/smtm/commit/db68d4562336e9c6902457fc77d88f7875669085
- **부분 프로파일 적용**: 일부 필드만 지정한 프로파일 적용 시 나머지 필드를 초기화하지 않고 현재 설정을 상속하도록 수정하였습니다.
  - https://github.com/msaltnet/smtm/commit/2d1420d411f6cf423960b1b2ad886e16b60f8326

### 문서 & 테스트
- **"AI Agent" 명칭 통일**: 사용자 대상 README에서 LLM 에이전트를 "AI Agent"로 일관되게 표기합니다.
  - https://github.com/msaltnet/smtm/commit/9371b40cf915ad833091280bb79cd6076a99fecf
- **외부 API 없는 E2E 테스트 프레임워크**: `tests/e2e_tests/`는 경계(`FakeLlmClient`, `FakeDataProvider`, `SimulationTrader`)만 Fake로 대체하고 내부는 실제 코드를 실행하며, 채팅 기반 매매와 멀티세션 시나리오를 처음부터 끝까지 검증합니다.
  - https://github.com/msaltnet/smtm/commit/bd48cf77a178727a760f926e4c4c0a329dacffc1
  - https://github.com/msaltnet/smtm/commit/a8d7645275cefe669a58a3fd61b1dc33e647a610
  - https://github.com/msaltnet/smtm/commit/435ade0c75b4ebe4a53352aa70156683bdef64c5

---

## v1.8.0

### New Features
- **HTTP request retry logic for transient network failures**: Added `request_with_retry` wrapper with 2 retries and exponential backoff for 5xx status codes and `ConnectionError`. Applied to `BaseExchangeTrader`, `BaseDataProvider`, and `UpbitTrader` cancel request.
  - https://github.com/msaltnet/smtm/commit/54d02af2bea0a238457ea7d3d26562a938fc2d53

### Refactoring
- **Extract base classes to eliminate code duplication in traders and data providers**: Added `BaseExchangeTrader` with shared logic (timer, callbacks, credentials, HTTP helpers, `send_request`, `cancel_all_requests`) and `BaseDataProvider` with shared HTTP GET + error handling. Refactored `UpbitTrader`/`BithumbTrader` (-38% / -34% LOC) and 3 DataProviders (-16~19% LOC).
  - https://github.com/msaltnet/smtm/commit/f48fcc39100e687f72504bb5cd07fb682c80146a
- **Introduce TraderFactory to replace hardcoded `is_bithumb` exchange selection**: Replaced boolean `is_bithumb` flag with exchange code pattern (UPB, BTH) using `TraderFactory`, consistent with existing `StrategyFactory` and `DataProviderFactory`. Backward compatible with legacy numeric trader arguments (0, 1).
  - https://github.com/msaltnet/smtm/commit/8cc6b308b573bdef1c3f0cb9465d9e5432872772

### Security
- **Remove hardcoded API credential fallbacks and add validation**: Replaced placeholder default values (e.g. `"upbit_access_key"`) with empty strings and added credential validation at API call points. Removed duplicate `load_dotenv()` calls from trader and telegram modules (already called in `config.py` via `__init__.py`).
  - https://github.com/msaltnet/smtm/commit/63ff0c1999a58e3e3237752e855f32f56c0cabce

### Fixed Bugs
- **Correct `is_intialized` typo to `is_initialized` across all strategies**: Renamed misspelled variable in 7 strategy files and 6 corresponding test files.
  - https://github.com/msaltnet/smtm/commit/84f06e878f73d834a76c83e0b70e9427a75cf2a6

### Build / CI
- **Pin dependency versions, separate dev dependencies, fix encoding**: Pinned compatible version ranges in `setup.cfg`, moved dev tools (`pytest`, `coverage`, `pylint`, `black`) to `extras_require[dev]`, added `requirements-dev.txt`, and fixed `requirements.txt` UTF-16 encoding to UTF-8.
  - https://github.com/msaltnet/smtm/commit/66a9c2bc911160a8a345cb4cc250329f886892ba
- **Install dev dependencies in CI** to provide `coverage` and `pytest` for the test workflow.
  - https://github.com/msaltnet/smtm/commit/c4265032eec23287fe6f2a2ed1d053024937afc1

## v1.8.0 (한국어)

### 기능 추가
- **일시적 네트워크 오류에 대한 HTTP 요청 재시도 로직 추가**: 5xx 상태 코드 및 `ConnectionError` 발생 시 지수 백오프(exponential backoff)로 2회 재시도하는 `request_with_retry` 래퍼를 추가하였습니다. `BaseExchangeTrader`, `BaseDataProvider`, `UpbitTrader`의 주문 취소 요청에 적용되었습니다.
  - https://github.com/msaltnet/smtm/commit/54d02af2bea0a238457ea7d3d26562a938fc2d53

### 리팩터링
- **Trader와 Data Provider의 코드 중복 제거를 위한 베이스 클래스 추출**: 타이머, 콜백, 인증정보, HTTP 헬퍼, `send_request`, `cancel_all_requests` 등의 공통 로직을 가진 `BaseExchangeTrader`와, 공통 HTTP GET 및 에러 처리 로직을 가진 `BaseDataProvider`를 추가하였습니다. `UpbitTrader`/`BithumbTrader`는 -38% / -34% LOC, 3개의 DataProvider는 -16~19% LOC 감소하였습니다.
  - https://github.com/msaltnet/smtm/commit/f48fcc39100e687f72504bb5cd07fb682c80146a
- **TraderFactory 도입으로 하드코딩된 `is_bithumb` 거래소 선택 방식 개선**: boolean `is_bithumb` 플래그를 거래소 코드 패턴(UPB, BTH)으로 대체하여 기존의 `StrategyFactory`, `DataProviderFactory`와 일관성을 확보하였습니다. 기존의 숫자 인자(0, 1)와도 하위 호환성을 유지합니다.
  - https://github.com/msaltnet/smtm/commit/8cc6b308b573bdef1c3f0cb9465d9e5432872772

### 보안 개선
- **하드코딩된 API 자격증명 기본값 제거 및 검증 추가**: placeholder 기본값(예: `"upbit_access_key"`)을 빈 문자열로 변경하고 API 호출 시점에 자격증명 검증을 추가하였습니다. trader와 telegram 모듈의 중복된 `load_dotenv()` 호출을 제거하였습니다(`config.py`의 `__init__.py`에서 이미 호출됨).
  - https://github.com/msaltnet/smtm/commit/63ff0c1999a58e3e3237752e855f32f56c0cabce

### 버그 수정
- **모든 전략에서 `is_intialized` 오타를 `is_initialized`로 수정**: 7개의 전략 파일과 6개의 테스트 파일에서 잘못 표기된 변수명을 수정하였습니다.
  - https://github.com/msaltnet/smtm/commit/84f06e878f73d834a76c83e0b70e9427a75cf2a6

### 빌드 / CI
- **의존성 버전 고정, 개발용 의존성 분리, 인코딩 수정**: `setup.cfg`에 호환 가능한 버전 범위를 고정하고, 개발 도구(`pytest`, `coverage`, `pylint`, `black`)를 `extras_require[dev]`로 분리하였으며, `requirements-dev.txt`를 추가하고 `requirements.txt` 인코딩을 UTF-16에서 UTF-8로 수정하였습니다.
  - https://github.com/msaltnet/smtm/commit/66a9c2bc911160a8a345cb4cc250329f886892ba
- **CI에서 개발용 의존성 설치**: 테스트 워크플로우에 필요한 `coverage`와 `pytest`를 제공하기 위해 CI에서 dev 의존성을 설치하도록 수정하였습니다.
  - https://github.com/msaltnet/smtm/commit/c4265032eec23287fe6f2a2ed1d053024937afc1

---

## v1.7.1
- Refactoring and renewal documents and images

---

## v1.6.2
- Fix `setup.py`, `setup.cfg`

---

## v1.6.1
- Fix README image link

---

## v1.6.0

### Telegram Controller multilingual support (English)
- https://github.com/msaltnet/smtm/commit/bd6decb7d9a14f22e8c0d429b16be07a5fa30b85

## v1.6.0 (한국어)

### TelegramController 다국어 지원(영어)
- https://github.com/msaltnet/smtm/commit/bd6decb7d9a14f22e8c0d429b16be07a5fa30b85

---

## v1.5.0

### Add the alert_callback interface
Added `alert_callback` which can be used to send notifications from the core module to the controller. It can be used to make no transaction, send only a notification, or to notify the Analyzer about errors in data processing. Added `StrategySas` strategy as an example.
- https://github.com/msaltnet/smtm/commit/7dcd9e1843b15cd281dfe7af4b35fa4ca1352514
- https://github.com/msaltnet/smtm/commit/3cd4328d8af1aa5749af6be646dec57b68c2db3b
- https://github.com/msaltnet/smtm/commit/5263cdb6e0ca707977a9a966d2bb25321debab60
- https://github.com/msaltnet/smtm/commit/231a58868d0bbd5c18f62171e231b8e1e19a5964
- https://github.com/msaltnet/smtm/commit/95485d5d5d068644cf4de0da3aadf094056b6b2c

### Added StrategyHey
A new strategy, **StrategyHey**, has been added, which analyzes trading data and sends alerts only. It inherits from `StrategySas` and implements an alert system through `alert_callback` when a moving average breakdown occurs or a volatility breakout event is detected. This strategy is particularly useful for short-term trading in ranging markets.
- https://github.com/msaltnet/smtm/commit/a420001d626d1a628c723eda01e676e95e1fbeda
- https://github.com/msaltnet/smtm/commit/b1a2bbc48af339cd5eafde88df481a1faaa20161

### Other Refactoring
- **Implemented `pytest`**: Unit and integration tests have been consolidated into the `tests` directory. The transition to `pytest` has also improved the clarity of test results, as shown below.
  - https://github.com/msaltnet/smtm/commit/087e910fb78f9f6328779ad89594633e34514cd4

![image](https://github.com/msaltnet/smtm/assets/9311990/4b3d2e5a-991a-4525-839a-1a2bf828d531)

- **Code Cleanup**: Removed warning messages by refining the code.
  - https://github.com/msaltnet/smtm/commit/02fb5c08fa829be67f1866cb4367d367cbebf5b6
  - https://github.com/msaltnet/smtm/commit/601b275bcba0b19b959672d6dc9e1d4d8c6410e6
  - https://github.com/msaltnet/smtm/commit/5c15e2a12cce0ff75faa97eafb17ccd81016f92d

## v1.5.0 (한국어)

### alert_callback 인터페이스 추가
코어 모듈에서 컨트롤러에 알림을 보내는 용도로 사용될 수 있는 `alert_callback`이 추가되었습니다. 거래를 하지 않고, 알림만 보내거나, Analyzer에서 데이터 처리시 오류에 대해서 알림을 보내는 등의 용도로 사용할 수 있습니다. 예제로는 `StrategySas` 전략이 추가 되었습니다.
- https://github.com/msaltnet/smtm/commit/7dcd9e1843b15cd281dfe7af4b35fa4ca1352514
- https://github.com/msaltnet/smtm/commit/3cd4328d8af1aa5749af6be646dec57b68c2db3b
- https://github.com/msaltnet/smtm/commit/5263cdb6e0ca707977a9a966d2bb25321debab60
- https://github.com/msaltnet/smtm/commit/231a58868d0bbd5c18f62171e231b8e1e19a5964
- https://github.com/msaltnet/smtm/commit/95485d5d5d068644cf4de0da3aadf094056b6b2c

### StrategyHey 전략 추가
거래 정보를 분석해서 알림만 보내는 전략으로 StrategyHey 전략이 추가되었습니다. `StrategySas` 전략을 상속 받아서 이동 평균선이 깨질 때 또는 변동성 돌파 이벤트가 발생하였을 때, `alert_callback`을 통해 알림을 전달하는 앱을 구현하였습니다. 횡보장에서 단기 트레이딩시에 유용하게 사용할 수 있습니다.
- https://github.com/msaltnet/smtm/commit/a420001d626d1a628c723eda01e676e95e1fbeda
- https://github.com/msaltnet/smtm/commit/b1a2bbc48af339cd5eafde88df481a1faaa20161

### 그 외 리팩터링
- `pytest`를 적용하고, 단위테스트와 통합테스트를 `tests`로 모았습니다. `pytest`를 사용하게 되면서 테스트 결과 화면도 아래와 같이 깔끔하게 변경되었습니다.
  - https://github.com/msaltnet/smtm/commit/087e910fb78f9f6328779ad89594633e34514cd4

![image](https://github.com/msaltnet/smtm/assets/9311990/4b3d2e5a-991a-4525-839a-1a2bf828d531)

- 코드를 정리하여 경고 문구를 제거하였습니다.
  - https://github.com/msaltnet/smtm/commit/02fb5c08fa829be67f1866cb4367d367cbebf5b6
  - https://github.com/msaltnet/smtm/commit/601b275bcba0b19b959672d6dc9e1d4d8c6410e6
  - https://github.com/msaltnet/smtm/commit/5c15e2a12cce0ff75faa97eafb17ccd81016f92d

---

## v1.4.0

### Analyzer 기능 추가

Analyzer를 통해서 선 그래프를 그릴 수 있는 `add_line_callback`를 추가되었습니다. Strategy에서 `add_line_callback` 콜백을 사용해서 선 그래프를 추가할 수 있으며, StrategySmaDualMl 전략에서 활용되고 있는 예제를 확인할 수 있습니다.
- https://github.com/msaltnet/smtm/commit/d67614f12cdfdebd312c1a55a7169a0721e16be6
- https://github.com/msaltnet/smtm/commit/1a4efb2b87e306e4e873247ca1f1bfcba1ed48f5

### Binance Data Provider 추가와 Data Provider Interface 변경

Binance Data Provider가 추가되었습니다. 이제 Binance 캔들 정보를 사용해서 시뮬레이션을 할 수 있습니다. Config 모듈의 simulation_source 정보를 변경해서 시뮬레이션에 사용할 데이터를 선택 할 수 있습니다.

```
class Config:
    """시스템 전역 설정 모듈"""

    # 시뮬레이션에 사용할 거래소 데이터 simulation_source: upbit, binance
    simulation_source = "upbit"
```

Binance 캔들 정보와 Upbite 캔들 정보를 동시에 사용할 수 있도록 Data Provider의 반환 데이터 형식이 변경되었습니다. Data Provider는 복수개의 data를 하나의 리스트로 한 번에 전달할 수 있게 되었으며, 각각의 데이터는 추가된 type 항목을 통해서 구분할 수 있습니다. 변경된 Data Provider의 Data 형식은 다음과 같으며, Binance와 Upbit 데이터를 모두 제공하는 UpbitBinanceDataProvider가 추가되었습니다.

```
  [
      {
          "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
          "market": 거래 시장 종류 BTC
          "date_time": 정보의 기준 시간
          "opening_price": 시작 거래 가격
          "high_price": 최고 거래 가격
          "low_price": 최저 거래 가격
          "closing_price": 마지막 거래 가격
          "acc_price": 단위 시간내 누적 거래 금액
          "acc_volume": 단위 시간내 누적 거래 양
      },
      {
          "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
          "usd_krw": 환율
          "date_time": 정보의 기준 시간
      },
      {
          "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
          "market": 거래 시장 종류 BTC
          "date_time": 정보의 기준 시간
          "opening_price": 시작 거래 가격
          "high_price": 최고 거래 가격
          "low_price": 최저 거래 가격
          "closing_price": 마지막 거래 가격
          "acc_price": 단위 시간내 누적 거래 금액
          "acc_volume": 단위 시간내 누적 거래 양
      }
  ]
```

Binance와 Upbit 두 거래소의 정보를 동시에 사용해서 시뮬레이션을 할 수 있는 SimulationDualDataProvider도 추가되었으며, Config에서 사용 여부를 선택 할 수 있습니다.

```
class Config:
    """시스템 전역 설정 모듈"""

    # SimulationDualDataProvider의 데이터를 사용할지 여부: normal, dual
    simulation_data_provider_type = "normal"
```

Upbit, Binance 두 거래소의 캔들 정보를 동시에 사용하는 예제 전략 StrategySmaDualMl이 추가되었습니다. SML 전략과 동일한 로직을 가지고 있으며 Binance 데이터로 add_line_callback를 사용해서 선 그래프를 추가하도록 하였습니다. 아래 붉은 색 선이 Binance 데이터의 closing price입니다.

![68e7d3d8-9cce-4eb1-ae5c-166d591e1641](https://github.com/msaltnet/smtm/assets/9311990/ea339501-d679-449d-b582-1e29244e01c2)

- https://github.com/msaltnet/smtm/commit/e8f490e5b8d61ad2b3520f00e296498d6004488c
- https://github.com/msaltnet/smtm/commit/34ca568b6112e0b0d60f8e19afb9425c45d9e537
- https://github.com/msaltnet/smtm/commit/d46064c08344685aaf89042d321c8687b914e93a
- https://github.com/msaltnet/smtm/commit/77c482bf5658e31ce802b0fb82f0ffbbdabeb110
- https://github.com/msaltnet/smtm/commit/ac7f3421603b4dc4b7b19c0b9efa5b03be846e25
- https://github.com/msaltnet/smtm/commit/69d9c63f4a135f0357b441a27f4bc9d0d55e585d
- https://github.com/msaltnet/smtm/commit/b8f1f938be58e23d3a003cbd57c1f1985bc82120
- https://github.com/msaltnet/smtm/commit/1cb1adbd19b69ed2e8ab1b0be6678e6d1d57151b
- https://github.com/msaltnet/smtm/commit/3a038d740b82f370a46cd84b0bf7a1167b48402b

DataProviderFactory를 추가하여 Telegram Controller에서 Data Provider를 동적으로 선택할 수 있도록 하였습니다. 기존에는 Trader와 Data Provider가 일치하였지만 Binance 데이터나 다른 데이터를 복합적으로 사용하는 Data Provider를 추가해서 전략을 운영할 수 있게 되었습니다. 환율정보, 주가정보, 암호화폐 지수를 사용한 다양한 전략을 만들어서 운영이 가능합니다.

![image](https://github.com/msaltnet/smtm/assets/9311990/3a9a4da7-d285-498b-8329-63264d8b843f)

### 그 외 수정 사항

모듈이 많아짐에 따라 관리를 위해서 controller, data, strategy, trader 폴더로 구분하였습니다.
- https://github.com/msaltnet/smtm/commit/b58e100380ca6e28163944bf6ef5cb1688c4ebea

0.0024와 같은 값을 소숫점 4자리 수로 변경할 때 발생하는 부동 소수점 문제를 수정하였습니다.
- https://github.com/msaltnet/smtm/commit/2fff47b1e5caf1bee36388194e031c190585e786 


---

## v1.3.0 (English)
Improve architecture to change candel interval for both simulation and real-trading
  - Make `Config` module for global interval setting
    - 5542498c66804aa2f6dba3fa0e6a9002c628b79f
    - 7de1ae1452346910819f2a96d4801832f62cea0a
    - 40657f816366dd1b98fa3eaa975a813f41c97b40
    - c3728b4a2b2e53dbfe0659563333d9bb6837e173
    - c64c2215e073283baadbfad7e529c2da5137e9fd
    - 6ffcee97f6d3fa13604d037e1da9b4eb9d660ad6
    - 031fcdf789f4f4e0a43ec0ff7173772a1476df33

## v1.3.0 (한국어)
Candle Interval을 변경해서 시뮬레이션, 거래 진행 할 수 있도록 구조 개선
  - `Config` 모듈을 만들어서 전역적으로 interval 설정 가능하도록 변경
    - 5542498c66804aa2f6dba3fa0e6a9002c628b79f
    - 7de1ae1452346910819f2a96d4801832f62cea0a
    - 40657f816366dd1b98fa3eaa975a813f41c97b40
    - c3728b4a2b2e53dbfe0659563333d9bb6837e173
    - c64c2215e073283baadbfad7e529c2da5137e9fd
    - 6ffcee97f6d3fa13604d037e1da9b4eb9d660ad6
    - 031fcdf789f4f4e0a43ec0ff7173772a1476df33

---

## v1.2.0 (English)
Enhance simulation performance (about 3x more speedup)
  - when interval is under 1sec, call handler directly instead of using `threading.Timer`
    - d9e9b2b9262612ff35389a4ffd0f4e56effd9290
Change CI Travis -> github action
  - 50faecd5d1c83cd9af3f04b274d018d1f9f08e64
Use strategy code instead of names
  - 5ea80279ca64f78f536f139ef615035ab1e5de57

### New Features
- add StrategySmaMl
  - aad85ce841b90505017d94a6034f7f3b5b12965f

### Fixed Bugs
- fix a bug for telegram controller strategy selector
  - 7101eedd81bafa746ab21ff64c7f9a82ed4a2f2a

## v1.2.0
Simulation 속도 개선 (약 3배이상 향상)
  - interval이 1초 미만일 때, `threading.Timer`를 사용하지 않고 바로 핸들러 호출하도록 수정
    - d9e9b2b9262612ff35389a4ffd0f4e56effd9290
CI를 Travis -> github action으로 변경
  - 50faecd5d1c83cd9af3f04b274d018d1f9f08e64
전략 이름 대신 코드를 사용
  - 5ea80279ca64f78f536f139ef615035ab1e5de57

### 기능 추가
- 이동 평균선을 이용한 기본 전략에 간단한 ML을 추가한 StrategySmaMl 전략 추가
  - aad85ce841b90505017d94a6034f7f3b5b12965f

### 버그 수정
- 텔레그램 컨트롤러에서 전략 선택 문자 비교 버그 수정
  - 7101eedd81bafa746ab21ff64c7f9a82ed4a2f2a

---

## v1.1.1 (English)
Add StrategyFactory and remove integration_tests from package

### New Features
- Add StrategyFactory to add/remove a strategy easily.
  - 3403c6918a18bd6fedf5606fe7726ce080fdd941
  - 4bdc03e8214b7d172aa73ca1680b44a3e61f6386
- Add log directory to write log files
  - e74e91095425228038344ced0484416b00ea787a

### Fixed Bugs
- Remove integration_tests package in the top_level of packages.
  - bf5b925dc6aa4cd5cc9dc10218bdf30b1d308f6f

## v1.1.1
StrategyFactory 추가 및 integration_tests를 패키지에서 제거

### 기능 추가
- 전략을 쉽게 추가/제거 할 수 있도록 StrategyFactory 추가. 전략을 추가할 때 StrategyFactory에만 추가해주면 됨
  - 3403c6918a18bd6fedf5606fe7726ce080fdd941
  - 4bdc03e8214b7d172aa73ca1680b44a3e61f6386
- 로그 파일을 log 폴더에 저장
  - e74e91095425228038344ced0484416b00ea787a

### 버그 수정
- integration_tests가 별도의 패키지로 top_level에 추가되고 있는 문제 수정. smtm 패키지 설치시 smtm과 integration_tests 두 개의 패키지가 따로 설치되는 문제
  - bf5b925dc6aa4cd5cc9dc10218bdf30b1d308f6f

---

## v1.1.0 (English)
Demo feature and RSI strategy

### New Features
- Analyzer `add_drawing_spot` can add green spots to graph
  - bff9cefc51fb9b0df7710e16b16d5889aeffe8b7
  - 254e1165358a6d2055bbddea9133f135651ded41
  - a98cb0075fa1a08554d94e1dc797846645f912d3
  - 5893198250611ec60c50a5218d95b7e11a92e6da
- Add DOGE, XRP for Upbit
  - 6f68ea3975f12e42bfb579740c376d52f5504499
- Can save periodic graph for Simulation, MassSimulation 
  - 692cc7323b502d2ab69aeb3be43a648208d7f89b
  - e448005c07623b158de642a94483286644f511da
- Add RSI index to Analyzer graph
  - a12b565fc047de6e145861995d79c7c70139b628
- Add RSI Strategy
  - 59ef24c2e15a76cc24a952e7d8bebba7031aa020
- Telegram controller demo mode with DemoTrader
  - 698b7240e9a62492d8f87815a96477e4372602b4

### Fixed Bugs
- Send warning message via telegram when Worker catch exception from runnable
  - ab54bfa5f42dab87e1efc53c8e792f66397ba744
  - 032fac2df35de05c3d9b516d076277bb6b8222f0

## v1.1.0
Demo 모드와 RSI 전략 추가

### 기능 추가
- Analyzer `add_drawing_spot` 그래프에 점 추가 가능
  - bff9cefc51fb9b0df7710e16b16d5889aeffe8b7
  - 254e1165358a6d2055bbddea9133f135651ded41
  - a98cb0075fa1a08554d94e1dc797846645f912d3
  - 5893198250611ec60c50a5218d95b7e11a92e6da
- Upbit에 DOGE, XRP 화폐 추가
  - 6f68ea3975f12e42bfb579740c376d52f5504499
- Simulation, MassSimulation 주기적으로 그래프 저장
  - 692cc7323b502d2ab69aeb3be43a648208d7f89b
  - e448005c07623b158de642a94483286644f511da
- RSI index 추가
  - a12b565fc047de6e145861995d79c7c70139b628
- RSI 전략 추가
  - 59ef24c2e15a76cc24a952e7d8bebba7031aa020
- Telegram controller Demo 모드 추가
  - 698b7240e9a62492d8f87815a96477e4372602b4

### 버그 수정
- Worker runnable에 문제 발생시 종료 후 텔레그램 메세지 전송
  - ab54bfa5f42dab87e1efc53c8e792f66397ba744
  - 032fac2df35de05c3d9b516d076277bb6b8222f0

---

## v1.0.0 (English)
First release with main features

### Main Features
1. Simulation
2. Mass-Simulation
3. Real Trading
4. Telegram Chatbot Controller
5. Jupyter Notebook Controller

## v1.0.0
주요 기능을 포함한 첫번째 릴리즈

### 주요 기능
1. 시뮬레이션
2. 대량시뮬레이션
3. 실전 거래
4. 텔레그램봇 모드
5. 주피터 노트북 컨트롤러

