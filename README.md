# smtm
[![Travis](https://travis-ci.org/msaltnet/smtm.svg?branch=master&style=flat-square&colorB=green)](https://travis-ci.org/msaltnet/smtm)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

> It's a game to get money.

It has a very simple routine and repeat periodically.
Performance critical approach is NOT suitable. e.g. trading in seconds. If you want, find another solution.

1. Get data from Data Provider
2. Make a decision using Strategy
3. Execute a trading via Trader  
 --- repeat ---
4. Create analyzing result by Analyzer

| Layered Architecture | Role |
|:---:|:---:|
| Controller | User Interface |
| Operator | Operating Manager |
| Analyzer, Trader, Strategy, Data Provider | Main Modules |
| Requests(lib), Pandas(lib), Mpl plot(lib) | External Lib |


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

### How to run simulator
After install, run module smtm

```
python -m smtm
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
python -m unittest tests\integration_tester\bithumb_trader_integration_test.py
```

#### Tip
clear jupyter notebook output before make commit

```
jupyter nbconvert --clear-output --inplace {file.ipynb}
```
