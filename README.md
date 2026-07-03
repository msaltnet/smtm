# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

An LLM-powered autonomous cryptocurrency trading system made in Python. https://smtm.msalt.net

[한국어](https://github.com/msaltnet/smtm/blob/master/README-ko-kr.md) 👈

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

A chat-driven LLM agent orchestrates the system -- selecting a strategy, starting/stopping trading, and managing account profiles -- while a separate fixed-interval loop executes the actual trades.

1. SystemOperator (the chat agent) selects/switches strategies and starts or stops trading via tools
2. TradingOperator runs a fixed-interval loop: DataProvider -> Strategy -> SafetyGuard -> Trader -> Analyzer
3. Strategy is pluggable -- algorithmic (Buy & Hold, RSI, SMA) or a single LLM judgment per tick (`LLM`)
4. SafetyGuard enforces trading limits before every order; SystemMonitor independently logs all activity

## Features
- Chat-based orchestration agent: select a strategy, start/stop trading, manage account profiles
- Pluggable trading strategies executed on a fixed interval: Buy & Hold, RSI, SMA, or a single LLM judgment per tick (`LLM`)
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

You can also move run options into a JSON config file:

```bash
python -m smtm --config config/virtual-upbit.json
```

Supported config keys are `mode`, `budget`, `currency`, `exchange`, `virtual`, `paper`, `term`, `log`, `token`, and `chatid`. `virtual` is the recommended key for virtual trading; `paper` remains supported as a compatibility alias. `interval` is accepted as an alias for `term`, and `chat_id` is accepted as an alias for `chatid`. CLI arguments override config-file values.

You can also pick a trading strategy directly, or load a saved account profile:

```bash
# Run with an algorithmic strategy (no LLM call in the trading loop)
python -m smtm --mode 0 --strategy RSI --virtual --budget 500000

# Run with the LLM decision strategy
python -m smtm --mode 0 --strategy LLM --virtual

# Run with a saved account profile (config/profiles/<name>.json)
python -m smtm --mode 0 --profile my-btc-virtual
```

#### Example chat session

```
메시지를 입력하세요 (q: 종료): Switch to the RSI strategy
[Agent → select_strategy(RSI)]
Switched to the RSI strategy.

메시지를 입력하세요 (q: 종료): start
자동 매매가 시작되었습니다

메시지를 입력하세요 (q: 종료): Show my portfolio
[Agent → get_portfolio]
Cash: 495,000 KRW · BTC: 0.0001 · Current value: 500,000 KRW (0.0%)

메시지를 입력하세요 (q: 종료): stop
자동 매매가 중지되었습니다
```

### Telegram Chatbot Mode

```bash
python -m smtm --mode 1 --token <telegram_token> --chatid <chat_id>
```

Control trading through Telegram messenger. All messages are forwarded to the LLM.

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--config` | JSON config file path | None |
| `--mode` | 0: CLI interactive, 1: Telegram chatbot | (shows help) |
| `--budget` | Trading budget (KRW) | 500000 |
| `--currency` | Trading currency (e.g. BTC, ETH) | BTC |
| `--exchange` | Exchange code (UPB: Upbit, BTH: Bithumb) | UPB |
| `--strategy` | Trading strategy code (BNH, RSI, SMA, LLM) | BNH |
| `--profile` | Load a saved account profile from `config/profiles/` | None |
| `--virtual` / `--paper` | Virtual trading mode with real-time quotes and simulated balance | False |
| `--no-virtual` / `--no-paper` | Disable virtual trading when the config file enables it | False |
| `--term` | Trading tick interval in seconds | 60 |
| `--log` | Log file name | None |

### Virtual Trading

```bash
python -m smtm --mode 0 --budget 500000 --currency BTC --exchange UPB --virtual
python -m smtm --mode 0 --currency BTC --exchange UFC --virtual
```

Virtual trading keeps the selected DataProvider but routes orders to the in-memory `SimulationTrader` instead of a real exchange. Orders are not sent to the exchange; they are applied to a virtual account so portfolio value and returns can be inspected. Quotes are injected from the latest `primary_candle` close. State is in-memory only and commission is currently 0.

### Supported Exchanges & Data Providers

`--exchange` selects both the market data source and the order-placing trader. End-to-end trading requires a matching entry in both factories. Any code in this table can be combined with `--virtual` to route orders through `SimulationTrader` instead of the real exchange.

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

To override the defaults, pass a `safety` entry into the operator config when wiring `SystemOperator`:

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
- **SimulationTrader** — Production virtual-trading trader with real balance/asset state management
- **FakeDataProvider** — Returns static market candle data

All internal components (`SystemOperator`, `TradingOperator`, `ToolRouter`, `SafetyGuard`, `SystemMonitor`, all Strategies and Tools) run with real code.

## Architecture

The system is split into two layers:

- **SystemOperator** — chat-based LLM agent; orchestrates strategy selection, start/stop, and account profiles via Tools (does not trade directly)
- **TradingOperator** — fixed-interval loop: **DataProvider** -> **Strategy** -> **SafetyGuard** -> **Trader** -> **Analyzer**
- **Strategy** — pluggable: algorithmic (Buy & Hold, RSI, SMA) or a single LLM judgment per tick (`LLM`)
- **SystemMonitor** — independently logs all activity (market data, requests, results, safety events, LLM usage)

**More information 👉[Wiki](https://github.com/msaltnet/smtm/wiki)**
