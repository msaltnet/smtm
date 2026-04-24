# smtm — FAQ

자주 묻는 질문과 답변을 모은 문서입니다. 모든 답변은 **코드 동작 기준**이며, 정책·한도는 구체적인 수치까지 기재합니다.

- 최종 갱신일: 2026-04-20
- 기준 버전: 1.7.1

---

## 1. 일반 FAQ

**Q. smtm이 정말로 수익을 보장하나요?**
A. 아니요. smtm은 **LLM이 매매 판단을 수행하는 실행 프레임워크**입니다. 수익 여부는 시장 상황과 LLM의 판단 품질에 따라 달라지며, 손실 가능성이 항상 존재합니다. 기본 SafetyGuard는 **최대 -20% 누적 손실**까지만 허용하도록 설계돼 있습니다.

**Q. 어떤 LLM을 쓸 수 있나요?**
A. 현재 코드에 구현된 벤더는 Anthropic Claude(`claude-sonnet-4-20250514`) 하나입니다. `LlmClient` 추상 계층은 존재하므로 OpenAI / Ollama 어댑터를 추가할 수 있도록 설계돼 있지만, 아직 구현되지 않았습니다.

**Q. 어떤 거래소를 지원하나요?**
A. 실주문까지 가능한 거래소(Trader 구현 존재)는 **Upbit(`UPB`)** 와 **Bithumb(`BTH`)** 두 곳입니다. Binance(`BNC`)와 Upbit+Binance 병합(`UBD`)은 **데이터 조회만** 지원합니다.

**Q. 지원 통화는?**
A. `execute_trade` Tool 입력 스키마상 BTC, ETH, DOGE, XRP를 받으며, 실제 거래소에 해당 페어가 존재해야 합니다.

**Q. API 호출 비용은 어느 정도 드나요?**
A. 기본 `--term 60`(1분) 주기로 LLM을 호출합니다. 한 틱마다 시스템 프롬프트 + 시장 데이터 + 대화 이력을 전송하므로 장시간 구동 시 비용이 누적됩니다. `SystemMonitor.get_llm_usage()`로 누적 토큰을 추적하세요.

---

## 2. 역할별 FAQ

### 2.1 일반 사용자

**Q. `start`만 누르고 방치해도 되나요?**
A. 기술적으로는 가능하나 권장하지 않습니다. LLM 판단이 예상과 어긋날 수 있고, 네트워크 단절/거래소 점검/한도 초과 상황에서도 프로세스는 살아 있을 수 있습니다. 로그와 텔레그램 알림을 주기적으로 확인하세요.

**Q. 중간에 LLM 판단을 바꾸고 싶어요.**
A. 대화창에 그냥 입력하면 됩니다. "지금은 매도하지 마", "관망하자" 같은 메시지는 대화 이력에 합류해 다음 판단에 영향을 줍니다. 확실히 멈추려면 `stop`을 입력하세요.

**Q. 대화 이력은 얼마나 유지되나요?**
A. 기본 최대 100개 메시지(= 50 턴)까지 유지하고 그 이상은 오래된 것부터 잘라냅니다. 프로세스가 재시작되면 이력은 사라집니다.

### 2.2 개발자 / 빌더

**Q. 새 거래소를 추가하려면?**
A. `smtm/data/` 안에 `DataProvider` 구현 + `smtm/trader/`에 `Trader` 구현을 추가하고, 각각 `DataProviderFactory.DataProvider_LIST`, `TraderFactory.TRADER_LIST`에 등록합니다. `NAME`, `CODE` 클래스 속성을 반드시 지정하세요.

**Q. 새 Tool을 추가하려면?**
A. `smtm/llm/tools/` 아래에 `Tool`을 상속한 클래스를 만들고 `LlmOperator.setup_tools()`에서 `tool_router.register(my_tool)`로 등록합니다. `input_schema`는 JSON Schema 형태로 LLM에 그대로 전달됩니다.

**Q. 다른 LLM 벤더를 붙이고 싶어요.**
A. `smtm/llm/llm_client.py`의 `LlmClient`를 상속해 `create_message()`를 구현하고, 응답을 `LlmResponse(text, tool_calls, stop_reason, usage)` 형태로 정규화하면 됩니다.

### 2.3 운영자

**Q. 장기 구동 시 모니터링은 어떻게 하나요?**
A. `log/smtm.log`(2MB × 10 롤링)가 기본 파일 로그입니다. 내부 상태(거래/LLM 호출/안전장치 차단)는 현재 `SystemMonitor`에 인메모리로만 남습니다. 영속 저장은 로드맵 항목입니다.

**Q. 서버 재시작 후 자동 복구가 되나요?**
A. 현재 설계상 **세션 상태를 영속 저장하지 않습니다.** 대화 이력, 거래 이력, 일일 거래 카운터는 프로세스가 죽으면 사라집니다. 한도 재계산도 재시작 이후부터 새로 쌓입니다.

---

## 3. 기능별 FAQ

### 3.1 인증 / 환경변수

**Q. `SMTM_LLM_API_KEY`를 설정하지 않으면?**
A. CLI 모드에서 "`SMTM_LLM_API_KEY` 환경변수를 설정해주세요" 메시지가 뜨고 종료됩니다.

**Q. 거래소 키는 언제 검증되나요?**
A. 주문을 실제로 전송하는 시점에 거래소가 검증합니다. 잘못된 키의 경우 `execute_trade` Tool 결과가 실패로 돌아오고, LLM이 해당 오류 메시지를 받아 후속 판단에 반영합니다.

### 3.2 LLM / Tool use

**Q. LLM이 Tool을 안 부르고 그냥 답변만 하는데요.**
A. 일반 질문이거나 시장에 변화가 크지 않다고 판단한 경우 LLM이 "관망"을 제안하며 Tool 호출을 생략할 수 있습니다. 강제로 Tool을 호출하게 하려면 "지금 시장 데이터 한 번 확인해줘"처럼 명시적으로 요청하세요.

**Q. 대화 이력이 너무 길어지면 문제가 있나요?**
A. `max_conversation_turns`(기본 50턴) 한도로 오래된 메시지를 잘라냅니다. 시스템 프롬프트와 최근 이력만 전송되므로 토큰은 대체로 안정적입니다.

### 3.3 SafetyGuard (안전장치)

**Q. 기본 한도는 얼마인가요?**
A. `SafetyConfig` 기본값은 다음과 같습니다.

| 필드 | 기본값 | 의미 |
|------|--------|------|
| `max_trade_amount` | 100,000 KRW | 1회 거래 최대 금액 |
| `max_daily_trades` | 20 | 하루 거래 횟수 |
| `max_loss_ratio` | -0.20 (-20%) | 누적 손실률 한도 |
| `initial_budget` | `--budget` 값 | 손실률 계산 기준 |

**Q. CLI 옵션으로 한도를 바꿀 수 있나요?**
A. 현재는 노출돼 있지 않습니다. Controller 코드에서 `config["safety"]` dict로 주입해야 합니다 (예시는 [user-guide.md 시나리오 5](user-guide.md#시나리오-5--안전장치-기본값이-너무-타이트해서-조정) 참고).

**Q. SafetyGuard가 거절하면 어떻게 되나요?**
A. `execute_trade` Tool이 실패 결과(`allowed=False, reason="..."`)를 LLM에 반환합니다. LLM은 그 사유를 읽고 주문 금액을 줄이거나 관망으로 전환합니다. 모든 차단 이벤트는 `SystemMonitor.safety_event_log`에 기록됩니다.

**Q. LLM이 안전장치를 우회할 수 있나요?**
A. 없습니다. `SafetyGuard.check()`는 **Tool 실행 직전 코드**에서 호출되며, LLM이 응답하는 JSON과는 독립적으로 동작합니다.

### 3.4 데이터 / 거래소

**Q. `--exchange UPB`와 `--exchange BNC`의 차이는?**
A. `UPB`는 Upbit 시장 데이터 + Upbit 실주문을 모두 사용합니다. `BNC`(Binance)는 시장 데이터는 제공하지만 **Trader 구현이 없어** 주문이 불가합니다 (Factory가 `None`을 반환해 실행이 중단됩니다).

**Q. `UBD`는 무엇인가요?**
A. `UpbitBinanceDataProvider`로 Upbit과 Binance 양쪽 데이터를 병합해 제공하는 DataProvider 코드입니다. 역시 Trader 구현은 없습니다.

**Q. `UPN`은 무엇인가요?**
A. `UpbitNewsDataProvider`입니다. Upbit의 `primary_candle`과 RSS 기반 암호화폐 뉴스(`type='news'`)를 한 번에 제공합니다. 기본 소스는 CoinDesk이며 Trader는 Upbit가 그대로 사용돼 실매매가 가능합니다. 사용자 정의 RSS URL을 쓰고 싶으면 `UpbitNewsDataProvider(news_url=..., news_source=...)`로 직접 생성하세요.

**Q. `UMN`은 무엇인가요?**
A. `UpbitMultiNewsDataProvider`입니다. Upbit 캔들에 CoinDesk·CoinTelegraph·Decrypt·CryptoSlate 네 곳의 RSS 뉴스를 합쳐 한 번의 `get_info()` 응답으로 돌려줍니다. 소스별 건수는 `per_source_count`(기본 3)로 조절하며, 다른 소스 구성을 원하면 `news_providers=[...]`에 `NewsDataProvider` 인스턴스 리스트를 직접 주입할 수 있습니다.

**Q. 다른 뉴스 소스를 쓰고 싶습니다.**
A. `smtm/data/news_sources.py`에 CoinTelegraph(`CTN`) / Decrypt(`DCN`) / CryptoSlate(`CSN`) / Bitcoin Magazine(`BMN`) 프리셋 서브클래스가 있고, 여러 소스를 합치는 `MultiNewsDataProvider`(`MNS`)도 있습니다. 프리셋은 Factory에 등록되어 있지 않으므로 코드에서 직접 `from smtm import CoinTelegraphNewsDataProvider` 방식으로 사용하세요. 완전히 새 소스를 추가하려면 `NewsDataProvider`를 상속해 `DEFAULT_URL`·`DEFAULT_SOURCE`·`CODE`·`NAME`만 덮어쓰면 됩니다.

**Q. `USC`는 무엇인가요?**
A. `UpbitSocialDataProvider`입니다. Upbit 캔들(`primary_candle`)에 다중 뉴스(`type='news'`), r/CryptoCurrency와 r/Bitcoin 게시물(`type='reddit'`), alternative.me의 Crypto Fear & Greed 지수(`type='sentiment_index'`)를 한 번의 `get_info()`로 합쳐 반환합니다. 가격 움직임과 함께 시장 심리까지 LLM에 넘기고 싶을 때 사용하세요. 소스 구성은 `UpbitSocialDataProvider(..., providers=[...])`로 바꿀 수 있습니다.

**Q. 뉴스 말고 다른 텍스트/지표 소스도 추가할 수 있나요?**
A. 네. 현재 내장돼 있고 키 없이 바로 쓸 수 있는 빌딩 블록은 다음과 같습니다.
- **가격/시총** `type='price_snapshot'` — `CoinGeckoDataProvider`(`CGK`, 코인별), `CoinCapDataProvider`(`CCP`, CoinGecko 백업)
- **크립토 시장 거시** `type='crypto_global'` — `CryptoGlobalDataProvider`(`CGL`, 전체 시총·BTC/ETH/스테이블 도미넌스)
- **전통시장/매크로 지수** `type='macro_market'` — `YahooFinanceDataProvider`(`YFN`, DXY·S&P500·VIX·Gold·US10Y·Nasdaq)
- **온체인(BTC)** `type='onchain_stats'` / `type='mempool_fees'` — `BlockchainInfoDataProvider`(`BCI`), `MempoolFeesDataProvider`(`MPF`) (모두 BTC 전용)
- **온체인(ETH)** `type='eth_gas'` — `EtherscanGasDataProvider`(`EGS`, gwei 권장값, 키 선택)
- **파생·포지셔닝** `type='funding_rate'` / `open_interest` / `long_short_ratio` — `BinanceFundingRateDataProvider`(`BFR`), `BinanceOpenInterestDataProvider`(`BOI`), `BinanceLongShortRatioDataProvider`(`BLS`)
- **감정** `type='sentiment_index'` — `FearGreedDataProvider`(`FGI`, alternative.me/fng)
- **환율** `type='exchange_rate'` — `ExchangeRateDataProvider`(`FXR`, open.er-api.com)
- **소셜** `type='reddit'` / `type='hackernews'` — Reddit 3종(`RDT`·`RCC`·`RBT`), `HackerNewsDataProvider`(`HNS`)
- **경제/금융 뉴스** `type='news'` — `WSJMarketsNewsDataProvider`(`WSJ`), `MarketWatchNewsDataProvider`(`MWN`), `CNBCFinanceNewsDataProvider`(`CNB`), `TheBlockNewsDataProvider`(`TBN`)
- **거래소 공지** `type='notice'` — `UpbitNoticeDataProvider`(`UPT`)
새 타입을 도입할 때는 `get_info()`에 `type` 필드가 있는 딕셔너리 리스트를 반환하도록 만들기만 하면 LLM이 `type`에 따라 해석합니다.

**Q. 이 모든 소스를 한 번에 쓰고 싶어요.**
A. `UpbitFullContextDataProvider`(`UFC`)를 사용하세요. Upbit 캔들에 위 빌딩 블록을 전부 붙인 '풀 컨텍스트' 복합 Provider로, `--exchange UFC`로 바로 선택할 수 있습니다. 틱마다 토큰이 크게 늘어나므로 연구·실험용으로 적합하고 실전에서는 `--term`을 충분히 길게(예: 300초) 조절하는 것을 권장합니다. 소스 구성을 직접 지정하려면 `UpbitFullContextDataProvider(..., providers=[...])`로 리스트를 넣으면 됩니다.

**Q. DataProvider가 캔들 말고 다른 것도 제공할 수 있나요?**
A. 네. `get_info()`는 `type` 필드로 구분되는 어떤 형식의 딕셔너리든 같은 리스트에 섞어 반환할 수 있습니다. 현재 내장된 타입은 `primary_candle`, `binance`, `news` 세 종류이며, `exchange_rate`·`notice` 같은 새 타입을 추가하려면 Provider만 새로 만들고 Factory에 등록하면 됩니다. LLM은 각 항목의 `type`을 보고 알아서 해석합니다.

**Q. 수수료는 어떻게 반영되나요?**
A. Trader 생성 시 `commission_ratio`(기본 0.0005 = 0.05%)가 포함되지만, 현재 SafetyGuard 계산은 수수료 제외입니다. 실제 수익률 확인은 거래소 잔고 또는 `get_performance` 결과를 기준으로 합니다.

---

## 4. 문제 해결 체크리스트

### 4.1 "시작했는데 아무 일도 안 일어납니다"

1. `start`를 입력했는지 확인 (입력하지 않으면 타이머 미기동)
2. `--term` 값이 너무 큰 것은 아닌지 (기본 60초)
3. `log/smtm.log` 확인 — LLM 호출 로그가 찍히는지
4. `SMTM_LLM_API_KEY`가 유효한지 (Anthropic 콘솔에서 잔액/권한 확인)

### 4.2 "`execute_trade`가 계속 실패합니다"

1. 거래소 키 환경변수 4종(UPBIT_OPEN_API_ACCESS_KEY 등) 확인
2. 거래소 시간 동기화 (NTP)
3. SafetyGuard 한도 초과 여부 — `log/smtm.log`에서 "1회 최대 거래금액 초과" 등 로그 검색
4. 거래소 원화 잔고가 주문 금액보다 큰지
5. 거래 페어(currency × exchange)가 실제로 존재하는지

### 4.3 "텔레그램 봇이 반응하지 않습니다"

1. `--token`과 `--chatid`가 맞는지 (`--chatid`는 내 개인 chat id여야 함)
2. 봇이 그 `chat_id`와 최소 한 번 대화한 적 있는지 (BotFather의 봇은 먼저 `/start`를 보내야 수신 가능)
3. 네트워크 방화벽이 `api.telegram.org`로의 아웃바운드를 막지 않았는지

### 4.4 "비용이 예상보다 큽니다"

1. `--term`을 늘려 틱 주기를 길게 (예: 300초)
2. `context.candle_count`를 줄여 매 틱당 전달되는 시장 데이터 축소
3. `max_conversation_turns`를 줄여 전송 이력 축소
4. 사용자 메시지 길이가 길면 시스템 프롬프트보다 사용자 메시지가 토큰을 더 먹을 수 있음 — 간결하게 대화

### 4.5 "프로세스가 죽었는데 상태가 이상합니다"

1. 현재 설계는 상태를 영속 저장하지 않음 — 재시작 후 일일 거래 카운터는 0부터
2. 거래소에는 이미 체결된 주문이 남아 있을 수 있음 — 거래소 콘솔에서 확인
3. 재시작 전에 `log/smtm.log`와 텔레그램 이력으로 마지막 상태 확인

---

## 5. 더 깊이 알고 싶을 때

- 아키텍처 상세 → [`architecture.md`](architecture.md)
- DataProvider 카탈로그(엔드포인트·필드·인증) → [`data-providers.md`](data-providers.md)
- 기능 명세 전체 목록 → [`requirements.md`](requirements.md)
- 코드 레벨 구조 → 저장소 루트 README 또는 `docs/wiki/`
