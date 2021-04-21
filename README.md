# smtm
[![Travis](https://travis-ci.org/msaltnet/smtm.svg?branch=master&style=flat-square&colorB=green)](https://travis-ci.org/msaltnet/smtm)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![codecov](https://codecov.io/gh/msaltnet/smtm/branch/master/graph/badge.svg?token=USXTX7MG70)](https://codecov.io/gh/msaltnet/smtm)

It's a game to get money.

## How to install
Install all packages using setup.py

```
python setup.py install
```

for development, all development depedencies included.

```
pip install -e .[dev]
```

## How to run simulator
After install, run module smtm

```
python -m smtm
```

### How to test
Test project with unittest.

```
# run unittest directly
python -m unittest discover ./tests *test.py -v
```

### Integration test
Test with real trading market.

```
# run unittest directly
python -m unittest tests\integration_tester\bithumb_trader_integration_test.py
```

### Tip
clear jupyter notebook output before make commit

```
jupyter nbconvert --clear-output --inplace {file.ipynb}
````