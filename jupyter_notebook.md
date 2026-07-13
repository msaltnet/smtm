# Jupyter Notebook

Jupyter Notebook is a convenient way to run and control smtm interactively.

[Jupyter Notebook](https://jupyter.org/)

## Using smtm with JptController

`JptController` (`smtm/controller/jpt_controller.py`) wraps the LLM-based
`SystemOperator` for interactive use in a notebook: initialize once, then
chat with the orchestration agent and start/stop trading from notebook cells.

Requirements:
- `SMTM_LLM_API_KEY` environment variable (Anthropic Claude API key) — required
- Exchange API keys (e.g. `UPBIT_OPEN_API_ACCESS_KEY` / `UPBIT_OPEN_API_SECRET_KEY`)
  — `JptController` initializes with `virtual: False`, so orders are sent to
  the real exchange

```python
from smtm import JptController

controller = JptController(interval=60, budget=500000, currency="BTC")
controller.initialize(interval=60, budget=500000, exchange="UPB")  # UPB or BTH

# Chat with the orchestration agent
# (check market/portfolio/status, switch strategy, manage sessions, ...)
controller.chat("현재 상태 알려줘")
controller.chat("RSI 전략으로 바꿔줘")  # switch strategy while trading is stopped

# Start / stop trading
controller.start()  # start the default session's fixed-interval trading loop
controller.stop()   # shut down all trading sessions

# Console log verbosity (10: DEBUG, 20: INFO, 30: WARNING, 40: ERROR)
JptController.set_log_level(30)
```

Notes:
- `initialize()` must be called before `start()`, `stop()`, or `chat()`.
- The default strategy is `BNH` (Buy and Hold).
- `chat()` prints the agent's response and also returns it, so you can keep
  the result in a variable.

## Example notebooks

The `notebook/` directory contains exploratory notebooks for individual
components — `UpbitDataProvider`, `BithumbDataProvider`, `BinanceDataProvider`,
`UpbitTrader`, `BithumbTrader` — plus raw exchange REST API and logging
exercises.

## General tips

How to run jupyter notebook in remote server by ssh
```
nohup jupyter notebook > /dev/null &
```

How to convert `.ipynb` to `.py`:
```
jupyter nbconvert --to script [YOUR_NOTEBOOK].ipynb
```

How to run with https
```
jupyter notebook --certfile=mycert.pem --keyfile mykey.key --no-browser
```
