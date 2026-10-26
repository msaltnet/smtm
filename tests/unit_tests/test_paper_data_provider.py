"""No sockets, credentials, or exchange orders are used by these regressions."""
from unittest.mock import Mock, patch

import pytest
import requests

from smtm.data.paper_data_provider import (PaperBinanceDataProvider, PaperOkxDataProvider,
                                          PaperQuoteError, create_paper_data_provider)
from smtm.data.binance_data_provider import BinanceDataProvider
from smtm.data.okx_data_provider import OkxDataProvider
from smtm.session_manager import SessionManager
from smtm.trading_operator import TradingOperator


PROVIDERS = [PaperBinanceDataProvider, PaperOkxDataProvider]
SECRET = 'sensitive-token-and-response-body'


def payload(provider):
    row = [1792972800000, '100', '110', '90', '100', '2', '200', '200']
    return {'code': '0', 'data': [row]} if provider.CODE == 'OKX' else [row]


@pytest.mark.parametrize('provider_class', PROVIDERS)
def test_success_uses_original_endpoint_bounded_read_and_no_redirect(provider_class):
    provider = provider_class()
    with patch('smtm.data.paper_data_provider.requests.get', return_value=Mock(
            status_code=200, json=lambda: payload(provider))) as get:
        info = provider.get_info()
    get.assert_called_once_with(provider.URL, params=provider._query_params,
                                timeout=5, allow_redirects=False)
    assert info[0]['closing_price'] == 100
    assert info[0]['acc_price'] == 200


@pytest.mark.parametrize('provider_class', PROVIDERS)
@pytest.mark.parametrize('failure, category', [
    (requests.Timeout(SECRET), 'timeout'),
    (requests.ConnectionError(SECRET), 'connection'),
    (requests.RequestException(SECRET), 'request_error'),
    (451, 'http_451'), (429, 'http_429'), (302, 'http_302'), (500, 'http_500'),
    ('json', 'invalid_response'), ('shape', 'invalid_response'),
    ('nan', 'invalid_response'), ('business', 'invalid_response')])
def test_failure_is_sanitized_and_not_retried(provider_class, failure, category):
    provider = provider_class()
    provider.logger = Mock()
    response = Mock(status_code=failure if type(failure) is int else 200)
    response.json.return_value = payload(provider)
    if failure == 'json':
        response.json.side_effect = ValueError(SECRET)
    elif failure in ('shape', 'business'):
        response.json.return_value = {'code': 'bad', 'msg': SECRET, 'data': []}
    elif failure == 'nan':
        data = payload(provider)
        (data['data'] if provider.CODE == 'OKX' else data)[0][4] = 'nan'
        response.json.return_value = data
    with patch('smtm.data.paper_data_provider.requests.get', return_value=response,
               side_effect=failure if isinstance(failure, Exception) else None) as get:
        with pytest.raises(PaperQuoteError, match=category) as caught:
            provider.get_info()
    assert get.call_count == 1
    assert SECRET not in str(caught.value)
    assert caught.value.__suppress_context__
    assert SECRET not in str(provider.logger.mock_calls)


@pytest.mark.parametrize('exchange, original, strict', [
    ('BNC', BinanceDataProvider, PaperBinanceDataProvider),
    ('OKX', OkxDataProvider, PaperOkxDataProvider)])
@pytest.mark.parametrize('virtual, enabled', [(True, True), (True, False), (False, False)])
def test_session_wiring_is_opt_in_only(exchange, original, strict, virtual, enabled):
    profile = dict(exchange=exchange, currency='BTC', budget=100, strategy='BNH',
                   virtual=virtual, paper_exchange_rules=enabled, cash_accounting='fractional')
    # _assemble is isolated from LIVE account/trader construction and all secrets.
    with patch.object(TradingOperator, 'initialize') as initialize:
        SessionManager()._assemble(profile, 'wiring', Mock(), None)
    provider = initialize.call_args.args[0]
    assert type(provider) is (strict if enabled else original)


@pytest.mark.parametrize('provider_class', PROVIDERS)
def test_failed_tick_has_no_orders_or_quote_update_and_next_tick_recovers(provider_class):
    provider = provider_class()
    operator = TradingOperator()
    operator.data_provider = provider
    operator.state = 'running'
    operator.trader = Mock()
    operator.strategy = Mock()
    operator.strategy.get_request.return_value = []
    operator.analyzer = Mock()
    operator.safety_guard = Mock()
    operator._sync_trader_quote = Mock()
    operator._send_requests = Mock()
    operator._start_timer = Mock()
    response = Mock(status_code=200, json=lambda: payload(provider))
    with patch('smtm.data.paper_data_provider.requests.get',
               side_effect=[requests.Timeout(SECRET), response]):
        operator._execute_trading(None)
        operator._sync_trader_quote.assert_not_called()
        operator._send_requests.assert_not_called()
        operator.trader.assert_not_called()
        operator.strategy.get_request.assert_not_called()
        operator._start_timer.assert_called_once()
        operator._execute_trading(None)
    operator._sync_trader_quote.assert_called_once()
    operator.strategy.get_request.assert_called_once()
    assert operator._start_timer.call_count == 2


def test_unsupported_exchange_cannot_fallback():
    with pytest.raises(ValueError, match='unsupported'):
        create_paper_data_provider('UPB', 'BTC', 60)
