"""Offline fee-inclusive local buy admission, without authentication or HTTP."""
import threading
from decimal import Decimal, Inexact, Rounded, localcontext
from unittest.mock import Mock, patch

import pytest

from smtm.trader.binance_trader import BinanceTrader
from smtm.trader.okx_trader import OkxTrader
from smtm.trader.okx_order_rules import OkxSpotRulesReader


def make_trader(variant):
    cls = BinanceTrader if variant.startswith('binance') else OkxTrader
    with patch.dict("os.environ", {}, clear=True), patch("smtm.trader.base_exchange_trader.Worker.start"):
        t = cls(budget=100, opt_mode=False)
    t.balance, t.asset, t.commission_ratio = 100.0, (100, 2), 0.001
    t.logger = Mock()
    t._send_order = Mock(return_value={'orderId': 1, 'ordId': '1'})
    t._register_submitted_order = Mock()
    t._limit_preflight = variant.endswith('preflight')
    t._preflight_context = threading.local()
    t.market = 'BTC-USDT'
    transport = Mock(return_value={'code': '0', 'data': [dict(
        instId='BTC-USDT', instType='SPOT', baseCcy='BTC', quoteCcy='USDT',
        state='live', tickSz='.01', lotSz='.001', minSz='.001')]})
    t._rules_reader = OkxSpotRulesReader(transport, lambda: 0)
    t.test_ord_type = 'market' if variant.endswith('market') else 'limit'
    return t


@pytest.fixture(params=['binance-limit', 'binance-market', 'okx-limit', 'okx-market', 'okx-preflight'])
def trader(request):
    return make_trader(request.param)


@pytest.mark.parametrize('price,balance,fee,accepted', [
    (100, 100, .001, False),
    (99.95, 100, .001, False),
    (100, 100.1, .001, True),
    (100, 100.0999, .001, False),
    (100, 100, 0, True),
])
def test_buy_checks_existing_fee_before_dispatch(trader, price, balance, fee, accepted):
    trader.balance, trader.commission_ratio = balance, fee
    task = {'request': dict(id='test', type='buy', price=price, amount=1,
                            ord_type=trader.test_ord_type), 'callback': Mock()}
    trader._execute_order(task)
    assert trader._send_order.call_count == int(accepted)
    assert trader._register_submitted_order.call_count == int(accepted)
    assert task['callback'].call_count == int(not accepted)
    assert trader.balance == balance  # No reservation or sizing change.


def test_sell_admission_does_not_require_cash_for_fee(trader):
    trader.balance = 0
    task = {'request': dict(id='test', type='sell', price=100, amount=1,
                            ord_type=trader.test_ord_type), 'callback': Mock()}
    trader._execute_order(task)
    trader._send_order.assert_called_once()
    task['callback'].assert_not_called()


@pytest.mark.parametrize('balance,accepted', [
    ('100.0999999999999999999999999999', False),
    ('100.1', True), ('100.1000000000000000000000000001', True),
])
def test_preflight_fee_boundary_ignores_decimal_context(balance, accepted):
    trader = make_trader("okx-preflight")
    trader.balance = Decimal(balance)
    task = {'request': dict(id='test', type='buy', price='100', amount='1'), 'callback': Mock()}
    with localcontext() as ctx:
        ctx.prec = 2
        ctx.traps[Inexact] = ctx.traps[Rounded] = True
        trader._execute_order(task)
    assert trader._send_order.call_count == int(accepted)
