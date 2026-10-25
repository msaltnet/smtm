"""Offline terminal-fill accounting: order limits are not execution prices."""
import threading
from unittest.mock import Mock

import pytest

from smtm.trader.binance_trader import BinanceTrader


@pytest.fixture
def trader():
    instance = BinanceTrader.__new__(BinanceTrader)
    instance._order_lock = threading.Lock()
    instance.market = "BTCUSDT"
    instance.logger = Mock()
    instance.balance = 1000
    instance.asset = (80, 4)
    instance.commission_ratio = 0.001
    instance._start_timer = Mock()
    instance._stop_timer = Mock()
    instance._query_order = Mock()
    instance._cancel_order = Mock()
    instance.order_map = {"local": {
        "order_id": 123,
        "callback": Mock(),
        "result": {"type": "buy", "state": "requested", "price": 100, "amount": 2},
    }}
    return instance


def terminal(status="FILLED", **changes):
    response = {"orderId": 123, "symbol": "BTCUSDT", "status": status,
                "price": "100", "executedQty": "2", "cummulativeQuoteQty": "190"}
    response.update(changes)
    return response


@pytest.mark.parametrize("side,quote,price,balance,asset", [
    ("buy", "190", 95, 809.81, (85, 6)),
    ("sell", "210", 105, 1209.79, (80, 2)),
])
@pytest.mark.parametrize("status", BinanceTrader.TERMINAL_STATES)
@pytest.mark.parametrize("operation", ["poll", "cancel"])
def test_limit_price_improvement_settles_actual_value_once(trader, side, quote, price,
                                                         balance, asset, status, operation):
    order = trader.order_map["local"]
    order["result"]["type"] = side
    if status != "FILLED":
        order["result"]["amount"] = 4  # Only two units filled before termination.
    response = terminal(status, cummulativeQuoteQty=quote)
    trader._query_order.return_value = response
    trader._cancel_order.return_value = response
    if operation == "poll":
        trader._update_order_result(None)
    else:
        trader.cancel_request("local")
    order["callback"].assert_called_once()
    assert order["callback"].call_args[0][0]["price"] == price
    assert trader.balance == balance
    assert trader.asset == asset
    assert trader.order_map == {}
    # A delayed terminal poll/cancel response must not settle twice.
    assert not trader._complete_order("local", order, response)
    order["callback"].assert_called_once()
    assert trader.balance == balance
    assert trader.asset == asset


@pytest.mark.parametrize("quote", [None, True, False, "bad", "nan", "inf", "-inf",
                                    "-1", "0", "1e-400", [], {}, 10**400])
@pytest.mark.parametrize("status", ["FILLED", "CANCELED", "EXPIRED"])
def test_invalid_quote_retains_positive_limit_fill(trader, quote, status):
    order = trader.order_map["local"]
    assert not trader._complete_order("local", order, terminal(status, cummulativeQuoteQty=quote))
    assert trader.order_map["local"] is order
    assert order["result"]["state"] == "requested"
    order["callback"].assert_not_called()
    assert trader.balance == 1000
    assert trader.asset == (80, 4)


def test_missing_quote_retained_until_valid_poll(trader):
    order = trader.order_map["local"]
    response = terminal("CANCELED")
    del response["cummulativeQuoteQty"]
    trader._cancel_order.return_value = response
    trader._query_order.return_value = response
    trader.cancel_request("local")
    assert trader.order_map["local"] is order
    order["callback"].assert_not_called()
    trader._start_timer.assert_called_once()
    trader._query_order.return_value = terminal("CANCELED")
    trader._update_order_result(None)
    order["callback"].assert_called_once()
    assert trader.balance == 809.81


@pytest.mark.parametrize("status", ["CANCELED", "REJECTED", "EXPIRED", "EXPIRED_IN_MATCH"])
def test_zero_fill_needs_no_average_execution_price(trader, status):
    order = trader.order_map["local"]
    response = terminal(status, executedQty="0")
    del response["cummulativeQuoteQty"]
    assert trader._complete_order("local", order, response)
    assert trader.balance == 1000
    assert trader.asset == (80, 4)
    order["callback"].assert_called_once()
