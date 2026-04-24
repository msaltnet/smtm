# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

An LLM-powered autonomous cryptocurrency trading system made in Python. https://smtm.msalt.net

[한국어](https://github.com/msaltnet/smtm/blob/master/README-ko-kr.md) 👈

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

LLM autonomously analyzes market data, makes trading decisions, and executes trades using tools -- all controlled through a simple chat interface.

1. LlmOperator periodically invokes the LLM with market context  
2. LLM autonomously calls tools (market data, trade, portfolio, etc.)  
3. SafetyGuard enforces trading limits at the tool level  
4. SystemMonitor independently logs all activity  

## Features
- LLM-powered autonomous trading decisions via tool use
- Safety guardrails (max trade amount, daily trade limit, loss ratio ceiling)
- CLI interactive mode and Telegram chatbot control
- Strategy knowledge loaded as documents (SMA, RSI, Buy & Hold)
- Pluggable LLM client interface — Claude is implemented; OpenAI / Ollama adapters are planned

## Setup

### Prerequisites
- Python 3.9 or higher

### Installation

```bash
git clone https://github.com/msaltnet/smtm.git
cd smtm
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root (or export variables directly):

```bash
# Required: LLM API key (currently Anthropic Claude — the only implemented vendor)
SMTM_LLM_API_KEY=your_anthropic_api_key

# Upbit exchange (when using --exchange UPB)
UPBIT_OPEN_API_ACCESS_KEY=your_upbit_access_key
UPBIT_OPEN_API_SECRET_KEY=your_upbit_secret_key
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb exchange (when using --exchange BTH)
BITHUMB_API_ACCESS_KEY=your_bithumb_access_key
BITHUMB_API_SECRET_KEY=your_bithumb_secret_key
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# Telegram (mode 1 only)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

### CLI Interactive Mode

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB
```

Chat with the LLM to control trading. Type messages to ask about the market, start/stop trading, or check portfolio status.

#### Example chat session

```
메시지를 입력하세요 (q: 종료): start
자동 매매가 시작되었습니다

메시지를 입력하세요 (q: 종료): Analyze the BTC market and buy if it looks good
[LLM → get_market_data → execute_trade(buy, ...)]
Market is in an uptrend. Placed a buy order for 0.0001 BTC at ~50,000,000 KRW.

메시지를 입력하세요 (q: 종료): Show my portfolio
[LLM → get_portfolio]
Cash: 495,000 KRW · BTC: 0.0001 · Current value: 500,000 KRW (0.0%)

메시지를 입력하세요 (q: 종료): Sell everything and stop
[LLM → execute_trade(sell, ...)]
Sold 0.0001 BTC. Trading stopped.
```

### Telegram Chatbot Mode

```bash
python -m smtm --mode 1 --token <telegram_token> --chatid <chat_id>
```

Control trading through Telegram messenger. All messages are forwarded to the LLM.

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--mode` | 0: CLI interactive, 1: Telegram chatbot | (shows help) |
| `--budget` | Trading budget (KRW) | 500000 |
| `--currency` | Trading currency (e.g. BTC, ETH) | BTC |
| `--exchange` | Exchange code (UPB: Upbit, BTH: Bithumb) | UPB |
| `--term` | Trading tick interval in seconds | 60 |
| `--log` | Log file name | None |

### Supported Exchanges & Data Providers

`--exchange` selects both the market data source and the order-placing trader. End-to-end trading requires a matching entry in both factories.

| Code | Data Provider | Trader | Notes |
|------|---------------|--------|-------|
| `UPB` | Upbit | Upbit | Default |
| `BTH` | Bithumb | Bithumb | |
| `BNC` | Binance | — | Data only; no trader yet |
| `UBD` | Upbit + Binance (merged) | — | Data only; no trader yet |
| `UPN` | Upbit + Crypto News RSS (CoinDesk) | Upbit | Candle + text news items in one feed |
| `UMN` | Upbit + Multi-source News (CoinDesk / CoinTelegraph / Decrypt / CryptoSlate) | Upbit | Candle + aggregated news from four sources |
| `USC` | Upbit + Multi News + Reddit + Fear & Greed Index | Upbit | Full social/sentiment snapshot alongside candle |
| `UFC` | Upbit + **all** public sources below (price / on-chain / funding / macro / notices / news / social / tech) | Upbit | Heaviest option — single "full context" feed per tick |

Registered in `smtm/data/data_provider_factory.py` and `smtm/trader/trader_factory.py`.

Building-block signal providers (use directly, not factory-registered). All use free public APIs with no key required:

| Class | `CODE` | `type` emitted | Source |
|-------|--------|----------------|--------|
| `NewsDataProvider` | `NWS` | `news` | Generic RSS (CoinDesk by default) |
| `CoinTelegraphNewsDataProvider` | `CTN` | `news` | `cointelegraph.com/rss` |
| `DecryptNewsDataProvider` | `DCN` | `news` | `decrypt.co/feed` |
| `CryptoSlateNewsDataProvider` | `CSN` | `news` | `cryptoslate.com/feed/` |
| `BitcoinMagazineNewsDataProvider` | `BMN` | `news` | `bitcoinmagazine.com/.rss/full/` |
| `TheBlockNewsDataProvider` | `TBN` | `news` | `theblock.co/rss.xml` — crypto/finance crossover |
| `WSJMarketsNewsDataProvider` | `WSJ` | `news` | `feeds.a.dj.com/rss/RSSMarketsMain.xml` — WSJ Markets |
| `MarketWatchNewsDataProvider` | `MWN` | `news` | `feeds.marketwatch.com/marketwatch/topstories/` |
| `CNBCFinanceNewsDataProvider` | `CNB` | `news` | `cnbc.com/id/10000664/device/rss/rss.html` — CNBC Markets |
| `MultiNewsDataProvider` | `MNS` | `news` | Aggregates multiple news sources |
| `RedditDataProvider` | `RDT` | `reddit` | Any subreddit Atom feed (`/r/{sub}/.rss`) |
| `CryptoCurrencyRedditDataProvider` | `RCC` | `reddit` | `r/CryptoCurrency` |
| `BitcoinRedditDataProvider` | `RBT` | `reddit` | `r/Bitcoin` |
| `FearGreedDataProvider` | `FGI` | `sentiment_index` | `api.alternative.me/fng/` (Crypto Fear & Greed) |
| `CoinGeckoDataProvider` | `CGK` | `price_snapshot` | `api.coingecko.com/api/v3/simple/price` — price / market cap / 24h volume / 24h change |
| `CoinCapDataProvider` | `CCP` | `price_snapshot` | `api.coincap.io/v2/assets/{id}` — alternative with higher rate limit |
| `CryptoGlobalDataProvider` | `CGL` | `crypto_global` | `api.coingecko.com/api/v3/global` — total market cap / BTC·ETH·stablecoin dominance |
| `YahooFinanceDataProvider` | `YFN` | `macro_market` | `query1.finance.yahoo.com/v8/finance/chart` — DXY / S&P500 / VIX / Gold / US10Y / Nasdaq |
| `BlockchainInfoDataProvider` | `BCI` | `onchain_stats` | `api.blockchain.info/stats` — BTC hash rate / difficulty / tx / mempool |
| `MempoolFeesDataProvider` | `MPF` | `mempool_fees` | `mempool.space/api/v1/fees/recommended` — BTC fee sat/vB |
| `EtherscanGasDataProvider` | `EGS` | `eth_gas` | `api.etherscan.io/api?module=gastracker&action=gasoracle` — ETH gas safe/propose/fast (gwei), optional key |
| `BinanceFundingRateDataProvider` | `BFR` | `funding_rate` | `fapi.binance.com/fapi/v1/premiumIndex` — perp funding / mark price |
| `BinanceOpenInterestDataProvider` | `BOI` | `open_interest` | `fapi.binance.com/futures/data/openInterestHist` — perp open interest (contracts + USD notional) |
| `BinanceLongShortRatioDataProvider` | `BLS` | `long_short_ratio` | `fapi.binance.com/futures/data/globalLongShortAccountRatio` — retail / top trader long vs short ratio |
| `UpbitNoticeDataProvider` | `UPT` | `notice` | `api-manager.upbit.com/api/v1/notices` — Upbit announcements |
| `ExchangeRateDataProvider` | `FXR` | `exchange_rate` | `open.er-api.com/v6/latest/USD` — USD → KRW/JPY/EUR/CNY |
| `HackerNewsDataProvider` | `HNS` | `hackernews` | `hn.algolia.com/api/v1/search_by_date` — crypto stories |

`DataProvider.get_info()` may return a mixed list of typed dicts — numeric types such as `primary_candle`, `binance`, `price_snapshot`, `crypto_global`, `macro_market`, `onchain_stats`, `mempool_fees`, `eth_gas`, `funding_rate`, `open_interest`, `long_short_ratio`, `exchange_rate`, `sentiment_index`, and text / social types such as `news`, `reddit`, `hackernews`, `notice`. Each dict is self-describing via its `type` field; see `smtm/data/data_provider.py` for the contract and `UpbitNewsDataProvider` (`UPN`) / `UpbitMultiNewsDataProvider` (`UMN`) / `UpbitSocialDataProvider` (`USC`) / `UpbitFullContextDataProvider` (`UFC`) for working multi-type examples.

### Safety Guardrails

`SafetyGuard` validates every trade tool call before execution and cannot be bypassed by the LLM. Defaults are defined in `smtm/llm/safety_guard.py` (`SafetyConfig`):

| Parameter | Description | Default |
|-----------|-------------|---------|
| `max_trade_amount` | Max KRW value of a single trade | 100,000 |
| `max_daily_trades` | Max number of trades per calendar day | 20 |
| `max_loss_ratio` | Cumulative loss floor (negative ratio) | -0.20 (-20%) |
| `initial_budget` | Baseline for loss-ratio calculation | value of `--budget` |

To override the defaults, pass a `safety` entry into the operator config when wiring `LlmOperator`:

```python
config = {
    "budget": 500000,
    "safety": {
        "max_trade_amount": 50000,
        "max_daily_trades": 10,
        "max_loss_ratio": -0.10,
    },
}
operator = LlmOperator(llm_client, config)
```

## Testing

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run all tests
python -m pytest tests/

# Run by category
python -m pytest tests/unit_tests/          # Unit tests
python -m pytest tests/e2e_tests/           # E2E tests
python -m pytest tests/integration_tests/   # Integration tests (requires API keys)
```

### Test Structure

| Directory | Description | External APIs |
|-----------|-------------|---------------|
| `tests/unit_tests/` | Individual component tests | All mocked |
| `tests/e2e_tests/` | Full pipeline tests (chat → tool → trade → result) | LLM, exchange, market data are Fake; all internal components run real code |
| `tests/integration_tests/` | Real exchange API tests | Requires API keys |

### E2E Tests

E2E tests verify the complete flow without calling any external APIs. Only the system boundary is replaced with Fake implementations:

- **FakeLlmClient** — Returns pre-scripted LLM responses (tool calls and text)
- **FakeTrader** — Simulates exchange with real balance/asset state management
- **FakeDataProvider** — Returns static market candle data

All internal components (`LlmOperator`, `ToolRouter`, `SafetyGuard`, `SystemMonitor`, all Tools) run with real code.

## Architecture

**LlmOperator** replaces the traditional rule-based pipeline with a single chat interface:

- **DataProvider** -> Market Data Tool
- **Trader** -> Trade / Portfolio Tools  
- **Strategy** -> Knowledge documents (RAG)
- **Analyzer** -> SystemMonitor + Performance Tool

**More information 👉[Wiki](https://github.com/msaltnet/smtm/wiki)**
