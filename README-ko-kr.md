# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

LLM 기반 자율 암호화폐 자동매매 프로그램. https://smtm.msalt.net

[English](https://github.com/msaltnet/smtm/blob/master/README.md) 👈

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

채팅으로 제어하는 LLM 에이전트가 계좌 등록, 프로파일 관리, 하나 이상의 매매 세션 병렬 시작/중지를 담당하고, 실제 매매는 각 세션마다 별도의 고정 주기 루프가 수행합니다.

1. SystemOperator(채팅 에이전트)가 Tool을 통해 세션을 생성/시작/중지/비교하며, 기존 단일 세션 select/start/stop 흐름도 그대로 지원  
2. 각 세션의 TradingOperator가 고정 주기 루프를 실행: DataProvider -> Strategy -> SafetyGuard -> Trader -> Analyzer  
3. Strategy는 교체 가능 — 알고리즘 전략(Buy & Hold, RSI, SMA) 또는 매 틱 LLM 판단 1회(`LLM`)  
4. SafetyGuard가 모든 주문 전에 거래 제한을 강제하고(같은 계좌를 공유하는 세션 간에는 계좌 단위 가드도 함께 적용), SystemMonitor가 세션별로 태깅하여 독립적으로 모든 활동을 기록  

## 주요기능
- 채팅 기반 오케스트레이션 에이전트: 계좌 등록, 프로파일 관리, 매매 세션 병렬 생성/시작/중지
- 고정 주기로 실행되는 교체 가능한 매매 전략: Buy & Hold, RSI, SMA, 또는 매 틱 LLM 판단 1회(`LLM`)
- 안전 가드레일 (최대 거래 금액, 일일 거래 제한, 손실 비율 상한)
- CLI 인터랙티브 모드 및 텔레그램 챗봇 제어
- 전략 지식을 문서로 로딩 (SMA, RSI, Buy & Hold)
- 교체 가능한 LLM 클라이언트 인터페이스 — 현재 Claude 구현. OpenAI / Ollama 어댑터는 예정

## 설치

### 사전 요구 사항
- Python 3.9 이상

```bash
git clone https://github.com/msaltnet/smtm.git
cd smtm
pip install -r requirements.txt
```

### 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하거나 환경변수를 직접 설정합니다:

```bash
# 필수: LLM API 키 (현재 구현된 벤더는 Anthropic Claude 하나입니다)
SMTM_LLM_API_KEY=your_anthropic_api_key

# Upbit 거래소 (--exchange UPB 사용 시)
UPBIT_OPEN_API_ACCESS_KEY=your_upbit_access_key
UPBIT_OPEN_API_SECRET_KEY=your_upbit_secret_key
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb 거래소 (--exchange BTH 사용 시)
BITHUMB_API_ACCESS_KEY=your_bithumb_access_key
BITHUMB_API_SECRET_KEY=your_bithumb_secret_key
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# 텔레그램 (mode 1 전용)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## 사용법

### CLI 인터랙티브 모드

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB
```

LLM과 채팅하며 거래를 제어합니다. 시장 분석, 거래 시작/중지, 포트폴리오 확인 등을 메시지로 요청할 수 있습니다.

실행 옵션은 JSON 설정 파일로 옮길 수도 있습니다:

```bash
python -m smtm --config config/virtual-upbit.json
```

지원하는 설정 키는 `mode`, `budget`, `currency`, `exchange`, `virtual`, `paper`, `term`, `strategy`, `log`, `token`, `chatid`입니다. 가상거래에는 `virtual` 사용을 권장하며, `paper`는 호환용 별칭으로 계속 지원합니다. `interval`은 `term`의 별칭으로, `chat_id`는 `chatid`의 별칭으로 사용할 수 있습니다. CLI 인자를 함께 주면 설정 파일 값보다 우선합니다.

전략을 직접 지정하거나, 저장된 계좌 프로파일을 불러올 수도 있습니다:

```bash
# 알고리즘 전략으로 실행 (매매 루프에서 LLM을 호출하지 않음)
python -m smtm --mode 0 --strategy RSI --virtual --budget 500000

# LLM 판단 전략으로 실행
python -m smtm --mode 0 --strategy LLM --virtual

# 저장된 계좌 프로파일로 실행 (config/profiles/<name>.json)
python -m smtm --mode 0 --profile my-btc-virtual
```

#### 채팅 예시

```
메시지를 입력하세요 (q: 종료): RSI 전략으로 바꿔줘
[Agent → select_strategy(RSI)]
RSI 전략으로 변경했습니다.

메시지를 입력하세요 (q: 종료): start
자동 매매가 시작되었습니다

메시지를 입력하세요 (q: 종료): 포트폴리오 보여줘
[Agent → get_portfolio]
현금: 495,000 KRW · BTC: 0.0001 · 현재가치: 500,000 KRW (0.0%)

메시지를 입력하세요 (q: 종료): stop
자동 매매가 중지되었습니다
```

### 텔레그램 챗봇 모드

```bash
python -m smtm --mode 1 --token <telegram_token> --chatid <chat_id>
```

텔레그램 메신저를 통해 거래를 제어합니다. 모든 메시지가 LLM에 전달됩니다.

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--config` | JSON 설정 파일 경로 | None |
| `--mode` | 0: CLI 인터랙티브, 1: 텔레그램 챗봇 | (도움말 표시) |
| `--budget` | 거래 예산 (KRW) | 500000 |
| `--currency` | 거래 통화 (예: BTC, ETH) | BTC |
| `--exchange` | 거래소 코드 (UPB: 업비트, BTH: 빗썸) | UPB |
| `--strategy` | 매매 전략 코드 (BNH, RSI, SMA, LLM) | BNH |
| `--profile` | `config/profiles/`에 저장된 계좌 프로파일 로드 | None |
| `--virtual` / `--paper` | 가상거래 모드 (실시간 시세 + 가상 잔고) | False |
| `--no-virtual` / `--no-paper` | 설정 파일에서 켠 가상거래 모드를 CLI에서 끔 | False |
| `--term` | 거래 주기 (초) | 60 |
| `--log` | 로그 파일 이름 | None |

### 가상거래

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB --virtual
python -m smtm --mode 0 --currency BTC --exchange UFC --virtual
```

가상거래 모드는 선택한 DataProvider는 그대로 쓰되, 실제 거래소로 주문을 전송하지 않고 인메모리 `SimulationTrader`의 가상계좌에서 매매를 처리합니다. 그래서 가상 잔고, 보유 자산, 포트폴리오 가치, 수익률을 확인할 수 있습니다. 시세는 최신 `primary_candle` 종가에서 주입되며, 상태는 메모리에만 저장됩니다. 현재 시뮬레이션 수수료는 0입니다.

### 지원 거래소 및 데이터 제공자

`--exchange`는 시장 데이터 소스와 주문 실행 Trader를 동시에 선택합니다. 실제 매매까지 가능하려면 두 Factory에 모두 등록되어 있어야 합니다. 이 표의 모든 코드는 `--virtual`과 결합해 실제 거래소 대신 `SimulationTrader`로 주문을 보낼 수 있습니다.

| 코드 | Data Provider | Trader | 비고 |
|------|---------------|--------|------|
| `UPB` | Upbit | Upbit | 기본값 |
| `BTH` | Bithumb | Bithumb | |
| `BNC` | Binance | — | 데이터만 지원, Trader 미구현 |
| `UBD` | Upbit + Binance 병합 | — | 데이터만 지원, Trader 미구현 |
| `UPN` | Upbit + 암호화폐 뉴스 RSS(CoinDesk) | Upbit | 캔들 + 텍스트형 뉴스 항목을 함께 제공 |
| `UMN` | Upbit + 다중 소스 뉴스(CoinDesk / CoinTelegraph / Decrypt / CryptoSlate) | Upbit | 캔들 + 네 곳의 뉴스를 집계해 제공 |
| `USC` | Upbit + 다중 뉴스 + Reddit + Fear & Greed 지수 | Upbit | 캔들과 함께 소셜·감정 지표까지 한 번에 제공 |
| `UFC` | Upbit + **모든 공개 소스**(가격·온체인·펀딩·매크로·공지·뉴스·소셜·테크) | Upbit | 가장 무거운 옵션 — 한 틱에 "풀 컨텍스트"를 한 번에 전달 |

등록 위치: `smtm/data/data_provider_factory.py`, `smtm/trader/trader_factory.py`.

Factory에 등록하지 않고 직접 코드로 사용하는 빌딩 블록형 Provider. 모두 무료 공개 API이며 키가 필요 없습니다:

| 클래스 | `CODE` | 반환 `type` | 소스 |
|--------|--------|------------|------|
| `NewsDataProvider` | `NWS` | `news` | 범용 RSS(기본 CoinDesk) |
| `CoinTelegraphNewsDataProvider` | `CTN` | `news` | `cointelegraph.com/rss` |
| `DecryptNewsDataProvider` | `DCN` | `news` | `decrypt.co/feed` |
| `CryptoSlateNewsDataProvider` | `CSN` | `news` | `cryptoslate.com/feed/` |
| `BitcoinMagazineNewsDataProvider` | `BMN` | `news` | `bitcoinmagazine.com/.rss/full/` |
| `TheBlockNewsDataProvider` | `TBN` | `news` | `theblock.co/rss.xml` — 크립토·금융 교차 보도 |
| `WSJMarketsNewsDataProvider` | `WSJ` | `news` | `feeds.a.dj.com/rss/RSSMarketsMain.xml` — WSJ Markets |
| `MarketWatchNewsDataProvider` | `MWN` | `news` | `feeds.marketwatch.com/marketwatch/topstories/` |
| `CNBCFinanceNewsDataProvider` | `CNB` | `news` | `cnbc.com/id/10000664/device/rss/rss.html` — CNBC Markets |
| `MultiNewsDataProvider` | `MNS` | `news` | 여러 뉴스 소스 합산 |
| `RedditDataProvider` | `RDT` | `reddit` | 임의 서브레딧 Atom 피드(`/r/{sub}/.rss`) |
| `CryptoCurrencyRedditDataProvider` | `RCC` | `reddit` | `r/CryptoCurrency` |
| `BitcoinRedditDataProvider` | `RBT` | `reddit` | `r/Bitcoin` |
| `FearGreedDataProvider` | `FGI` | `sentiment_index` | `api.alternative.me/fng/` (Crypto Fear & Greed) |
| `CoinGeckoDataProvider` | `CGK` | `price_snapshot` | `api.coingecko.com/api/v3/simple/price` — 가격/시총/24h거래량/변동률 |
| `CoinCapDataProvider` | `CCP` | `price_snapshot` | `api.coincap.io/v2/assets/{id}` — CoinGecko 백업(rate limit 더 관대) |
| `CryptoGlobalDataProvider` | `CGL` | `crypto_global` | `api.coingecko.com/api/v3/global` — 전체 시총 / BTC·ETH·스테이블 도미넌스 |
| `YahooFinanceDataProvider` | `YFN` | `macro_market` | `query1.finance.yahoo.com/v8/finance/chart` — DXY / S&P500 / VIX / Gold / US10Y / Nasdaq |
| `BlockchainInfoDataProvider` | `BCI` | `onchain_stats` | `api.blockchain.info/stats` — BTC 해시레이트/난이도/거래수/멤풀 |
| `MempoolFeesDataProvider` | `MPF` | `mempool_fees` | `mempool.space/api/v1/fees/recommended` — BTC 수수료 sat/vB |
| `EtherscanGasDataProvider` | `EGS` | `eth_gas` | `api.etherscan.io/api?module=gastracker&action=gasoracle` — ETH 가스 safe/propose/fast(gwei), 키 선택 |
| `BinanceFundingRateDataProvider` | `BFR` | `funding_rate` | `fapi.binance.com/fapi/v1/premiumIndex` — 선물 펀딩비/마크가격 |
| `BinanceOpenInterestDataProvider` | `BOI` | `open_interest` | `fapi.binance.com/futures/data/openInterestHist` — 선물 누적 미결제약정(계약수·USD 환산) |
| `BinanceLongShortRatioDataProvider` | `BLS` | `long_short_ratio` | `fapi.binance.com/futures/data/globalLongShortAccountRatio` — 선물 롱/숏 계정 비율(리테일·상위) |
| `UpbitNoticeDataProvider` | `UPT` | `notice` | `api-manager.upbit.com/api/v1/notices` — Upbit 공지 |
| `ExchangeRateDataProvider` | `FXR` | `exchange_rate` | `open.er-api.com/v6/latest/USD` — USD→KRW/JPY/EUR/CNY |
| `HackerNewsDataProvider` | `HNS` | `hackernews` | `hn.algolia.com/api/v1/search_by_date` — 크립토 스토리 |

`DataProvider.get_info()`는 `type` 키로 구분되는 여러 형식의 딕셔너리를 하나의 리스트로 반환할 수 있습니다. `primary_candle`·`binance`·`price_snapshot`·`crypto_global`·`macro_market`·`onchain_stats`·`mempool_fees`·`eth_gas`·`funding_rate`·`open_interest`·`long_short_ratio`·`exchange_rate`·`sentiment_index` 같은 수치형뿐 아니라 `news`·`reddit`·`hackernews`·`notice` 같은 텍스트·소셜형도 혼합할 수 있으며, 각 딕셔너리는 `type` 필드로 자기 스키마를 표시합니다. 계약 정의는 `smtm/data/data_provider.py`, 다중 타입 실구현 예시는 `UpbitNewsDataProvider`(`UPN`) · `UpbitMultiNewsDataProvider`(`UMN`) · `UpbitSocialDataProvider`(`USC`) · `UpbitFullContextDataProvider`(`UFC`)를 참고하세요.

### 안전 가드레일

`SafetyGuard`는 모든 거래 Tool 호출을 실행 전에 검증하며 LLM이 우회할 수 없습니다. 기본값은 `smtm/llm/safety_guard.py`의 `SafetyConfig`에 정의되어 있습니다:

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `max_trade_amount` | 1회 최대 거래 금액 (KRW) | 100,000 |
| `max_daily_trades` | 하루 최대 거래 횟수 | 20 |
| `max_loss_ratio` | 누적 손실 한도 (음수 비율) | -0.20 (-20%) |
| `initial_budget` | 손실률 계산 기준이 되는 초기 예산 | `--budget` 값 |

기본값을 덮어쓰려면 `SystemOperator` 설정의 `safety` 항목으로 전달합니다:

```python
config = {
    "budget": 500000,
    "safety": {
        "max_trade_amount": 50000,
        "max_daily_trades": 10,
        "max_loss_ratio": -0.10,
    },
}
operator = SystemOperator(llm_client, config)
```

## 테스트

```bash
# 개발 의존성 설치
pip install -r requirements-dev.txt

# 전체 테스트 실행
python -m pytest tests/

# 카테고리별 실행
python -m pytest tests/unit_tests/          # 단위 테스트
python -m pytest tests/e2e_tests/           # E2E 테스트
python -m pytest tests/integration_tests/   # 통합 테스트 (API 키 필요)
```

### 테스트 구조

| 디렉토리 | 설명 | 외부 API |
|----------|------|----------|
| `tests/unit_tests/` | 개별 컴포넌트 테스트 | 전부 mock |
| `tests/e2e_tests/` | 전체 파이프라인 테스트 (채팅 → 도구 → 거래 → 결과) | LLM, 거래소, 시장 데이터만 Fake. 내부 컴포넌트는 전부 실제 코드 |
| `tests/integration_tests/` | 실제 거래소 API 테스트 | API 키 필요 |

### E2E 테스트

E2E 테스트는 외부 API 호출 없이 전체 흐름을 검증합니다. 시스템 경계만 Fake로 대체됩니다:

- **FakeLlmClient** — 미리 정의된 LLM 응답(도구 호출, 텍스트)을 순서대로 반환
- **SimulationTrader** — 실제 잔고/자산 상태를 관리하는 프로덕션 가상거래 Trader
- **FakeDataProvider** — 고정 시장 캔들 데이터 반환

내부 컴포넌트(`SystemOperator`, `TradingOperator`, `ToolRouter`, `SafetyGuard`, `SystemMonitor`, 모든 Strategy와 Tool)는 실제 코드로 동작합니다.

## Architecture

시스템은 2계층으로 나뉘며, SessionManager가 하나 이상의 세션을 병렬로 조율합니다:

- **SystemOperator** — 채팅 기반 LLM 에이전트. Tool을 통해 계좌 등록, 프로파일, 세션 수명 주기를 오케스트레이션 (직접 매매하지 않음)
- **SessionManager** — 모든 `TradingSession`(default 세션 + 채팅으로 생성한 세션)을 소유. 예산을 실제 계좌 잔고와 대조 검증하고 (계좌, 심볼) 중복 할당을 방지
- **TradingOperator** — 세션당 1개; 고정 주기 루프: **DataProvider** -> **Strategy** -> **SafetyGuard** -> **Trader** -> **Analyzer**
- **Strategy** — 교체 가능: 알고리즘 전략(Buy & Hold, RSI, SMA) 또는 매 틱 LLM 판단 1회(`LLM`)
- **SystemMonitor** — 모든 활동(시장 데이터, 요청, 결과, 안전 이벤트, LLM 사용량)을 세션별로 태깅하여 독립적으로 기록

### 멀티 세션 병렬 매매

여러 전략을 여러 계좌·심볼에 걸쳐 동시에 실행할 수 있습니다 — 모두
에이전트와의 채팅으로 제어합니다:

- 계좌는 환경변수 *이름*으로만 등록합니다 (`SMTM_KEY_1` 등), 키 원문은 저장하지 않습니다
- 프로파일 생성 (전략 × 거래소 × 심볼 × 예산 × 계좌)
- 채팅으로 `create_session` / `start_session` / `compare_performance` 호출
- 세션별 예산은 실제 계좌 잔고와 대조 검증되며, 계좌 단위 가드가
  세션 전체에 걸친 일일 거래 한도를 관리합니다
- 세션마다 거래소를 독립 폴링하므로, API 호출 한도를 고려해 소수의 세션 운영을 전제로 합니다

**더 많은 정보는 👉[smtm wiki](https://github.com/msaltnet/smtm/wiki)**
