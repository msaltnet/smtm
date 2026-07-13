# 설치 및 사용 방법

Python 3.9 이상이 필요합니다. 소스 코드를 내려받고 관련 패키지를 설치하세요.

```
git clone https://github.com/msaltnet/smtm.git
cd smtm
pip install -r requirements.txt
```

시스템 수정 및 개발을 원할 때는 개발 관련 패키지도 설치하세요.

```
pip install -r requirements-dev.txt
```

## 환경변수 설정

프로젝트 루트에 `.env` 파일을 생성하거나 환경변수를 직접 설정합니다.

```
# 필수: LLM API 키 (현재 구현된 벤더는 Anthropic Claude 하나입니다)
SMTM_LLM_API_KEY=your_anthropic_api_key

# Upbit 거래소 (거래소 코드 UPB) - 실거래 시 필요
UPBIT_OPEN_API_ACCESS_KEY=your_upbit_access_key
UPBIT_OPEN_API_SECRET_KEY=your_upbit_secret_key
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb 거래소 (거래소 코드 BTH) - 실거래 시 필요
BITHUMB_API_ACCESS_KEY=your_bithumb_access_key
BITHUMB_API_SECRET_KEY=your_bithumb_secret_key
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# 텔레그램 (--token / --chatid 로 대신 전달 가능)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

`SMTM_LLM_API_KEY`는 필수이며, 없으면 부팅이 중단됩니다. 거래소 API 키는 실거래 세션을 만들 때만 필요하고, 기본 가상거래에는 필요하지 않습니다.

## 실행 방법

제어 채널은 텔레그램 하나입니다. 봇을 띄운 뒤 모든 조작을 채팅으로 합니다.

```
python -m smtm --token <telegram_token> --chatid <chat_id>
```

`--token` / `--chatid`를 생략하면 환경변수 `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID`를 사용합니다. 사용 가능한 토큰이나 대화방 아이디가 없으면 `Please check your telegram settings: ...` 메시지를 출력하고 종료합니다.

지정한 `chat_id`의 메시지만 수용하고 나머지는 무시합니다. 수용된 메시지는 모두 AI Agent에 전달됩니다.

### 부팅 후 콘솔 안내

정상적으로 부팅되면 콘솔에 아래와 같은 안내가 출력됩니다. (`SMTM_LLM_API_KEY`가 없으면 이 단계에 도달하지 못하고 종료됩니다.)

```
##### smtm telegram LLM controller is started #####
'start'를 입력하면 default 세션 매매가 시작됩니다
default 세션은 가상거래입니다 - 실제 주문은 전송되지 않습니다
실거래는 채팅으로 계좌를 등록한 뒤 세션을 만들어 시작하세요
```

이후에는 텔레그램 대화방에서 채팅으로 조작합니다.

### 기본은 가상거래

프로세스와 함께 뜨는 `default` 세션은 **가상거래(페이퍼 트레이딩) 세션**입니다. 실시간 시세를 쓰되 잔고는 가상이며, 주문이 거래소로 나가지 않습니다. 기본값은 거래소 UPB, 통화 BTC, 예산 500000, 주기 60초, 전략 BNH입니다.

실거래를 하려면 **채팅으로** 다음을 진행합니다.

1. `register_account` — 키 '값'이 아니라 키가 담긴 환경변수 '이름'으로 계좌를 등록합니다.
2. `create_profile` — `virtual: false`와 `account`를 지정한 프로파일을 만듭니다.
3. `create_session` + `start_session` — 그 프로파일로 세션을 만들고 시작합니다.

### 설정은 플래그가 아니라 채팅으로

예산(budget), 통화(currency), 거래소(exchange), 매매 주기(term), 전략(strategy), 가상여부(virtual)는 모두 **프로파일/세션 설정값**이며 명령행 플래그가 아닙니다. 에이전트에게 프로파일 생성·수정을 요청하세요.

```
my-btc 프로파일 만들어줘: 거래소 UPB, 통화 BTC, 예산 500000, 전략 RSI, 주기 60초, 가상거래
my-btc로 세션 만들고 시작해줘
포트폴리오 보여줘
세션별 성과 비교해줘
```

### 옵션

| 옵션 | 설명 | 기본값 |
|------|------|--------|
| `--token` | 텔레그램 봇 토큰 | `TELEGRAM_BOT_TOKEN` |
| `--chatid` | 텔레그램 chat id | `TELEGRAM_CHAT_ID` |
| `--log` | 로그 파일 이름 | None (`log/smtm.log`) |
| `--version` | 버전 출력 후 종료 | - |

### 프로그램/Jupyter에서 사용 (JptController)

텔레그램 없이 파이썬 코드나 Jupyter 노트북에서 직접 제어하려면 `JptController`를 사용합니다.

```python
from smtm import JptController

controller = JptController(interval=60, budget=500000, currency="BTC")
controller.initialize(interval=60, budget=500000, exchange="UPB")
controller.chat("포트폴리오 보여줘")
controller.start()   # 자동 매매 시작
controller.stop()    # 자동 매매 중지
JptController.set_log_level(20)  # 로그 레벨 (10/20/30/40)
```

⚠️ 텔레그램의 default 세션과 달리, `JptController.initialize()`는 **실거래(virtual=False)** 로 부팅하며 거래소 API 키가 필요합니다. 가상거래가 아니므로 실제 주문이 거래소로 전송될 수 있으니 주의하세요.


# How to setup and run

Python 3.9 or higher is required. Clone the source and install the packages.

```
git clone https://github.com/msaltnet/smtm.git
cd smtm
pip install -r requirements.txt
```

For development, install the development dependencies too.

```
pip install -r requirements-dev.txt
```

## Environment Variables

Create a `.env` file in the project root (or export variables directly).

```
# Required: LLM API key (currently Anthropic Claude — the only implemented vendor)
SMTM_LLM_API_KEY=your_anthropic_api_key

# Upbit exchange (exchange code UPB) - needed for real trading
UPBIT_OPEN_API_ACCESS_KEY=your_upbit_access_key
UPBIT_OPEN_API_SECRET_KEY=your_upbit_secret_key
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com

# Bithumb exchange (exchange code BTH) - needed for real trading
BITHUMB_API_ACCESS_KEY=your_bithumb_access_key
BITHUMB_API_SECRET_KEY=your_bithumb_secret_key
BITHUMB_API_SERVER_URL=https://api.bithumb.com

# Telegram (can be passed as --token / --chatid instead)
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

`SMTM_LLM_API_KEY` is required — the process aborts without it. Exchange API keys are only needed when you create a real-trading session; the default paper-trading session does not require them.

## How to run

Telegram is the only entry point. Start the bot and control everything by chatting with it.

```
python -m smtm --token <telegram_token> --chatid <chat_id>
```

If `--token` / `--chatid` are omitted, `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` are used. Without a usable token or chat id the process prints `Please check your telegram settings: ...` and exits.

Only messages from the given `chat_id` are accepted; everything else is ignored. All accepted messages are forwarded to the AI Agent.

### Console messages after boot

On a successful boot the console prints the following. (Without `SMTM_LLM_API_KEY` it never reaches this stage and exits.)

```
##### smtm telegram LLM controller is started #####
'start'를 입력하면 default 세션 매매가 시작됩니다
default 세션은 가상거래입니다 - 실제 주문은 전송되지 않습니다
실거래는 채팅으로 계좌를 등록한 뒤 세션을 만들어 시작하세요
```

From then on you operate everything from the Telegram chat.

### Paper trading by default

The `default` session that boots with the process is a **paper-trading (virtual) session** -- real-time quotes, simulated balance, no order ever reaches the exchange. Its defaults are exchange UPB, currency BTC, budget 500000, tick interval 60s, strategy BNH.

To trade for real, do the following **through chat**:

1. `register_account` -- register an account by the *names* of the env vars holding the keys (never the key values).
2. `create_profile` -- create a profile with `virtual: false` and an `account`.
3. `create_session` + `start_session` -- create a session from that profile and start it.

### Settings are chat settings, not flags

Budget, currency, exchange, tick interval (`term`), strategy, and the `virtual` flag are all **profile/session settings** set through chat -- they are not command-line flags. Ask the agent to create or update a profile instead.

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

### Using it from a program / Jupyter (JptController)

To drive the system directly from Python code or a Jupyter notebook without Telegram, use `JptController`.

```python
from smtm import JptController

controller = JptController(interval=60, budget=500000, currency="BTC")
controller.initialize(interval=60, budget=500000, exchange="UPB")
controller.chat("Show my portfolio")
controller.start()   # start automated trading
controller.stop()    # stop automated trading
JptController.set_log_level(20)  # log level (10/20/30/40)
```

⚠️ Unlike the Telegram `default` session, `JptController.initialize()` boots in **real-trading mode (virtual=False)** and requires exchange API keys. Because it is not paper trading, real orders may be sent to the exchange -- use it with care.
