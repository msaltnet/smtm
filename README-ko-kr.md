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

#### 채팅 예시

```
메시지를 입력하세요 (q: 종료): start
자동 매매가 시작되었습니다

메시지를 입력하세요 (q: 종료): BTC 시장 분석해서 괜찮으면 매수해줘
[LLM → get_market_data → execute_trade(buy, ...)]
상승 추세입니다. 50,000,000 KRW 부근에서 0.0001 BTC 매수 주문을 넣었습니다.

메시지를 입력하세요 (q: 종료): 포트폴리오 보여줘
[LLM → get_portfolio]
현금: 495,000 KRW · BTC: 0.0001 · 현재가치: 500,000 KRW (0.0%)

메시지를 입력하세요 (q: 종료): 전부 매도하고 중지
[LLM → execute_trade(sell, ...)]
0.0001 BTC를 매도했습니다. 자동 매매가 중지되었습니다.
```

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

### 지원 거래소 및 데이터 제공자

`--exchange`는 시장 데이터 소스와 주문 실행 Trader를 동시에 선택합니다. 실제 매매까지 가능하려면 두 Factory에 모두 등록되어 있어야 합니다.

| 코드 | Data Provider | Trader | 비고 |
|------|---------------|--------|------|
| `UPB` | Upbit | Upbit | 기본값 |
| `BTH` | Bithumb | Bithumb | |
| `BNC` | Binance | — | 데이터만 지원, Trader 미구현 |
| `UBD` | Upbit + Binance 병합 | — | 데이터만 지원, Trader 미구현 |

등록 위치: `smtm/data/data_provider_factory.py`, `smtm/trader/trader_factory.py`.

### 안전 가드레일

`SafetyGuard`는 모든 거래 Tool 호출을 실행 전에 검증하며 LLM이 우회할 수 없습니다. 기본값은 `smtm/llm/safety_guard.py`의 `SafetyConfig`에 정의되어 있습니다:

| 파라미터 | 설명 | 기본값 |
|----------|------|--------|
| `max_trade_amount` | 1회 최대 거래 금액 (KRW) | 100,000 |
| `max_daily_trades` | 하루 최대 거래 횟수 | 20 |
| `max_loss_ratio` | 누적 손실 한도 (음수 비율) | -0.20 (-20%) |
| `initial_budget` | 손실률 계산 기준이 되는 초기 예산 | `--budget` 값 |

기본값을 덮어쓰려면 `LlmOperator` 설정의 `safety` 항목으로 전달합니다:

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
- **FakeTrader** — 실제 잔고/자산 상태를 관리하는 거래소 시뮬레이터
- **FakeDataProvider** — 고정 시장 캔들 데이터 반환

내부 컴포넌트(`LlmOperator`, `ToolRouter`, `SafetyGuard`, `SystemMonitor`, 모든 Tool)는 실제 코드로 동작합니다.

## Architecture

**LlmOperator**가 기존 규칙 기반 파이프라인을 단일 채팅 인터페이스로 대체:

- **DataProvider** -> Market Data Tool
- **Trader** -> Trade / Portfolio Tools
- **Strategy** -> Knowledge 문서 (RAG)
- **Analyzer** -> SystemMonitor + Performance Tool

**더 많은 정보는 👉[smtm wiki](https://github.com/msaltnet/smtm/wiki)**