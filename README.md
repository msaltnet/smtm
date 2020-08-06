# smtm
[![Travis](https://travis-ci.org/msaltnet/smtm.svg?branch=master&style=flat-square&colorB=green)](https://travis-ci.org/msaltnet/smtm)
[![license](https://img.shields.io/github/license/msaltnet/smtm.svg?style=flat-square)](https://github.com/msaltnet/smtm/blob/master/LICENSE)
![language](https://img.shields.io/github/languages/top/msaltnet/smtm.svg?style=flat-square&colorB=green)

It's a game to get money.

## How to Use
### Virtual Environment
We recommend use `virtualenv` to use virtual environment.

Install `virtualenv`:
```
C:\> pip install virtualenv
```

Create a new virtual environment by choosing a Python interpreter and making a .\venv directory to hold it:
```
C:\> virtualenv --system-site-packages -p python3 ./venv

```

Install packages within a virtual environment without affecting the host system setup. Start by upgrading pip:
```
(venv) C:\> pip install --upgrade pip

(venv) C:\> pip list  # show packages installed within the virtual environment
```

And to exit virtualenv later:
```
(venv) C:\> deactivate
```

### Install Required Packages
Install all packages using requirements.txt

```
pip install -r requirements.txt
```

### Jupyter Notebook
We recommend jupyter notebook to run and config dynamically.

[Jupyter Notebook](https://jupyter.org/)

How to run jupyter notebook in remote server by ssh
```
ipykernel kernel --debug > klog.file 2>&1 
nohup jupyter notebook > /dev/null &
```

How to convert `.ipynb` to `.py`:
```
jupyter nbconvert --to script [YOUR_NOTEBOOK].ipynb
```

### How to test
Just run below

```
python -m unittest discover ./tests *test.py -v
```
