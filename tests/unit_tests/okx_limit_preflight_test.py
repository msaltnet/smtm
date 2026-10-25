"""Offline opt-in checks: synthetic metadata, credentials and HTTP responses."""
import json
import threading
from decimal import Decimal, localcontext, Inexact, Rounded
from unittest import TestCase
from unittest.mock import Mock, patch
import requests
from smtm.trader.okx_order_rules import OkxSpotRulesReader, InstrumentRulesError
from smtm.trader.okx_trader import OkxTrader


def metadata(instrument='BTC-USDT', **changes):
    base, quote = instrument.split('-')
    item = dict(instId=instrument, instType='SPOT', baseCcy=base, quoteCcy=quote,
                state='live', tickSz='.25', lotSz='.003', minSz='.005')
    item.update(changes)
    return {'code': '0', 'data': [item]}


class LimitPreflightTest(TestCase):
    def setUp(self):
        for p in (patch.dict('os.environ', {}, clear=True),
                  patch('smtm.trader.base_exchange_trader.Worker.start'),
                  patch('requests.sessions.Session.request', side_effect=AssertionError('network'))):
            p.start()
            self.addCleanup(p.stop)
        self.now = 0
        self.transport = Mock(side_effect=lambda path, params: metadata(params['instId']))
        self.reader = OkxSpotRulesReader(self.transport, lambda: self.now)
        self.http = Mock(status_code=200)
        self.http.json.return_value = {'code': '0', 'data': [{'ordId': 'test-id', 'sCode': '0'}]}
        self.post_patch = patch('requests.post', return_value=self.http)
        self.post = self.post_patch.start()
        self.addCleanup(self.post_patch.stop)

    def trader(self, **kwargs):
        kwargs.setdefault('rules_reader', self.reader)
        kwargs.setdefault('limit_preflight', True)
        t = OkxTrader(budget=100000, opt_mode=False, **kwargs)
        t.ACCESS_KEY, t.SECRET_KEY, t.PASSPHRASE = 'fake', 'fake', 'fake'
        t.SERVER_URL = 'https://exchange.invalid'
        t.asset = (100, 10)
        t.logger = Mock()
        t._start_timer = Mock()
        return t

    def task(self, **changes):
        req = dict(id='local-id', type='buy', price='100.25', amount='.006')
        req.update(changes)
        return dict(request=req, callback=Mock())

    def rejected(self, t, task):
        before = (t.balance, t.asset, dict(t.order_map))
        t._execute_order(task)
        self.post.assert_not_called()
        task['callback'].assert_called_once()
        self.assertEqual(task['callback'].call_args.args[0]['state'], 'failed')
        self.assertEqual((t.balance, t.asset, t.order_map), before)
        self.assertEqual(t.get_submission_status()['local-id'], dict(
            state='not_dispatched', dispatched=False, exchange_id=None))

    def test_constructor_boolean_and_no_fetch(self):
        self.trader()
        self.transport.assert_not_called()
        for value in (1, 0, 'true', None):
            with self.assertRaises(ValueError):
                self.trader(limit_preflight=value)

    def test_default_off_reader_injection_does_not_enable(self):
        t = self.trader(limit_preflight=False)
        t._execute_order(self.task(price='100.26', amount='.007'))
        self.transport.assert_not_called()
        self.assertEqual(json.loads(self.post.call_args.kwargs['data'])['px'], '100.26')

    def test_all_existing_pairs(self):
        for currency in ('BTC', 'ETH', 'DOGE', 'XRP'):
            t = self.trader(currency=currency)
            t._execute_order(self.task())
            self.assertEqual(json.loads(self.post.call_args.kwargs['data'])['instId'], currency+'-USDT')
        with self.assertRaises(UserWarning):
            self.trader(currency='SOL')

    def test_bad_numbers_and_grids_reject(self):
        for field, values in {'price': ['100.26', True, False, 'NaN', 'sNaN', 'Infinity', '-1', 'bad', None, Decimal('sNaN'), Decimal('NaN')],
                              'amount': ['.003', '.005', '.007', True, False, '0', 'NaN', '-1', None]}.items():
            for value in values:
                with self.subTest(field=field, value=value):
                    self.rejected(self.trader(), self.task(**{field:value}))

    def test_legacy_numeric_zero_hold_precedes_metadata(self):
        task = self.task(price=0)
        self.trader()._execute_order(task)
        self.transport.assert_not_called()
        self.post.assert_not_called()
        task['callback'].assert_not_called()

    def test_malformed_unavailable_and_ineligible_metadata(self):
        for value in (None, {}, {'code':'1','data':[]}, metadata('ETH-USDT'),
                      metadata(state='suspend'), metadata(state='unknown'),
                      metadata(quoteCcy='USDC'), metadata(tickSz='0'),
                      {'code':'0','data':metadata()['data']*2}):
            with self.subTest(value=value):
                self.reader._cache.clear()
                self.transport.side_effect = None
                self.transport.return_value = value
                self.rejected(self.trader(), self.task())
        self.transport.side_effect = requests.Timeout('public timeout')
        self.rejected(self.trader(), self.task())

    def test_exact_precision_and_context(self):
        self.transport.side_effect = lambda *a, **k: metadata(tickSz='1e-12',lotSz='1e-12',minSz='1e-12')
        task = self.task(price=Decimal('1.123456789123'), amount=Decimal('.123456789123'))
        original = task['request'].copy()
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = ctx.traps[Rounded] = True
            self.trader()._execute_order(task)
        payload = json.loads(self.post.call_args.kwargs['data'])
        self.assertEqual((payload['px'], payload['sz']), ('1.123456789123','0.123456789123'))
        self.assertEqual(task['request'], original)

    def test_both_market_paths_bypass_metadata(self):
        for side, unit, size in [('buy','quote_ccy','10'),('sell','base_ccy','0.1')]:
            self.trader()._execute_order(self.task(type=side, ord_type='market',price=100,amount=.1))
            payload=json.loads(self.post.call_args.kwargs['data'])
            self.assertEqual((payload['tgtCcy'],payload['sz']), (unit,size))
        self.transport.assert_not_called()

    def test_expiry_after_signing_before_creation_rejects_once(self):
        t = self.trader()
        original = t._auth_headers
        def sign(*args):
            headers=original(*args)
            self.now=60
            return headers
        t._auth_headers=sign
        self.rejected(t,self.task())

    def test_callback_exception_not_retried(self):
        task=self.task(amount='bad')
        task['callback'].side_effect=RuntimeError('callback')
        with self.assertRaisesRegex(RuntimeError,'callback'):
            self.trader()._execute_order(task)
        task['callback'].assert_called_once()
        self.post.assert_not_called()

    def test_timeout_and_bad_ack_remain_unknown_no_resend(self):
        for failure in (requests.Timeout('lost'), None):
            self.post.reset_mock()
            self.post.side_effect=failure
            self.http.json.return_value={}
            t,task=self.trader(),self.task()
            t._execute_order(task)
            t._execute_order(task)
            self.post.assert_called_once()
            self.assertFalse(self.post.call_args.kwargs['allow_redirects'])
            task['callback'].assert_not_called()
            self.assertEqual(t.get_submission_status()['local-id']['state'],'unknown')
            self.assertIs(t._submissions['local-id']['request'],task['request'])

    def test_public_transport_unsigned_and_constructor_lazy(self):
        with patch.object(OkxTrader,'_request_get',return_value=metadata()) as get:
            t=self.trader(rules_reader=None)
            get.assert_not_called()
            t._execute_order(self.task())
            get.assert_called_once_with('https://exchange.invalid/api/v5/public/instruments',
                                       params={'instType':'SPOT','instId':'BTC-USDT'})

    def test_reentrant_duplicate_retains_owner(self):
        t,task=self.trader(),self.task()
        second=self.task()
        self.transport.side_effect=lambda *a,**k: (t._execute_order(second),metadata())[1]
        t._execute_order(task)
        self.post.assert_called_once()
        second['callback'].assert_not_called()
        self.assertIs(t._submissions['local-id']['request'],task['request'])

    def test_close_admission_during_public_read_prevents_dispatch(self):
        t=self.trader()
        with patch.object(t.worker, '_capture_run', return_value=Mock()), \
                patch.object(t.worker, '_observe_run'):
            handle=t.get_admission_control().open_run()
        task=self.task()
        task['_admission_run']=handle._run
        self.transport.side_effect=lambda *a,**k: (handle.close(),metadata())[1]
        t._execute_order(task)
        self.post.assert_not_called()
        self.assertFalse(t.get_submission_status()['local-id']['dispatched'])

    def test_concurrent_duplicate_suppressed_during_metadata_read(self):
        entered, release = threading.Event(), threading.Event()
        t, first, second = self.trader(), self.task(), self.task()
        def transport(*a, **k):
            entered.set()
            if not release.wait(3): raise RuntimeError("test synchronization")
            return metadata()
        self.transport.side_effect = transport
        errors = []
        def run():
            try: t._execute_order(first)
            except Exception as exc: errors.append(exc)
        thread = threading.Thread(target=run)
        thread.start()
        try:
            self.assertTrue(entered.wait(3))
            t._execute_order(second)
            # Metadata reads must not hold ownership lock.
            self.assertEqual(t.get_submission_status()['local-id']['state'], 'preparing')
        finally:
            release.set()
            thread.join(3)
        self.assertFalse(thread.is_alive())
        self.assertEqual(errors, [])
        self.post.assert_called_once()
        second['callback'].assert_not_called()

    def test_mutation_during_signing_cannot_change_validated_payload(self):
        t, task = self.trader(), self.task()
        original = t._auth_headers
        def sign(*args):
            task['request']['price'] = '999.99'
            task['request']['amount'] = '.001'
            return original(*args)
        t._auth_headers = sign
        t._execute_order(task)
        payload = json.loads(self.post.call_args.kwargs['data'])
        self.assertEqual((payload['px'], payload['sz']), ('100.25','0.006'))

    def test_insufficient_balance_and_sell_asset_are_local_rejections(self):
        t=self.trader()
        t.balance=0
        self.rejected(t,self.task())
        t=self.trader()
        t.asset=(0,0)
        self.rejected(t,self.task(type='sell'))

    def test_independent_minimum_and_lot_boundaries_do_not_round(self):
        # minSz need not be a lot multiple: .005 is not an admissible .003 lot.
        for minimum, amount, accepted in (
            ('.005', '.003', False), ('.005', '.005', False),
            ('.005', '.006', True), ('.006', '.003', False),
            ('.006', '.006', True), ('.006', '.009', True),
        ):
            with self.subTest(minimum=minimum, amount=amount):
                self.reader._cache.clear()
                self.post.reset_mock()
                self.transport.side_effect = lambda *a, **k: metadata(minSz=minimum)
                t, task = self.trader(), self.task(amount=amount)
                original = task['request'].copy()
                if accepted:
                    t._execute_order(task)
                    self.post.assert_called_once()
                    payload = json.loads(self.post.call_args.kwargs['data'])
                    self.assertEqual(payload['sz'], format(Decimal(amount), 'f'))
                else:
                    self.rejected(t, task)
                self.assertEqual(task['request'], original)

    def test_sub_usdt_buy_balance_boundary_is_exact_under_low_precision(self):
        # .6015 notional + .0006015 fee = .6021015 USDT.
        # A float comparison loses the fractional shortfall.
        for balance, accepted in (
            ('0.6021014999999999999999999999', False),
            ('0.6021015', True), ('0.6021015000000000000000000001', True),
        ):
            with self.subTest(balance=balance):
                self.post.reset_mock()
                t, task = self.trader(), self.task()
                t.balance = Decimal(balance)
                with localcontext() as ctx:
                    ctx.prec = 2
                    ctx.traps[Inexact] = ctx.traps[Rounded] = True
                    if accepted:
                        t._execute_order(task)
                        self.post.assert_called_once()
                    else:
                        self.rejected(t, task)
                self.assertEqual(t.balance, Decimal(balance))

    def test_sell_asset_boundary_is_exact_not_float_rounded(self):
        for available, accepted in (
            ('0.0059999999999999999999999999', False),
            ('0.006', True), ('0.0060000000000000000000000001', True),
        ):
            with self.subTest(available=available):
                self.post.reset_mock()
                t, task = self.trader(), self.task(type='sell')
                t.asset = (100, Decimal(available))
                if accepted:
                    t._execute_order(task)
                    self.post.assert_called_once()
                    self.assertEqual(json.loads(self.post.call_args.kwargs['data'])['side'], 'sell')
                else:
                    self.rejected(t, task)
                self.assertEqual(t.asset, (100, Decimal(available)))

    def test_near_grid_values_are_rejected_not_rounded_to_valid_orders(self):
        for changes in (
            {'price': '100.2499999999999999999999999999'},
            {'price': '100.2500000000000000000000000001'},
            {'amount': '0.0059999999999999999999999999'},
            {'amount': '0.0060000000000000000000000001'},
        ):
            with self.subTest(changes=changes):
                task = self.task(**changes)
                original = task['request'].copy()
                self.rejected(self.trader(), task)
                self.assertEqual(task['request'], original)

    def test_tiny_valid_order_keeps_fixed_point_payload_without_rounding(self):
        self.transport.side_effect = lambda *a, **k: metadata(
            tickSz='1e-12', lotSz='3e-12', minSz='3e-12')
        t, task = self.trader(), self.task(price='1e-12', amount='3e-12')
        t.balance = Decimal('3.003e-24')  # Notional plus the existing .001 fee.
        original = task['request'].copy()
        t._execute_order(task)
        self.post.assert_called_once()
        payload = json.loads(self.post.call_args.kwargs['data'])
        self.assertEqual((payload['px'], payload['sz']),
                         ('0.000000000001', '0.000000000003'))
        self.assertEqual(task['request'], original)

    def test_expiry_rejection_callback_exception_is_not_retried(self):
        t,task=self.trader(),self.task()
        self.reader.require_fresh=Mock(side_effect=InstrumentRulesError('expired'))
        task['callback'].side_effect=RuntimeError('callback')
        with self.assertRaisesRegex(RuntimeError,'callback'):t._execute_order(task)
        task['callback'].assert_called_once()
        self.post.assert_not_called()

    def test_cancel_bypasses_metadata(self):
        t=self.trader()
        t.cancel_request=Mock()
        t._execute_order(self.task(type='cancel'))
        t.cancel_request.assert_called_once_with('local-id')
        self.transport.assert_not_called()


class StrictSnapshotTest(TestCase):
    def test_cache_deadline_slow_response_and_no_fallback(self):
        now=[0]
        transport=Mock(return_value=metadata())
        reader=OkxSpotRulesReader(transport,lambda:now[0])
        snap=reader.get_snapshot('BTC-USDT')
        now[0]=59
        self.assertIs(reader.get_snapshot('BTC-USDT').rules,snap.rules)
        now[0]=60
        transport.side_effect=RuntimeError('unavailable')
        with self.assertRaises(RuntimeError):reader.get_snapshot('BTC-USDT')
        self.assertNotIn('BTC-USDT',reader._cache)
        transport.side_effect=lambda *a,**k:(now.__setitem__(0,now[0]+60),metadata())[1]
        with self.assertRaises(InstrumentRulesError):reader.get_snapshot('BTC-USDT')
        self.assertNotIn('BTC-USDT',reader._cache)

    def test_nonfinite_and_backward_clock_fail_closed(self):
        for end in (float('nan'),float('inf'),True,-1):
            clock=Mock(side_effect=[0,end])
            reader=OkxSpotRulesReader(Mock(return_value=metadata()),clock)
            with self.assertRaises(InstrumentRulesError):reader.get_snapshot('BTC-USDT')
        for start in (float('nan'),float('inf'),True):
            transport=Mock()
            reader=OkxSpotRulesReader(transport,lambda:start)
            with self.assertRaises(InstrumentRulesError):reader.get_snapshot('BTC-USDT')
            transport.assert_not_called()

    def test_final_clock_invalid_rejected(self):
        clock=Mock(side_effect=[0,0,float('nan')])
        reader=OkxSpotRulesReader(Mock(return_value=metadata()),clock)
        snapshot=reader.get_snapshot('BTC-USDT')
        with self.assertRaises(InstrumentRulesError):reader.require_fresh(snapshot)

    def test_shared_strict_reads_serialize_transport(self):
        entered, release, second_started = threading.Event(), threading.Event(), threading.Event()
        active, errors, snapshots = [], [], []
        def transport(*args, **kwargs):
            active.append(kwargs['params']['instId'])
            entered.set()
            if not release.wait(3): raise RuntimeError('test synchronization')
            return metadata(kwargs['params']['instId'])
        reader=OkxSpotRulesReader(transport,lambda:0)
        def read(pair):
            try:
                if pair=='ETH-USDT': second_started.set()
                snapshots.append(reader.get_snapshot(pair))
            except Exception as exc: errors.append(exc)
        first=threading.Thread(target=read,args=('BTC-USDT',))
        second=threading.Thread(target=read,args=('ETH-USDT',))
        first.start()
        try:
            self.assertTrue(entered.wait(3))
            second.start()
            self.assertTrue(second_started.wait(3))
            self.assertEqual(active,['BTC-USDT'])
        finally:
            release.set()
            first.join(3)
            second.join(3)
        self.assertFalse(first.is_alive() or second.is_alive())
        self.assertEqual(errors,[])
        self.assertEqual(len(snapshots),2)
