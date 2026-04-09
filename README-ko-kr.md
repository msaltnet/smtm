# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

LLM 기반 자율 암호화폐 자동매매 프로그램. https://smtm.msalt.net

[English](https://github.com/msaltnet/smtm/blob/master/README.md) 👈

[![icon_wide_gold](https://github.com/user-attachments/assets/ef1651bf-87e4-4afc-9cd9-b3e2b5d0cd1a)](https://smtm.msalt.net/)

LLM이 자율적으로 시장 데이터를 분석하고, 매매 결정을 내리고, 도구를 통해 거래를 실행합니다. 간단한 채팅 인터페이스로 제어합니다.

1. LlmOperator가 주기적으로 시장 컨텍스트와 함께 LLM을 호출  
2. LLM이 자율적으로 도구를 호출 (시장 데이터, 거래, 포트폴리오 등)  
3. SafetyGuard가 도구 레벨에서 거래 제한을 강제  
4. SystemMonitor가 독립적으로 모든 활동을 기록  

## 주요기능
- LLM 기반 자율 매매 결정 (Tool Use)
- 안전 가드레일 (최대 거래 금액, 일일 거래 제한, 손실 비율 상한)
- CLI 인터랙티브 모드 및 텔레그램 챗봇 제어
- 전략 지식을 문서로 로딩 (SMA, RSI, Buy & Hold)
- 벤더 독립적 LLM 클라이언트 추상화 (Claude, OpenAI, Ollama)

## 설치

```bash
git clone https://github.com/msaltnet/smtm.git
cd smtm
pip install -r requirements.txt
```

### 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하거나 환경변수를 직접 설정합니다:

```bash
# 필수: LLM API 키 (Anthropic Claude)
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

### 텔레그램 챗봇 모드

```bash
python -m smtm --mode 1 --token <telegram_token> --chatid <chat_id>
```

텔레그램 메신저를 통해 거래를 제어합니다. 모든 메시지가 LLM에 전달됩니다.

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--mode` | 0: CLI 인터랙티브, 1: 텔레그램 챗봇 | (도움말 표시) |
| `--budget` | 거래 예산 (KRW) | 500000 |
| `--currency` | 거래 통화 (예: BTC, ETH) | BTC |
| `--exchange` | 거래소 코드 (UPB: 업비트, BTH: 빗썸) | UPB |
| `--term` | 거래 주기 (초) | 60 |
| `--log` | 로그 파일 이름 | None |

## Architecture

**LlmOperator**가 기존 규칙 기반 파이프라인을 단일 채팅 인터페이스로 대체:

- **DataProvider** -> Market Data Tool
- **Trader** -> Trade / Portfolio Tools
- **Strategy** -> Knowledge 문서 (RAG)
- **Analyzer** -> SystemMonitor + Performance Tool

**더 많은 정보는 👉[smtm wiki](https://github.com/msaltnet/smtm/wiki)**