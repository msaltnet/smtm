# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

An AI Agent-powered autonomous cryptocurrency trading system made in Python. https://smtm.msalt.net

[한국어](https://github.com/msaltnet/smtm/blob/master/README-ko-kr.md) 👈

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

A chat-driven AI Agent orchestrates the system -- registering accounts, managing profiles, and starting/stopping one or more trading sessions in parallel -- while each session runs its own separate fixed-interval loop that executes the actual trades.

1. SystemOperator (the chat agent) manages sessions via tools -- create/start/stop/compare -- and still supports the legacy single-session select/start/stop flow
2. Each session's TradingOperator runs a fixed-interval loop: DataProvider -> Strategy -> SafetyGuard -> Trader -> Analyzer
3. Strategy is pluggable -- algorithmic (Buy & Hold, RSI, SMA) or a single LLM judgment per tick (`LLM`)
4. SafetyGuard enforces trading limits before every order (with an account-level guard across sessions sharing an account); SystemMonitor independently logs all activity, tagged by session

## Features
- Chat-based orchestration agent: register accounts, manage profiles, and create/start/stop parallel trading sessions
- Pluggable trading strategies executed on a fixed interval: Buy & Hold, RSI, SMA, or a single LLM judgment per tick (`LLM`)
- Safety guardrails (max trade amount, daily trade limit, loss ratio ceiling)
- Telegram chatbot control
- Uses the implemented trading strategy modules (Buy & Hold, RSI, SMA); for the `LLM` strategy, strategy knowledge from `smtm/strategies/*.md` is injected into the prompt to inform its decisions
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
# Required: LLM API key (currently Anthropic Claude is the only implemented vendor)
SMTM_LLM_API_KEY=your_anthropic_api_key

# Upbit exchange (exchange code UPB)
UPBIT_OPEN_API_ACCESS_KEY=your_upbit_access_key
UPBIT_OPEN_API_SECRET_KEY=your_upbit_secret_key
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb exchange (exchange code BTH)
BITHUMB_API_ACCESS_KEY=your_bithumb_access_key
BITHUMB_API_SECRET_KEY=your_bithumb_secret_key
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# Telegram (can be passed as --token / --chatid instead)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

Telegram is the only entry point. Start the bot and control everything by chatting with it.

```bash
python -m smtm --token <telegram_token> --chatid <chat_id>
```

If `--token` / `--chatid` are omitted, `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` are used. Without a usable token the process prints `Please check your telegram chat-bot token` and exits.

Only messages from the given `chat_id` are accepted; everything else is ignored. All accepted messages are forwarded to the LLM agent.

### Paper trading by default

The `default` session that boots with the process is a **paper-trading (virtual) session** -- real-time quotes, simulated balance, no order ever reaches the exchange.

To trade for real, do the following **through chat**:

1. `register_account` -- register an account by the *names* of the env vars holding the keys (never the key values).
2. `create_profile` -- create a profile with `virtual: false` and an `account`.
3. `create_session` + `start_session` -- create a session from that profile and start it.

### Settings are chat settings, not flags

Budget, currency, exchange, tick interval (`term`), and strategy are **profile/session settings** set through chat -- they are not command-line flags. Ask the agent to create or update a profile instead.

```
Create a profile called my-btc: exchange UPB, currency BTC, budget 500000, strategy RSI, term 60, virtual true
Create a session from my-btc and start it
Show my portfolio
Compare the performance of my sessions
```

### Options

| Option | Description | Default |
|--------|-------------|---------|
| `--token` | Telegram bot token | `TELEGRAM_BOT_TOKEN` |
| `--chatid` | Telegram chat id | `TELEGRAM_CHAT_ID` |
| `--log` | Log file name | None (`log/smtm.log`) |
| `--version` | Print version and exit | - |

### Virtual Trading

Virtual (paper) trading is the default for the `default` session, and any profile can enable it with the `virtual` setting.

Virtual trading keeps the selected DataProvider but routes orders to the in-memory `SimulationTrader` instead of a real exchange. Orders are not sent to the exchange; they are applied to a virtual account so portfolio value and returns can be inspected. Quotes are injected from the latest `primary_candle` close. State is in-memory only and commission is currently 0.

### Supported Exchanges & Data Providers

The `exchange` profile setting selects both the market data source and the order-placing trader. End-to-end trading requires a matching entry in both factories. Any code in this table can be combined with the `virtual` setting to route orders through `SimulationTrader` instead of the real exchange.

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
| `initial_budget` | Baseline for loss-ratio calculation | the session's `budget` setting |

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

The system is split into two layers, coordinated by a SessionManager that runs one or more sessions in parallel:

- **SystemOperator** — chat-based AI Agent; orchestrates account registration, profiles, and session lifecycle via Tools (does not trade directly)
- **SessionManager** — owns all `TradingSession`s (default session plus any created via chat); validates budgets against real account balances and prevents duplicate (account, symbol) allocations
- **TradingOperator** — one per session; fixed-interval loop: **DataProvider** -> **Strategy** -> **SafetyGuard** -> **Trader** -> **Analyzer**
- **Strategy** — pluggable: algorithmic (Buy & Hold, RSI, SMA) or a single LLM judgment per tick (`LLM`)
- **SystemMonitor** — independently logs all activity (market data, requests, results, safety events, LLM usage), tagged by session

### Multi-Session Parallel Trading

Run multiple strategies across accounts and symbols in parallel — all
controlled by chatting with the agent:

- Register accounts by env-var *names* (`SMTM_KEY_1`...), never raw keys
- Create profiles (strategy × exchange × symbol × budget × account)
- `create_session` / `start_session` / `compare_performance` via chat
- Per-session budgets are validated against the real account balance,
  and an account-level guard caps daily trades across sessions
- Designed for a handful of concurrent sessions — each session polls the exchange independently, so keep session count modest to respect API rate limits

**More information 👉[Wiki](https://github.com/msaltnet/smtm/wiki)**
