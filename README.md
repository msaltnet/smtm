# smtm
[![Travis](https://travis-ci.com/msaltnet/smtm.svg?branch=master&style=flat-square&colorB=green)](https://app.travis-ci.com/github/msaltnet/smtm)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money. 

An algorithm-based cryptocurrency automatic trading system made in Python. https://smtm.msalt.net

[![icon_wide](https://user-images.githubusercontent.com/9311990/150662620-9c2ef1d8-7384-4856-a8fa-f1e52031d6fa.jpg)](https://smtm.msalt.net/)

It has a very simple routine and repeat periodically.
Performance critical approach is NOT suitable. e.g. trading in seconds. If you want, find another solution.

1. Get data from Data Provider
2. Make a decision using Strategy
3. Execute a trading via Trader  
 --- repeat ---
4. Create analyzing result by Analyzer

![intro](https://user-images.githubusercontent.com/9311990/140635409-93e4b678-5a6b-40b8-8e28-5c8f819aa88c.jpg)


## Architecture

| Layer | Role |
|:---:|:---:|
| Controller | User Interface |
| Operator | Operating Manager |
| Analyzer, Trader, Strategy, Data Provider | Modules |

### Telegram Chat-bot Mode
User can launch the program with Telegram chat-bot mode which provide user interface via Telegram chat-bot.

![chatbot](https://user-images.githubusercontent.com/9311990/140635384-58b6e3ed-d5d7-4c20-a217-6493e25799d0.jpg)

### Simulation Mode
User can execute simulation with Simulator or MassSimulator, which run simulations using past trading records.

![simulator](https://user-images.githubusercontent.com/9311990/140635388-5ced5e05-23ad-44df-a14f-8492f489cfd9.jpg)

## User guide
It's need to install and run manually like general python packages.

### How to install
Install all packages using setup.py

```
python setup.py install
```

for development, all development depedencies included.

```
pip install -e .[dev]
```

### How to run
There are 6 mode for each features.
- 0: simulator with interative mode
- 1: execute single simulation
- 2: controller for real trading
- 3: telegram chatbot controller
- 4: mass simulation with config file
- 5: make config file for mass simulation

#### interactive mode simulator
run with only mode
```
python -m smtm --mode 0
```

#### execute single simulation
run with mode and simulation setting parameters
```
python -m smtm --mode 1 --budget 50000 --from_dash_to 201220.170000-201221 --term 0.1 --strategy 0 --currency BTC
```

#### run controller for trading
run with mode and initial setting parameters
```
python -m smtm --mode 2 --budget 50000 --term 60 --strategy 0 --currency ETH
```

#### run telegram chatbot controller for trading
run with only mode 
```
python -m smtm --mode 3
```

#### execute mass simulation with config file
run with mode and config file info
```
python -m smtm --mode 4 --config /data/sma0_simulation.json
```

#### make config file for mass simulation
run with mode and simulation setting parameters
```
python -m smtm --mode 5 --budget 50000 --title SMA_6H_week --strategy 1 --currency ETH --from_dash_to 210804.000000-210811.000000 --offset 360 --file generated_config.json
```

### How to test
#### Unit test
Test project with unittest.

```
# run unittest directly
python -m unittest discover ./tests *test.py -v
```

#### Integration test
Test with real trading market. Some integration tests are excuted via Jupyter notebook. It's good to run test flexible re-ordered.

```
# run unittest directly
python -m unittest integration_tests

# or
python -m unittest integration_tests.simulation_ITG_test
```

#### Tip
clear jupyter notebook output before make commit

```
jupyter nbconvert --clear-output --inplace {file.ipynb}
#jupyter nbconvert --clear-output --inplace .\notebook\*.ipynb
```
