# 설치 및 사용 방법

소스 코드를 다운로드하고 관련된 패키지를 설치하세요.

```
pip install -r requirements.txt
```

시스템 수정 및 개발을 원할 때는 -e 옵션으로 개발관련 패키지도 설치하세요.

```
pip install -r requirements-dev.txt
```

## 사용 방법
시뮬레이션, 대량 시뮬레이션, 챗봇 모드를 포함하여 아래 6개의 기능을 제공합니다.

- 0: 인터렉티브 모드 시뮬레이터
- 1: 입력받은 설정값으로 싱글 시뮬레이션 실행
- 2: 인터렉티브 모드 기본 실전 매매 프로그램
- 3: 텔레그램 챗봇 모드로 실전 매매 프로그램
- 4: 컨피그 파일을 사용한 대량 시뮬레이션 실행
- 5: 대량 시뮬레이션을 위한 컨피그 파일 생성

### 인터렉티브 모드 시뮬레이터
아래 명령어로 인터렉티브 모드 시뮬레이터 실행.

```
python -m smtm --mode 0
```

### 싱글 시뮬레이션
시뮬레이션 파라미터와 함께 아래 명령어로 단일 시뮬레이션을 실행하면 결과를 반환합니다.

```
python -m smtm --mode 1 --budget 500000 --from_dash_to 201220.080000-201221 --term 0.001 --strategy SMA --currency BTC
```

### 기본 실전 매매 프로그램
아래 명령어로 초기값과 함께 기본 실전 매매 프로그램을 실행합니다. 기본 실전 매매 프로그램은 인터렉티브 모드로 실행되어 입력에 따라 거래 시작, 중지, 결과 조회가 가능합니다.

```
python -m smtm --mode 2 --budget 100000 --term 60 --strategy BNH --currency ETH
```

실전 거래를 위해서는 `.env` 파일에 거래소 API KEY와 API host url을 넣어 주어야 합니다.

```
UPBIT_OPEN_API_ACCESS_KEY=Your API KEY
UPBIT_OPEN_API_SECRET_KEY=Your API KEY
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com
```
### 텔레그램 챗봇 모드 실전 매매 프로그램
아래 명령어로 텔레그램 챗봇 모드 실전 매매 프로그램을 실행합니다. 텔레그램 챗봇 모드 실전 매매 프로그램은 입력받은 텔레그램 챗봇 API 토큰과 대화방 정보를 사용하여 텔레그램 챗봇 메세지를 통해서 거래 시작, 중지, 결과 조회가 가능합니다.

```
python -m smtm --mode 3
```

챗봇 모드를 위해서는 `.env` 파일에 텔레그램 챗봇 API 토큰과 챗봇 대화방 아이디를 넣어 주어야 합니다.

```
TELEGRAM_BOT_TOKEN=bot123456789:YOUR bot Token
TELEGRAM_CHAT_ID=123456789
```

### 대량 시뮬레이션
대량 시뮬레이션 설정 파일과 함께 실행합니다. 설정 파일을 json 형식이며 텍스트 편집기를 통해서 직접 생성해도 되고, 명령어를 통해 생성도 가능합니다.

```
python -m smtm --mode 4 --config /data/sma0_simulation.json
```

### 대량 시뮬레이션 설정 파일 생성
파라미터와 함께 아래 명령어로 대량 시뮬레이션에 사용될 설정 파일을 생성할 수 있습니다.

```
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy SMA --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
```


# How to setup and run

Install all packages using requirements.txt

```
pip install -r requirements.txt
```

For development, all development depedencies included.

```
pip install -r requirements-dev.txt
```

## How to run
There are 6 mode for each features.
- 0: simulator with interative mode
- 1: execute single simulation
- 2: interactive mode controller for real trading
- 3: telegram chatbot controller
- 4: mass simulation with config file
- 5: make config file for mass simulation

### Interactive mode simulator
Run the interactive mode simulator with the command below.

```
python -m smtm --mode 0
```

### Execute single simulation
Running a single simulation with the command below with the simulation parameters will return the results.

```
python -m smtm --mode 1 --budget 50000 --from_dash_to 201220.170000-201221 --term 0.1 --strategy BNH --currency BTC
```

### Run controller for trading
Use the command below to run the default demo trading program with initial values. The demo runs in interactive mode, allowing you to start, stop, and view results based on your inputs.

```
python -m smtm --mode 2 --budget 50000 --term 60 --strategy BNH --currency ETH
```

for real trading API key and host url is included in `.env` file.

```
UPBIT_OPEN_API_ACCESS_KEY=Your API KEY
UPBIT_OPEN_API_SECRET_KEY=Your API KEY
UPBIT_OPEN_API_SERVER_URL=https://api.upbit.com
```

### Run telegram chatbot controller for trading
Execute the command below to run the Telegram Chatbot mode live trading program. The Telegram Chatbot mode live trading program uses the Telegram Chatbot API token and chat room information to start, stop, and view results via Telegram Chatbot messages.

```
python -m smtm --mode 3
```

chat-bot api token and chat room id is needed in `.env`.

```
TELEGRAM_BOT_TOKEN=bot123456789:YOUR bot Token
TELEGRAM_CHAT_ID=123456789
```

### Execute mass simulation with config file
run with mode and config file info
```
python -m smtm --mode 4 --config /data/sma0_simulation.json
```

### Make config file for mass simulation
Run with a mass simulation configuration file. The configuration file is in JSON format and can be generated directly through a text editor or via a command.

```
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy SMA --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
```
