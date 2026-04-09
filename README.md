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
- Vendor-independent LLM client abstraction (Claude, OpenAI, Ollama)

## Setup

### Installation

```bash
git clone https://github.com/msaltnet/smtm.git
cd smtm
pip install -r requirements.txt
```

### Environment Variables

Create a `.env` file in the project root (or export variables directly):

```bash
# Required: LLM API key (Anthropic Claude)
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

## Architecture

**LlmOperator** replaces the traditional rule-based pipeline with a single chat interface:

- **DataProvider** -> Market Data Tool
- **Trader** -> Trade / Portfolio Tools  
- **Strategy** -> Knowledge documents (RAG)
- **Analyzer** -> SystemMonitor + Performance Tool

**More information 👉[Wiki](https://github.com/msaltnet/smtm/wiki)**
