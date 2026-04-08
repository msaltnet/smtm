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

## Architecture

**LlmOperator** replaces the traditional rule-based pipeline with a single chat interface:

- **DataProvider** -> Market Data Tool
- **Trader** -> Trade / Portfolio Tools  
- **Strategy** -> Knowledge documents (RAG)
- **Analyzer** -> SystemMonitor + Performance Tool

**More information 👉[Wiki](https://github.com/msaltnet/smtm/wiki)**
