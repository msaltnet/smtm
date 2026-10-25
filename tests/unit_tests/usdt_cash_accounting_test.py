"""Offline regression checks for fractional USDT cash settlement."""
import threading
from unittest.mock import Mock

import pytest

from smtm.trader.binance_trader import BinanceTrader
from smtm.trader.okx_trader import OkxTrader


@pytest.fixture(params=[BinanceTrader, OkxTrader], ids=["binance", "okx"])
def trader(request):
    # Avoid credentials, timers and HTTP: exercise the real settlement method only.
    instance = request.param.__new__(request.param)
    instance._order_lock = threading.Lock()
    instance.balance = 100.0
    instance.asset = (102500.0, 0.001)
    instance.commission_ratio = 0.001
    return instance


@pytest.mark.parametrize("side,expected", [("buy", 89.73975), ("sell", 110.23975)])
def test_fractional_cash_includes_fractional_fee(trader, side, expected):
    result = {"state": "done", "type": side, "price": 102500, "amount": 0.0001}
    callback = Mock()
    trader._call_callback(callback, result)
    assert trader.balance == pytest.approx(expected, abs=1e-10, rel=0)
    callback.assert_called_once_with(result)


@pytest.mark.parametrize("side,expected", [("buy", 99.8999), ("sell", 100.0999)])
def test_small_fills_are_not_rounded_away(trader, side, expected):
    for _ in range(10):
        trader._call_callback(lambda result: None,
                              {"state": "done", "type": side, "price": 100, "amount": 0.0001})
    assert trader.balance == pytest.approx(expected, abs=1e-10, rel=0)


def test_round_trip_cash_cost_is_both_fees(trader):
    initial_amount = trader.asset[1]
    for side in ("buy", "sell"):
        trader._call_callback(lambda result: None,
                              {"state": "done", "type": side, "price": 102500, "amount": 0.0001})
    assert trader.balance == pytest.approx(99.9795, abs=1e-10, rel=0)
    assert trader.asset[1] == initial_amount


@pytest.mark.parametrize("state", ["requested", "cancelled"])
def test_non_done_result_leaves_cash_unchanged(trader, state):
    trader._call_callback(lambda result: None,
                          {"state": state, "type": "buy", "price": 102500, "amount": 0.0001})
    assert trader.balance == 100.0
