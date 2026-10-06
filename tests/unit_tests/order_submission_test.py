"""Creation transport/ownership contracts; synthetic ACKs and no exchange access."""
import json
import threading
import unittest
from unittest.mock import Mock, patch

import requests
from smtm.trader.upbit_trader import UpbitTrader
from smtm.trader.binance_trader import BinanceTrader
from smtm.trader.okx_trader import OkxTrader
from smtm.trader.bithumb_trader import BithumbTrader


SESSION_REQUEST = requests.sessions.Session.request


class OrderSubmissionTest(unittest.TestCase):
    ADAPTERS = (UpbitTrader, BinanceTrader, OkxTrader, BithumbTrader)

    def setUp(self):
        for target, kwargs in (
            ('os.environ', {'clear': True}),
        ):
            p = patch.dict(target, {}, **kwargs)
            p.start()
            self.addCleanup(p.stop)
        for target in ('smtm.trader.base_exchange_trader.Worker.start',
                       'smtm.http_session.time.sleep'):
            p = patch(target)
            p.start()
            self.addCleanup(p.stop)
        p = patch('requests.sessions.Session.request',
                  side_effect=AssertionError('Network forbidden'))
        p.start()
        self.addCleanup(p.stop)

    def trader(self, cls):
        trader = cls(budget=100000, opt_mode=False)
        trader.ACCESS_KEY, trader.SECRET_KEY = 'synthetic-access', 'synthetic-secret'
        trader.SERVER_URL = 'https://exchange.invalid'
        if cls is OkxTrader:
            trader.PASSPHRASE = 'synthetic-passphrase'
        trader.asset = (100, 10)
        trader.logger = Mock()
        trader._start_timer = Mock()
        return trader

    @staticmethod
    def task(request_id='local-id', **changes):
        request = {'id': request_id, 'type': 'buy', 'price': 100, 'amount': 1}
        request.update(changes)
        return {'request': request, 'callback': Mock()}

    @staticmethod
    def ack(cls, identifier='exchange-id'):
        if cls is UpbitTrader:
            return {'uuid': identifier}
        if cls is BinanceTrader:
            return {'orderId': 123 if identifier == 'exchange-id' else identifier}
        if cls is OkxTrader:
            return {'code': '0', 'data': [{'ordId': identifier, 'sCode': '0'}]}
        return {'status': '0000', 'order_id': identifier}

    @staticmethod
    def response(payload=None, status=200):
        response = Mock(status_code=status)
        response.json.return_value = payload
        if status >= 400:
            response.raise_for_status.side_effect = requests.HTTPError('synthetic HTTP error')
        return response

    def assert_unknown(self, trader, task):
        record = trader._submissions['local-id']
        self.assertEqual(record['state'], 'unknown')
        self.assertTrue(record['dispatched'])
        self.assertIs(record['request'], task['request'])
        self.assertIs(record['callback'], task['callback'])
        self.assertIsNone(record['exchange_id'])
        self.assertEqual(trader.order_map, {})
        task['callback'].assert_not_called()
        self.assertEqual(trader.get_submission_status()['local-id']['state'], 'unknown')

    def test_creation_connection_failure_has_one_attempt_and_retains_ownership(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', side_effect=requests.ConnectionError('lost ACK')) as post:
                    trader._execute_order(task)
                self.assertEqual(post.call_count, 1)
                self.assertIs(post.call_args.kwargs['allow_redirects'], False)
                self.assert_unknown(trader, task)

    def test_creation_5xx_has_one_attempt_and_retains_ownership(self):
        for cls in self.ADAPTERS:
            for status in (500, 502, 503, 504):
                with self.subTest(adapter=cls.__name__, status=status):
                    trader, task = self.trader(cls), self.task()
                    with patch('requests.post', return_value=self.response(status=status)) as post:
                        trader._execute_order(task)
                    self.assertEqual(post.call_count, 1)
                    self.assert_unknown(trader, task)

    def test_redirects_are_not_followed_or_treated_as_ack(self):
        for cls in self.ADAPTERS:
            for status in (301, 302, 307, 308):
                with self.subTest(adapter=cls.__name__, status=status):
                    trader, task = self.trader(cls), self.task()
                    with patch('requests.post', return_value=self.response(self.ack(cls), status)) as post:
                        trader._execute_order(task)
                    self.assertEqual(post.call_count, 1)
                    self.assertIs(post.call_args.kwargs['allow_redirects'], False)
                    self.assert_unknown(trader, task)

    def test_missing_and_malformed_ack_id_stays_unknown(self):
        for cls in self.ADAPTERS:
            invalid = [None, {}, [], 'not an object']
            invalid.extend(self.ack(cls, value) for value in (None, '', ' ', True, [], {}, -1, 0, 1.2))
            for payload in invalid:
                with self.subTest(adapter=cls.__name__, payload=payload):
                    trader, task = self.trader(cls), self.task()
                    with patch('requests.post', return_value=self.response(payload)) as post:
                        trader._execute_order(task)
                    self.assertEqual(post.call_count, 1)
                    self.assert_unknown(trader, task)

    def test_json_timeout_and_unclassified_http_rejection_stay_unknown(self):
        for cls in self.ADAPTERS:
            malformed = self.response()
            malformed.json.side_effect = ValueError('invalid JSON')
            for failure in (malformed, requests.Timeout('lost ACK'), self.response(status=400)):
                with self.subTest(adapter=cls.__name__, failure=type(failure).__name__):
                    trader, task = self.trader(cls), self.task()
                    with patch('requests.post') as post:
                        if isinstance(failure, Exception):
                            post.side_effect = failure
                        else:
                            post.return_value = failure
                        trader._execute_order(task)
                    self.assertEqual(post.call_count, 1)
                    self.assert_unknown(trader, task)

    def test_local_rejection_has_no_dispatch_or_unknown(self):
        for cls in self.ADAPTERS:
            for changes in ({'price': 0}, {'amount': 10000000}, {'ord_type': 'unsupported'}):
                with self.subTest(adapter=cls.__name__, changes=changes):
                    trader, task = self.trader(cls), self.task(**changes)
                    with patch('requests.post') as post:
                        trader._execute_order(task)
                    post.assert_not_called()
                    status = trader.get_submission_status()['local-id']
                    self.assertEqual(status['state'], 'not_dispatched')
                    self.assertFalse(status['dispatched'])
                    self.assertEqual(trader.order_map, {})

    def test_preparation_exception_does_not_invent_unknown(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch.object(trader, '_validate_credentials', side_effect=RuntimeError('prepare')), \
                     patch('requests.post') as post:
                    with self.assertRaisesRegex(RuntimeError, 'prepare'):
                        trader._execute_order(task)
                post.assert_not_called()
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'not_dispatched')

    def test_missing_credentials_is_not_dispatched(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                trader.ACCESS_KEY = ''
                with patch('requests.post') as post:
                    trader._execute_order(task)
                post.assert_not_called()
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'not_dispatched')

    def test_duplicate_unknown_id_never_overwrites_or_dispatches(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', side_effect=requests.ConnectionError()) as post:
                    trader._execute_order(task)
                    record = trader._submissions['local-id']
                    duplicate = self.task()
                    trader._execute_order(duplicate)
                self.assertEqual(post.call_count, 1)
                self.assertIs(trader._submissions['local-id'], record)
                self.assert_unknown(trader, task)
                duplicate['callback'].assert_not_called()

    def test_known_ack_retains_original_callback_and_blocks_duplicate(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', return_value=self.response(self.ack(cls))) as post:
                    trader._execute_order(task)
                    order = trader.order_map['local-id']
                    duplicate = self.task()
                    trader._execute_order(duplicate)
                self.assertEqual(post.call_count, 1)
                self.assertIs(trader.order_map['local-id'], order)
                self.assertIs(order['callback'], task['callback'])
                status = trader.get_submission_status()['local-id']
                self.assertEqual(status['state'], 'known')
                self.assertEqual(status['exchange_id'], 123 if cls is BinanceTrader else 'exchange-id')
                self.assertEqual(task['callback'].call_args.args[0]['state'], 'requested')
                duplicate['callback'].assert_not_called()

    def test_creation_modes_all_use_single_attempt(self):
        for cls in self.ADAPTERS:
            for kind in ('buy', 'sell'):
                for ord_type in ('limit', 'market'):
                    with self.subTest(adapter=cls.__name__, kind=kind, ord_type=ord_type):
                        trader, task = self.trader(cls), self.task(type=kind, ord_type=ord_type)
                        with patch('requests.post', side_effect=requests.ConnectionError()) as post:
                            trader._execute_order(task)
                        self.assertEqual(post.call_count, 1)
                        self.assert_unknown(trader, task)

    def test_get_and_bithumb_query_post_retries_are_preserved(self):
        trader = self.trader(BithumbTrader)
        for method in ('get', 'post'):
            for failure in (requests.ConnectionError(), self.response(status=503)):
                with self.subTest(method=method, failure=type(failure).__name__):
                    response = self.response({'status': '0000'})
                    with patch('requests.' + method, side_effect=[failure, failure, response]) as request:
                        actual = trader._request_get('https://exchange.invalid/query') if method == 'get' \
                            else trader._query_order('known-exchange-id')
                    self.assertEqual(request.call_count, 3)
                    self.assertEqual(actual, {'status': '0000'})
                    self.assertNotIn('allow_redirects', request.call_args.kwargs)

    def test_unknown_is_not_queried_or_cancelled_using_local_id(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', side_effect=requests.ConnectionError()):
                    trader._execute_order(task)
                with patch.object(trader, '_cancel_order') as cancel, \
                     patch('requests.get') as get, patch('requests.post') as post:
                    trader.cancel_request('local-id')
                    trader.cancel_all_requests()
                    trader._update_order_result(None)
                cancel.assert_not_called()
                get.assert_not_called()
                post.assert_not_called()
                self.assert_unknown(trader, task)

    def test_concurrent_duplicate_during_physical_dispatch_preserves_owner(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                entered, release = threading.Event(), threading.Event()
                errors = []
                def post(*args, **kwargs):
                    entered.set()
                    self.assertTrue(release.wait(2))
                    raise requests.ConnectionError('lost ACK')
                def run():
                    try:
                        trader._execute_order(task)
                    except BaseException as error:
                        errors.append(error)
                with patch('requests.post', side_effect=post) as transport:
                    thread = threading.Thread(target=run, daemon=True)
                    thread.start()
                    try:
                        self.assertTrue(entered.wait(2))
                        self.assert_unknown(trader, task)
                        duplicate = self.task()
                        trader._execute_order(duplicate)
                    finally:
                        release.set()
                        thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(transport.call_count, 1)
                self.assert_unknown(trader, task)

    def test_optimization_lookup_is_preparing_until_creation_boundary(self):
        for cls in (UpbitTrader, BithumbTrader):
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                trader.is_opt_mode = True
                def optimize(price, is_buy):
                    status = trader.get_submission_status()['local-id']
                    self.assertEqual(status['state'], 'preparing')
                    self.assertFalse(status['dispatched'])
                    return price
                def post(*args, **kwargs):
                    self.assert_unknown(trader, task)
                    return self.response(self.ack(cls))
                with patch.object(trader, '_optimize_price', side_effect=optimize), \
                     patch('requests.post', side_effect=post):
                    trader._execute_order(task)
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'known')

    def test_status_snapshot_cannot_mutate_ownership(self):
        trader, task = self.trader(BinanceTrader), self.task()
        with patch('requests.post', side_effect=requests.ConnectionError()):
            trader._execute_order(task)
        snapshot = trader.get_submission_status()
        snapshot['local-id']['state'] = 'settled'
        snapshot.clear()
        self.assert_unknown(trader, task)

    @staticmethod
    def terminal(cls):
        if cls is UpbitTrader:
            return {'uuid': 'exchange-id', 'state': 'done', 'price': '100',
                    'executed_volume': '1', 'created_at': '2026-10-06T12:00:00+09:00'}
        if cls is BinanceTrader:
            return {'orderId': 123, 'symbol': 'BTCUSDT', 'status': 'FILLED',
                    'price': '100', 'executedQty': '1'}
        if cls is OkxTrader:
            return {'ordId': 'exchange-id', 'instId': 'BTC-USDT', 'state': 'filled',
                    'avgPx': '100', 'accFillSz': '1'}
        return {'status': '0000', 'data': {'order_status': 'Completed',
                'order_currency': 'BTC', 'payment_currency': 'KRW', 'type': 'bid',
                'order_price': '100', 'order_qty': '1',
                'transaction_date': '1572497603668315',
                'contract': [{'units': '1', 'price': '100',
                              'transaction_date': '1572497603668315'}]}}

    def test_valid_terminal_settles_once_and_same_id_replay_is_suppressed(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', return_value=self.response(self.ack(cls))) as post:
                    trader._execute_order(task)
                    order = trader.order_map['local-id']
                    self.assertTrue(trader._complete_order('local-id', order, self.terminal(cls)))
                    balance, asset = trader.balance, trader.asset
                    self.assertFalse(trader._complete_order('local-id', order, self.terminal(cls)))
                    replay = self.task(price=200)
                    trader._execute_order(replay)
                self.assertEqual(post.call_count, 1)
                self.assertEqual(task['callback'].call_count, 2)  # requested + terminal
                self.assertEqual(trader.balance, balance)
                self.assertEqual(trader.asset, asset)
                self.assertEqual(trader.order_map, {})
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'settled')
                self.assertIsNone(trader._submissions['local-id']['callback'])
                replay['callback'].assert_not_called()

    def test_initial_ack_callback_exception_keeps_known_order_and_schedules_timer(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                task['callback'].side_effect = RuntimeError('client callback failed')
                with patch('requests.post', return_value=self.response(self.ack(cls))) as post:
                    with self.assertRaisesRegex(RuntimeError, 'client callback failed'):
                        trader._execute_order(task)
                self.assertEqual(post.call_count, 1)
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'known')
                self.assertIn('local-id', trader.order_map)
                trader._start_timer.assert_called_once()

    def test_settlement_failure_is_retained_without_retry_or_recreation(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', return_value=self.response(self.ack(cls))) as post:
                    trader._execute_order(task)
                    order = trader.order_map['local-id']
                    task['callback'].side_effect = RuntimeError('settlement callback failed')
                    with self.assertRaisesRegex(RuntimeError, 'settlement callback failed'):
                        trader._complete_order('local-id', order, self.terminal(cls))
                    balance = trader.balance
                    trader._complete_order('local-id', order, self.terminal(cls))
                    trader._execute_order(self.task())
                self.assertEqual(post.call_count, 1)
                self.assertEqual(trader.balance, balance)
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'settlement_failed')
                self.assertIs(trader._submissions['local-id']['callback'], task['callback'])
                self.assertEqual(task['callback'].call_count, 2)

    def test_terminal_callback_in_progress_stays_owned_without_order_map(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', return_value=self.response(self.ack(cls))):
                    trader._execute_order(task)
                order = trader.order_map['local-id']
                entered, release = threading.Event(), threading.Event()
                errors = []
                def callback(result):
                    entered.set()
                    self.assertTrue(release.wait(2))
                task['callback'].side_effect = callback
                def run():
                    try:
                        trader._complete_order('local-id', order, self.terminal(cls))
                    except BaseException as error:
                        errors.append(error)
                thread = threading.Thread(target=run, daemon=True)
                thread.start()
                try:
                    self.assertTrue(entered.wait(2))
                    self.assertEqual(trader.order_map, {})
                    self.assertEqual(trader.get_submission_status()['local-id']['state'], 'settling')
                    self.assertIs(trader._submissions['local-id']['callback'], task['callback'])
                    with patch('requests.post') as post:
                        trader._execute_order(self.task())
                    post.assert_not_called()
                finally:
                    release.set()
                    thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'settled')

    def test_reentrant_callback_cannot_recreate_same_id_or_corrupt_other_context(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                duplicate, other = self.task(), self.task('other-id')
                def callback(result):
                    trader._execute_order(duplicate)
                    trader._execute_order(other)
                task['callback'].side_effect = callback
                with patch('requests.post', side_effect=[self.response(self.ack(cls)),
                                                        requests.ConnectionError()]) as post:
                    trader._execute_order(task)
                self.assertEqual(post.call_count, 2)
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'known')
                self.assertEqual(trader.get_submission_status()['other-id']['state'], 'unknown')
                self.assertIs(trader._submissions['other-id']['callback'], other['callback'])
                duplicate['callback'].assert_not_called()

    def test_concurrent_different_ids_keep_separate_transport_ownership(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader = self.trader(cls)
                tasks = (self.task('first'), self.task('second'))
                barrier = threading.Barrier(2, timeout=2)
                errors = []
                def post(*args, **kwargs):
                    barrier.wait()
                    raise requests.ConnectionError()
                def run(task):
                    try:
                        trader._execute_order(task)
                    except BaseException as error:
                        errors.append(error)
                with patch('requests.post', side_effect=post) as transport:
                    threads = [threading.Thread(target=run, args=(task,), daemon=True) for task in tasks]
                    for thread in threads:
                        thread.start()
                    for thread in threads:
                        thread.join(3)
                        self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertEqual(transport.call_count, 2)
                for task in tasks:
                    record = trader._submissions[task['request']['id']]
                    self.assertIs(record['request'], task['request'])
                    self.assertIs(record['callback'], task['callback'])
                    self.assertEqual(record['state'], 'unknown')

    def test_unexpected_exception_after_dispatch_preserves_unknown(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                with patch('requests.post', side_effect=RuntimeError('unexpected transport failure')) as post:
                    with self.assertRaisesRegex(RuntimeError, 'unexpected transport failure'):
                        trader._execute_order(task)
                self.assertEqual(post.call_count, 1)
                self.assert_unknown(trader, task)

    def test_callback_owner_is_not_copied_for_unknown_submission(self):
        class Owner:
            def __init__(self):
                self.lock = threading.Lock()
            def __deepcopy__(self, memo):
                raise AssertionError('Do not copy callback owners')
            def callback(self, result):
                raise AssertionError('No ambiguous result callback')
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                owner = Owner()
                task['callback'] = owner.callback
                with patch('requests.post', side_effect=requests.ConnectionError()):
                    trader._execute_order(task)
                self.assertIs(trader._submissions['local-id']['callback'], task['callback'])

    def test_second_creation_inside_same_execution_cannot_dispatch(self):
        trader, task = self.trader(BinanceTrader), self.task()
        def sender(*args):
            trader._request_post('https://exchange.invalid/create', creation=True)
            trader._request_post('https://exchange.invalid/create', creation=True)
        with patch.object(trader, '_send_order', side_effect=sender), \
             patch('requests.post', side_effect=requests.ConnectionError()) as post:
            with self.assertRaisesRegex(RuntimeError, 'already attempted'):
                trader._execute_order(task)
        self.assertEqual(post.call_count, 1)
        self.assert_unknown(trader, task)

    def test_okx_ambiguous_multiple_ack_items_remain_unknown(self):
        trader, task = self.trader(OkxTrader), self.task()
        response = self.ack(OkxTrader)
        response['data'].append({'ordId': 'another-order', 'sCode': '0'})
        with patch('requests.post', return_value=self.response(response)) as post:
            trader._execute_order(task)
        self.assertEqual(post.call_count, 1)
        self.assert_unknown(trader, task)

    def test_actual_adapter_query_get_paths_keep_retry_behavior(self):
        for cls in (UpbitTrader, BinanceTrader, OkxTrader):
            with self.subTest(adapter=cls.__name__):
                trader = self.trader(cls)
                response = self.response({'code': '0', 'data': [{'ordId': 'exchange-id'}]})
                with patch('requests.get', side_effect=[requests.ConnectionError(),
                                                       self.response(status=503), response]) as get:
                    if cls is UpbitTrader:
                        trader._query_order_list(['exchange-id'])
                    else:
                        trader._query_order('exchange-id')
                self.assertEqual(get.call_count, 3)
                self.assertNotIn('allow_redirects', get.call_args.kwargs)

    def test_cancellation_transport_retries_are_unchanged(self):
        for cls in self.ADAPTERS:
            method = 'delete' if cls in (UpbitTrader, BinanceTrader) else 'post'
            for failure in (requests.ConnectionError(), self.response(status=503)):
                with self.subTest(adapter=cls.__name__, failure=type(failure).__name__):
                    trader = self.trader(cls)
                    with patch('requests.' + method, side_effect=[failure, failure,
                                                                 self.response(self.ack(cls))]) as call:
                        trader._cancel_order('known-exchange-id')
                    self.assertEqual(call.call_count, 3)
                    self.assertNotIn('allow_redirects', call.call_args.kwargs)

    def test_reentrant_terminal_claim_waits_until_requested_callback_exits(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                seen = []
                def callback(result):
                    if result['state'] == 'requested':
                        order = trader.order_map['local-id']
                        self.assertFalse(trader._complete_order('local-id', order, self.terminal(cls)))
                        self.assertIs(trader.order_map['local-id'], order)
                    seen.append(result['state'])
                task['callback'].side_effect = callback
                with patch('requests.post', return_value=self.response(self.ack(cls))):
                    trader._execute_order(task)
                self.assertEqual(seen, ['requested'])
                order = trader.order_map['local-id']
                self.assertTrue(trader._complete_order('local-id', order, self.terminal(cls)))
                self.assertEqual(seen, ['requested', 'done'])
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'settled')

    def test_okx_creation_requires_explicit_per_item_success(self):
        for value in (None, '', False, True, [], {}, '51008'):
            with self.subTest(value=value):
                trader, task = self.trader(OkxTrader), self.task()
                payload = self.ack(OkxTrader)
                payload['data'][0]['sCode'] = value
                with patch('requests.post', return_value=self.response(payload)):
                    trader._execute_order(task)
                self.assert_unknown(trader, task)
        for value in (0, '0'):
            with self.subTest(accepted=value):
                trader, task = self.trader(OkxTrader), self.task()
                payload = self.ack(OkxTrader)
                payload['data'][0]['sCode'] = value
                with patch('requests.post', return_value=self.response(payload)):
                    trader._execute_order(task)
                self.assertEqual(trader.get_submission_status()['local-id']['state'], 'known')

    def test_concurrent_terminal_claim_cannot_overtake_initial_requested_callback(self):
        for cls in self.ADAPTERS:
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                entered, release = threading.Event(), threading.Event()
                seen, errors = [], []
                def callback(result):
                    if result['state'] == 'requested':
                        entered.set()
                        self.assertTrue(release.wait(2))
                    seen.append(result['state'])
                task['callback'].side_effect = callback
                def run():
                    try:
                        trader._execute_order(task)
                    except BaseException as error:
                        errors.append(error)
                with patch('requests.post', return_value=self.response(self.ack(cls))):
                    thread = threading.Thread(target=run, daemon=True)
                    thread.start()
                    try:
                        self.assertTrue(entered.wait(2))
                        order = trader.order_map['local-id']
                        self.assertFalse(trader._complete_order('local-id', order, self.terminal(cls)))
                        self.assertEqual(seen, [])
                        self.assertIs(trader.order_map['local-id'], order)
                    finally:
                        release.set()
                        thread.join(3)
                self.assertFalse(thread.is_alive())
                self.assertEqual(errors, [])
                self.assertTrue(trader._complete_order('local-id', order, self.terminal(cls)))
                self.assertEqual(seen, ['requested', 'done'])

    def test_contradictory_error_and_id_ack_is_unknown(self):
        for cls, error in ((UpbitTrader, {'error': {'name': 'rejected'}}),
                           (BinanceTrader, {'code': -2010, 'msg': 'rejected'})):
            with self.subTest(adapter=cls.__name__):
                trader, task = self.trader(cls), self.task()
                payload = self.ack(cls)
                payload.update(error)
                with patch('requests.post', return_value=self.response(payload)):
                    trader._execute_order(task)
                self.assert_unknown(trader, task)

    def test_binance_out_of_range_int64_id_is_unknown(self):
        trader, task = self.trader(BinanceTrader), self.task()
        with patch('requests.post', return_value=self.response(self.ack(BinanceTrader, 2 ** 63))):
            trader._execute_order(task)
        self.assert_unknown(trader, task)

    def test_real_requests_redirect_handling_never_replays_creation_transport(self):
        for cls in self.ADAPTERS:
            for status in (307, 308):
                with self.subTest(adapter=cls.__name__, status=status):
                    trader, task = self.trader(cls), self.task()
                    responses = []
                    for code in (status, 200):
                        response = requests.Response()
                        response.status_code = code
                        response.url = 'https://exchange.invalid/order'
                        response.headers['Location'] = 'https://exchange.invalid/replayed-order'
                        response._content = json.dumps(self.ack(cls)).encode()
                        response._content_consumed = True
                        responses.append(response)
                    # Exercise real requests.post -> Session.request/redirect
                    # handling, intercepting before HTTPAdapter can use a socket.
                    def transport(prepared, **kwargs):
                        response = responses.pop(0)
                        response.request = prepared
                        return response
                    with patch('requests.sessions.Session.request', SESSION_REQUEST), \
                         patch('requests.adapters.HTTPAdapter.send', side_effect=transport) as send:
                        trader._execute_order(task)
                    self.assertEqual(send.call_count, 1)
                    self.assert_unknown(trader, task)
