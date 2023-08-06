# smtm
[![build status](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml/badge.svg)](https://github.com/msaltnet/smtm/actions/workflows/python-test.yml)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

An algorithm-based automated cryptocurrency trading system made in Python. https://smtm.msalt.net

[한국어](https://github.com/msaltnet/smtm/blob/master/README.md) 👈

[![icon_wide_gold](https://user-images.githubusercontent.com/9311990/161744914-05e3d116-0e9b-447f-a015-136e0b9ec22b.png)](https://smtm.msalt.net/)

The basic idea is to repeat a simple process of data collection -> algorithmic analysis -> transaction at set intervals, and it's been proven to basically handle one process per minute.

1. The Data Provider module aggregates data  
2. Make a decision using the Strategy module  
3. Execute a trading via the Trader module  
 --- repeat ---
4. Create analyzing result by the Analyzer module  

![intro](https://user-images.githubusercontent.com/9311990/140635409-93e4b678-5a6b-40b8-8e28-5c8f819aa88c.jpg)

❗ It is not suitable for high-performance trading machines that need to process many trades in a short timeframe of seconds, and should be given due consideration if processing time is a critical performance requirement.

## Features
- Parameterizable Simulations
- Mass-Simulation with Multi-process
- CLI Mode Automated Trading Program
- Remote Control with Jupyter Notebook
- Automated trading programs controlled by Telegram

### Telegram Chat-bot Mode
The Telegram Chatbot mode allows you to control your automated trading program using the Telegram messenger.

For Telegram Chatbot mode, you need to create a chatbot, enter the API token and chat room information, and run it.

![smtm_bot](https://user-images.githubusercontent.com/9311990/150667094-95139bfb-03e0-41d5-bad9-6be05ec6c9df.png)

![telegram_chatbot](https://user-images.githubusercontent.com/9311990/150663864-c5a7ed27-f1c6-4b87-8220-e31b8ccce368.PNG)

### Simulation Mode
The simulation mode also allows you to run simulations based on historical trade data to see the results. You can run simple simulations or mass simulations.

## How to install
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
python -m smtm --mode 1 --budget 50000 --from_dash_to 201220.170000-201221 --term 0.1 --strategy 0 --currency BTC
```

### Run controller for trading
Use the command below to run the default demo trading program with initial values. The demo runs in interactive mode, allowing you to start, stop, and view results based on your inputs.

```
python -m smtm --mode 2 --budget 50000 --term 60 --strategy 0 --currency ETH
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
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy 1 --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
```

## Software Architecture
Layered architecture

| Layer | Module | Role |
|:---:|:---:|:---:|
| Controller Layer | Simulator, Controller, TelegramController| User Interface |
| Operator Layer | Operator, SimulationOperator |Operating Manager |
| Core Layer |Analyzer, Trader, Strategy, Data Provider | Core Feature |

### Component Diagram

![Component Diagram](https://user-images.githubusercontent.com/9311990/221420624-9807ca39-31c7-4bb6-b3de-3a4114f22430.png)

### Class Diagram

![Class Diagram](https://user-images.githubusercontent.com/9311990/221420583-6b335aec-1547-47b3-8b64-6a6313127890.png)

### Sequence Diagram

![Sequence Diagram](https://user-images.githubusercontent.com/9311990/221420599-301e0463-ad36-424b-a356-4ef83fa9e88e.png)


## How to test
### Unit test
Test project with unittest.

```
# run unittest directly
python -m unittest discover ./tests *test.py -v
```

### Integration test
Test with real trading market. Some integration tests are excuted via Jupyter notebook. It's good to run test flexible re-ordered.

You can find notebook files in `notebook` directory.

```
# run unittest directly
python -m unittest integration_tests

# or
python -m unittest integration_tests.simulation_ITG_test
```

### Tip
clear jupyter notebook output before make commit

```bash
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```

If you run simulation or demo mode, you should set timezone to 'Asia/Seoul' because smtm use Upbit trading information for simulation and demo. For Linux, below command is available.

```bash
timedatectl set-timezone 'Asia/Seoul'
```

For keeping smtm program process after terminating ssh connection, using `nohup` is recommended as below. Standard, error ouput is redirected to specific files.
```bash
nohup python -m smtm --mode 3 --demo 1 > nohup.out 2> nohup.err < /dev/null &
```

## Related Book

[![smtm-book](https://user-images.githubusercontent.com/9311990/157685437-dcedd2c0-9f0c-400c-a3d4-017354279b60.png)](http://www.kyobobook.co.kr/product/detailViewKor.laf?mallGb=KOR&ejkGb=KOR&barcode=9788997924967)
