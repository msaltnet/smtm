# smtm
[![Travis](https://travis-ci.org/msaltnet/smtm.svg?branch=master&style=flat-square&colorB=green)](https://travis-ci.org/msaltnet/smtm)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)
[![Coverage Status](https://coveralls.io/repos/github/msaltnet/smtm/badge.svg?branch=master)](https://coveralls.io/github/msaltnet/smtm?branch=master)

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
Test project with unittest. Run test also using setup.py

```
python setup.py test
# or run unittest directly
python -m unittest discover ./tests *test.py -v
```