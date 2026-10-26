"""Offline public-rule PAPER regression tests; all metadata is explicit fixtures."""
import copy
from unittest.mock import patch
import pytest
from smtm.trader.paper_rules import PublicPaperRulesReader, PaperRulesError, parse_rules, validate_profile_paper_rules
from smtm.trader.exchange_paper_trader import ExchangePaperTrader
from smtm.strategy.strategy_paper_bnh import StrategyPaperBuyAndHold
from smtm.session_manager import SessionManager


def metadata(exchange):
    if exchange == 'OKX':
        return {'code': '0', 'data': [{'instId': 'BTC-USDT', 'instType': 'SPOT',
                'baseCcy': 'BTC', 'quoteCcy': 'USDT', 'state': 'live',
                'lotSz': '0.00000001', 'minSz': '0.00001', 'tickSz': '0.1', 'upcChg': []}]}
    return {'symbols': [{'symbol': 'BTCUSDT', 'baseAsset': 'BTC', 'quoteAsset': 'USDT',
             'status': 'TRADING', 'isSpotTradingAllowed': True, 'orderTypes': ['LIMIT', 'MARKET'],
             'filters': [{'filterType': 'LOT_SIZE', 'minQty': '0.00001', 'maxQty': '100', 'stepSize': '0.00001'},
                         {'filterType': 'PRICE_FILTER', 'minPrice': '0.1', 'maxPrice': '10000000', 'tickSize': '0.1'},
                         {'filterType': 'MIN_NOTIONAL', 'minNotional': '5'}]}]}


def reader(exchange='BNC', now=None, transport=None):
    now = now if now is not None else [100.0]
    return PublicPaperRulesReader(exchange, 'BTC', transport or (lambda *_: metadata(exchange)), lambda: now[0])


def order(**kwargs):
    return dict({'id': 'one', 'type': 'buy', 'price': 100000, 'amount': .0002}, **kwargs)


@pytest.mark.parametrize('exchange', ['BNC', 'OKX'])
@pytest.mark.parametrize('budget', [100, 1000])
def test_small_usdt_generates_and_fills_orders(exchange, budget):
    trader = ExchangePaperTrader(exchange, budget, reader=reader(exchange))
    strategy = StrategyPaperBuyAndHold(trader)
    strategy.initialize(budget, cash_accounting='fractional')
    for _ in range(7):
        trader.update_quote('BTC', 100000)
        strategy.update_trading_info([{'type': 'primary_candle', 'closing_price': 100000}])
        requests = strategy.get_request()
        if requests:
            trader.send_request(requests, strategy.update_result)
    fills = [r for r in trader.order_history if r['state'] == 'done']
    assert len(fills) >= 4  # Zero orders must never masquerade as a passing lifecycle.
    assert trader.balance >= 0
    assert strategy.balance == pytest.approx(trader.balance)
    assert trader.assets['BTC'][1] > 0


@pytest.mark.parametrize('exchange', ['BNC', 'OKX'])
def test_rules_boundaries(exchange):
    r = parse_rules(exchange, 'BTC', metadata(exchange))
    r.validate(100000, .00005)
    for price, amount in [(100000.01, .00005), (100000, .000000001), (float('nan'), .1), (True, .1)]:
        with pytest.raises(PaperRulesError):
            r.validate(price, amount)
    if exchange == 'BNC':
        with pytest.raises(PaperRulesError):
            r.validate(100000, .00004)


@pytest.mark.parametrize('exchange', ['UPB', 'BTH', 'unknown'])
def test_missing_public_rules_block_without_transport(exchange):
    def forbidden(*_):
        raise AssertionError('must not call private API')
    t = ExchangePaperTrader(exchange, reader=reader(exchange, transport=forbidden))
    result = []
    t.send_request([order()], result.append)
    assert result[-1]['state'] == 'failed'
    assert 'public minimum-order metadata unavailable' in result[-1]['msg']
    assert not t.pending_orders and not t.assets


def test_expired_rules_and_failed_refresh_never_fall_back():
    now = [100.0]
    r = reader(now=now)
    t = ExchangePaperTrader('BNC', reader=r)
    t.update_quote('BTC', 110000)
    results = []
    t.send_request([order()], results.append)
    assert results[-1]['state'] == 'requested'
    now[0] = 160
    r.transport = lambda *_: (_ for _ in ()).throw(RuntimeError('offline'))
    t.prepare_rules()
    t.update_quote('BTC', 100000)
    assert results[-1]['state'] == 'failed'
    assert t.balance == 50000 and not t.assets and not t.pending_orders
    assert r.rules is None


@pytest.mark.parametrize('mutation', ['symbol', 'status', 'notional', 'duplicate', 'step', 'nan'])
def test_invalid_binance_metadata(mutation):
    data = metadata('BNC')
    symbol = data['symbols'][0]
    if mutation == 'symbol': symbol['symbol'] = 'ETHUSDT'
    elif mutation == 'status': symbol['status'] = 'HALT'
    elif mutation == 'notional': symbol['filters'].pop()
    elif mutation == 'duplicate': symbol['filters'].append(copy.deepcopy(symbol['filters'][0]))
    elif mutation == 'step': symbol['filters'][0]['stepSize'] = '0'
    elif mutation == 'nan': symbol['filters'][0]['stepSize'] = 'NaN'
    r = reader(transport=lambda *_: data)
    with pytest.raises(PaperRulesError): r.refresh()
    assert r.rules is None


@pytest.mark.parametrize('change', [{'virtual': False}, {'cash_accounting': 'legacy'}, {'strategy': 'SMA'}, {'paper_exchange_rules': 'true'}])
def test_profile_rejects_live_or_incompatible_mode(change):
    p = dict(virtual=True, cash_accounting='fractional', strategy='BNH', paper_exchange_rules=True)
    p.update(change)
    with pytest.raises(ValueError): validate_profile_paper_rules(p)
    with patch('smtm.trader.trader_factory.TraderFactory.create') as factory:
        assert SessionManager().create_session(p)['success'] is False
        factory.assert_not_called()


def test_default_is_off():
    assert validate_profile_paper_rules({}) is False


@pytest.mark.parametrize('ord_type', ['market', 'stop_loss', 'take_profit'])
def test_unsupported_order_types_fail_closed(ord_type):
    t = ExchangePaperTrader('BNC', reader=reader())
    t.update_quote('BTC', 100000)
    result = []
    t.send_request([order(ord_type=ord_type, type='sell', trigger=100000)], result.append)
    assert result[-1]['state'] == 'failed'
    assert 'LIMIT only' in result[-1]['msg']


def test_okx_sub_micro_lot_keeps_asset_quantity():
    data = metadata('OKX')
    data['data'][0]['minSz'] = '0.00000001'
    t = ExchangePaperTrader('OKX', reader=reader('OKX', transport=lambda *_: data))
    t.update_quote('BTC', 100000)
    out = []
    t.send_request([order(amount=.00000001)], out.append)
    assert out[-1]['state'] == 'done'
    assert t.assets['BTC'][1] == .00000001
    t.send_request([order(id='sell', type='sell', amount=.00000001)], out.append)
    assert out[-1]['state'] == 'done' and not t.assets
    assert t.balance == pytest.approx(50000)


def test_session_wires_explicit_paper_bnh():
    p = dict(name='rules', virtual=True, exchange='BNC', currency='BTC', budget=100,
             strategy='BNH', cash_accounting='fractional', paper_exchange_rules=True)
    with patch.object(PublicPaperRulesReader, '_get', side_effect=lambda *_: metadata('BNC')):
        manager = SessionManager()
        assert manager.create_session(p)['success']
    s = manager.get_session('rules')
    assert isinstance(s.trader, ExchangePaperTrader)
    assert isinstance(s.operator.strategy, StrategyPaperBuyAndHold)
    s.operator.worker.stop()


def test_slow_fetch_clock_reversal_and_refresh_recovery():
    now = [100.0]
    def slow(*_):
        now[0] += 61
        return metadata('BNC')
    r = reader(now=now, transport=slow)
    with pytest.raises(PaperRulesError): r.refresh()
    assert r.rules is None
    r.transport = lambda *_: metadata('BNC')
    r.refresh()
    now[0] -= 1
    with pytest.raises(PaperRulesError): r.require_fresh()
    now[0] += 1
    assert r.require_fresh().exchange == 'BNC'


def test_notional_filters_combine_and_maximum_is_enforced():
    data = metadata('BNC')
    data['symbols'][0]['filters'].append({'filterType': 'NOTIONAL', 'minNotional': '10', 'maxNotional': '100'})
    r = parse_rules('BNC', 'BTC', data)
    r.validate(100000, .0001)
    for amount in [.00009, .00101]:
        with pytest.raises(PaperRulesError): r.validate(100000, amount)


@pytest.mark.parametrize('edit', [{'state': 'suspend'}, {'baseCcy': 'ETH'}, {'minSz': 'NaN'}, {'upcChg': [{'minSz': '.1'}]}])
def test_okx_bad_or_changing_rules(edit):
    data = metadata('OKX')
    data['data'][0].update(edit)
    r = reader('OKX', transport=lambda *_: data)
    with pytest.raises(PaperRulesError): r.refresh()


def test_wrong_currency_and_insufficient_balance_never_fill():
    t = ExchangePaperTrader('BNC', budget=10, reader=reader())
    t.update_quote('BTC', 100000)
    results = []
    t.send_request([order(currency='ETH'), order(id='cost')], results.append)
    assert all(r['state'] == 'failed' for r in results)
    assert t.balance == 10 and not t.assets


def test_pending_notional_rechecked_at_fill_and_cancel_after_expiry():
    now = [100.0]
    t = ExchangePaperTrader('BNC', reader=reader(now=now))
    out = []
    t.update_quote('BTC', 110000)
    t.send_request([order(amount=.00005)], out.append)
    t.update_quote('BTC', 90000)
    assert out[-1]['state'] == 'failed' and not t.assets
    t.send_request([order(id='cancel', price=80000, amount=.0001)], out.append)
    now[0] = 200
    t.cancel_request('cancel')
    assert out[-1]['msg'] == 'canceled' and not t.pending_orders


def test_operator_pipeline_refreshes_rules_and_observes_fill():
    from unittest.mock import Mock
    from smtm.trading_operator import TradingOperator
    from smtm.llm.safety_guard import SafetyGuard, SafetyConfig
    from smtm.analyzer import Analyzer
    t = ExchangePaperTrader('BNC', budget=100, reader=reader())
    s = StrategyPaperBuyAndHold(t)
    data = Mock()
    data.get_info.return_value = [{'type': 'primary_candle', 'market': 'BTC',
        'date_time': '2026-10-25T00:00:00', 'opening_price': 100000, 'closing_price': 100000,
        'high_price': 100000, 'low_price': 100000, 'acc_volume': 1, 'acc_price': 100000}]
    a = Analyzer(Mock())
    operator = TradingOperator(currency='BTC')
    operator.initialize(data, s, t, a, SafetyGuard(SafetyConfig(initial_budget=100)),
                        budget=100, cash_accounting='fractional')
    a.make_start_point()
    operator.state = 'running'
    operator._start_timer = lambda: None
    operator._execute_trading(None)
    assert t.assets['BTC'][1] > 0
    assert any(r['state'] == 'done' for r in t.order_history)


def test_system_operator_preserves_flag_across_profile_and_strategy_changes():
    from unittest.mock import Mock
    from smtm.llm.system_operator import SystemOperator
    op = SystemOperator.__new__(SystemOperator)
    op.config = dict(exchange='BNC', currency='BTC', budget=100, virtual=True,
                     strategy='BNH', cash_accounting='fractional')
    op.budget = 100
    op.session_manager = Mock()
    op.session_manager.replace_session.return_value = {'success': True}
    assert op.apply_profile({'paper_exchange_rules': True})['success']
    assert op.session_manager.replace_session.call_args.args[1]['paper_exchange_rules'] is True
    assert op.config['paper_exchange_rules'] is True
    assert op.select_strategy('BNH')['success']
    assert op.session_manager.replace_session.call_args.args[1]['paper_exchange_rules'] is True
    op.config['paper_exchange_rules'] = None
    assert op._config_to_profile()['paper_exchange_rules'] is None
    from smtm.llm.tools.profile_tools import PROFILE_PROPERTIES
    assert PROFILE_PROPERTIES['paper_exchange_rules']['type'] == 'boolean'


def test_tiny_exchange_lots_do_not_create_assets_or_erase_remainder():
    data = metadata('OKX')
    data['data'][0].update(minSz='0.000000000001', lotSz='0.000000000001')
    t = ExchangePaperTrader('OKX', budget=100, reader=reader('OKX', transport=lambda *_: data))
    t.update_quote('BTC', 100000)
    out = []
    t.send_request([order(type='sell', amount=1e-12)], out.append)
    assert out[-1]['state'] == 'failed' and t.balance == 100 and not t.assets
    t.send_request([order(id='buy', amount=2e-12)], out.append)
    assert out[-1]['state'] == 'done'
    t.send_request([order(id='sell', type='sell', amount=1e-12)], out.append)
    assert out[-1]['state'] == 'done' and t.assets['BTC'][1] == 1e-12


@pytest.mark.parametrize('budget', [100, 1000])
def test_preserved_okx_public_candles_nonzero_replay(budget):
    import json
    from pathlib import Path
    root = Path(__file__).parents[1] / 'fixtures' / 'paper_rules'
    data = json.loads((root / 'okx-rules.json').read_text())
    candles = sorted((c for c in json.loads((root / 'okx-candles.json').read_text())['data']
                      if c[8] == '1'), key=lambda c: int(c[0]))
    assert len(candles) == 199
    t = ExchangePaperTrader('OKX', budget, reader=reader('OKX', transport=lambda *_: data))
    s = StrategyPaperBuyAndHold(t)
    s.initialize(budget, cash_accounting='fractional')
    for candle in candles:
        price = float(candle[4])
        t.update_quote('BTC', price)
        s.update_trading_info([{'type': 'primary_candle', 'closing_price': price}])
        requests = s.get_request()
        if requests:
            t.send_request(requests, s.update_result)
    assert len([r for r in t.order_history if r['state'] == 'done']) == 5
    assert t.assets['BTC'][1] > 0 and t.balance >= 0
    assert s.balance == pytest.approx(t.balance)


def test_public_http_failure_is_diagnostic_but_still_fail_closed():
    from unittest.mock import Mock
    r = PublicPaperRulesReader('BNC', 'BTC', clock=lambda: 100.0)
    with patch('smtm.trader.paper_rules.requests.get', return_value=Mock(status_code=451)), \
         patch('smtm.trader.paper_rules.LogManager.get_logger') as logger:
        with pytest.raises(PaperRulesError, match='metadata unavailable'):
            r.refresh()
        assert r.rules is None
        args = logger.return_value.warning.call_args.args
        assert args[1:4] == ('BNC', 'BTC', 'PaperRulesError')
        assert args[4] == 451
    with pytest.raises(PaperRulesError):
        r.require_fresh()


def test_refresh_diagnostics_never_log_raw_exception_payload():
    def fail(*_):
        raise ValueError('https://example.invalid?token=secret raw-payload')
    r = reader(transport=fail)
    with patch('smtm.trader.paper_rules.LogManager.get_logger') as logger:
        with pytest.raises(PaperRulesError):
            r.refresh()
        args = logger.return_value.warning.call_args.args
        assert args[3:] == ('ValueError', None)
        assert 'secret' not in str(args) and 'raw-payload' not in str(args)
        assert r.rules is None


@pytest.mark.parametrize('exchange', ['BNC', 'OKX'])
@pytest.mark.parametrize('failure', ['timeout', 451, 429, 302, 'invalid'])
def test_quote_failure_preserves_pending_balance_and_assets(exchange, failure):
    import requests
    from unittest.mock import Mock
    from smtm.data.paper_data_provider import create_paper_data_provider
    from smtm.trading_operator import TradingOperator
    trader = ExchangePaperTrader(exchange, budget=100, reader=reader(exchange))
    trader.update_quote('BTC', 110000)
    trader.send_request([order()], lambda result: None)
    pending = copy.deepcopy(trader.pending_orders)
    assert pending
    operator = TradingOperator(currency='BTC')
    operator.state = 'running'
    operator.data_provider = create_paper_data_provider(exchange, 'BTC', 60)
    operator.trader = trader
    operator.strategy = Mock()
    operator.analyzer = Mock()
    operator.safety_guard = Mock()
    operator._start_timer = Mock()
    response = Mock(status_code=failure if type(failure) is int else 200)
    response.json.return_value = {'bad': 'response'}
    with patch('smtm.data.paper_data_provider.requests.get', return_value=response,
               side_effect=requests.Timeout('secret') if failure == 'timeout' else None):
        operator._execute_trading(None)
    assert trader.balance == 100 and not trader.assets
    assert trader.pending_orders == pending
    operator.strategy.get_request.assert_not_called()
    operator._start_timer.assert_called_once()
