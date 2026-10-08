"""Synthetic, offline checks for the opt-in public rules reader."""
from dataclasses import FrozenInstanceError, replace
from decimal import Decimal, localcontext, Inexact, Rounded
from unittest import TestCase
from unittest.mock import Mock, patch

from smtm.trader.okx_order_rules import InstrumentRulesError, OkxSpotRules, OkxSpotRulesReader


def response(instrument_id='BTC-USDT', **changes):
    base, quote = instrument_id.split('-')
    item = {'instId': instrument_id, 'instType': 'SPOT', 'baseCcy': base,
            'quoteCcy': quote, 'state': 'live', 'tickSz': '0.25',
            'lotSz': '0.003', 'minSz': '0.005'}
    item.update(changes)
    return {'code': '0', 'data': [item]}


class OkxSpotRulesTest(TestCase):
    def rules(self, **changes):
        return OkxSpotRules.from_response('BTC-USDT', response(**changes))

    def test_identity_and_decimal_fields(self):
        rules = self.rules()
        self.assertEqual((rules.instrument_id, rules.base_currency, rules.quote_currency,
                          rules.instrument_type, rules.state),
                         ('BTC-USDT', 'BTC', 'USDT', 'SPOT', 'live'))
        self.assertEqual((rules.tick_size, rules.lot_size, rules.min_size),
                         (Decimal('.25'), Decimal('.003'), Decimal('.005')))
        self.assertTrue(rules.is_live_usdt_spot)

    def test_suspended_and_other_quote_remain_representable(self):
        for state in ('suspend', 'preopen', 'test', 'future_exchange_state'):
            self.assertFalse(self.rules(state=state).is_live_usdt_spot)
        rules = OkxSpotRules.from_response('BTC-USDC', response('BTC-USDC'))
        self.assertFalse(rules.is_live_usdt_spot)
        rules.validate_limit_order('100.25', '.006')

    def test_frozen_and_detached_from_response(self):
        payload = response()
        rules = OkxSpotRules.from_response('BTC-USDT', payload)
        payload['data'][0]['tickSz'] = '1000'
        self.assertEqual(rules.tick_size, Decimal('.25'))
        with self.assertRaises(FrozenInstanceError):
            rules.state = 'suspend'

    def test_direct_construction_enforces_validated_invariants(self):
        for changes in ({'tick_size': '.25'}, {'lot_size': Decimal('NaN')},
                        {'min_size': Decimal('-1')}, {'instrument_type': 'SWAP'},
                        {'base_currency': 'ETH'}):
            with self.subTest(changes=changes), self.assertRaises(InstrumentRulesError):
                replace(self.rules(), **changes)

    def test_malformed_envelopes(self):
        for payload in (None, [], '', {}, {'code': '1', 'data': response()['data']},
                        {'code': True, 'data': response()['data']},
                        {'code': '0', 'data': []}, {'code': '0', 'data': {}},
                        {'code': '0', 'data': [None]},
                        {'code': '0', 'data': response()['data'] * 2}):
            with self.subTest(payload=payload), self.assertRaises(InstrumentRulesError):
                OkxSpotRules.from_response('BTC-USDT', payload)

    def test_wrong_missing_or_ambiguous_identity_and_state(self):
        for key, values in {'instId': [None, 'ETH-USDT'], 'instType': [None, 'SWAP'],
                            'baseCcy': [None, '', 'ETH'], 'quoteCcy': [None, '', 'USDC'],
                            'state': [None, '', True, ' live '],
                            'sCode': ['1', True]}.items():
            for value in values:
                with self.subTest(key=key, value=value), self.assertRaises(InstrumentRulesError):
                    self.rules(**{key: value})

    def test_numeric_metadata_is_strict_positive_finite(self):
        for field in ('tickSz', 'lotSz', 'minSz'):
            for value in (None, True, False, 1, 0.25, '', '0', '-0', '-1', 'NaN',
                          'sNaN', 'Infinity', '-Infinity', 'garbage', '0.2_5',
                          '０.２５', ' 0.25', '0.25 ', '0.25\n'):
                with self.subTest(field=field, value=value), self.assertRaises(InstrumentRulesError):
                    self.rules(**{field: value})

    def test_ascii_scientific_metadata_is_exact(self):
        self.assertEqual(self.rules(tickSz="2.5e-7").tick_size, Decimal("0.00000025"))

    def test_arbitrary_grid_and_independent_minimum(self):
        rules = self.rules()
        rules.validate_limit_order('100.25', '.006')
        for price, amount in [('100.26', '.006'), ('100.25', '.007'),
                              ('100.25', '.003'), ('100.25', '.005')]:
            with self.subTest(price=price, amount=amount), self.assertRaises(InstrumentRulesError):
                rules.validate_limit_order(price, amount)
        self.rules(minSz='.006').validate_base_quantity('.006')

    def test_precision_beyond_eight_decimals_and_ambient_context(self):
        rules = self.rules(tickSz='0.000000000000000000000000003',
                           lotSz='0.000000000000000000000000007',
                           minSz='0.00000000000000000000000001')
        with localcontext() as ctx:
            ctx.prec = 2
            ctx.traps[Inexact] = ctx.traps[Rounded] = True
            rules.validate_limit_order('0.000000000000000000000000009',
                                       '0.000000000000000000000000014')
            self.rules().validate_price('123456789123456789123456789.25')
            with self.assertRaises(InstrumentRulesError):
                rules.validate_price('0.00000000000000000000000001')

    def test_invalid_order_values(self):
        for value in (None, True, False, '0', '-1', 'NaN', 'sNaN', 'Infinity', '', object()):
            for method in (self.rules().validate_price, self.rules().validate_base_quantity):
                with self.subTest(value=value, method=method), self.assertRaises(InstrumentRulesError):
                    method(value)

    def test_checks_do_not_mutate_or_round_inputs(self):
        values = {'price': Decimal('100.2500'), 'base_quantity': Decimal('.00600')}
        before = {key: value.as_tuple() for key, value in values.items()}
        self.rules().validate_limit_order(**values)
        self.assertEqual(before, {key: value.as_tuple() for key, value in values.items()})

    def test_base_quantity_contract_is_separate_from_quote_budgets(self):
        self.assertIn('quote-currency market-buy budgets', OkxSpotRules.__doc__)
        self.assertFalse(hasattr(self.rules(), 'validate_market_buy'))


class OkxSpotRulesReaderTest(TestCase):
    def setUp(self):
        self.now = 0
        self.transport = Mock(side_effect=lambda path, params: response(params['instId']))
        self.clock = Mock(side_effect=lambda: self.now)
        self.reader = OkxSpotRulesReader(self.transport, self.clock, ttl=10, capacity=2)

    def test_constructor_does_not_call_transport_clock_or_environment(self):
        with patch('os.getenv', side_effect=AssertionError('Environment forbidden')), \
                patch('os.environ', None):
            OkxSpotRulesReader(self.transport, self.clock)
        self.transport.assert_not_called()
        self.clock.assert_not_called()

    def test_exact_public_request(self):
        self.reader.get('BTC-USDT')
        self.transport.assert_called_once_with('/api/v5/public/instruments',
            params={'instType': 'SPOT', 'instId': 'BTC-USDT'})

    def test_cache_hit_and_exact_expiry(self):
        first = self.reader.get('BTC-USDT')
        self.now = 9.99
        self.assertIs(self.reader.get('BTC-USDT'), first)
        self.transport.assert_called_once()
        self.now = 10
        self.assertIsNot(self.reader.get('BTC-USDT'), first)
        self.assertEqual(self.transport.call_count, 2)

    def test_explicit_refresh_updates_state(self):
        self.assertTrue(self.reader.get('BTC-USDT').is_live_usdt_spot)
        self.transport.side_effect = lambda *a, **kw: response(state='suspend')
        rules = self.reader.get('BTC-USDT', refresh=True)
        self.assertFalse(rules.is_live_usdt_spot)
        self.assertIs(self.reader.get('BTC-USDT'), rules)

    def test_failed_refresh_invalidates_even_unexpired_cache(self):
        for expired in (False, True):
            with self.subTest(expired=expired):
                self.transport.side_effect = lambda *a, **kw: response()
                self.reader.get('BTC-USDT')
                if expired:
                    self.now += 10
                self.transport.side_effect = RuntimeError('offline failure')
                with self.assertRaises(RuntimeError):
                    self.reader.get('BTC-USDT', refresh=True)
                with self.assertRaises(RuntimeError):
                    self.reader.get('BTC-USDT')

    def test_unexpired_malformed_refresh_invalidates_cache(self):
        self.reader.get('BTC-USDT')
        self.transport.side_effect = lambda *a, **kw: response(tickSz='0.2_5')
        with self.assertRaises(InstrumentRulesError):
            self.reader.get('BTC-USDT', refresh=True)
        with self.assertRaises(InstrumentRulesError):
            self.reader.get('BTC-USDT')
        self.assertEqual(self.transport.call_count, 3)

    def test_expired_invalid_metadata_never_returns_stale_rules(self):
        self.reader.get('BTC-USDT')
        self.now = 10
        self.transport.side_effect = lambda *a, **kw: response(tickSz='NaN')
        for _ in range(2):
            with self.assertRaises(InstrumentRulesError):
                self.reader.get('BTC-USDT')
        self.assertEqual(self.transport.call_count, 3)

    def test_lru_capacity_and_distinct_instruments(self):
        btc = self.reader.get('BTC-USDT')
        self.reader.get('ETH-USDT')
        self.assertIs(self.reader.get('BTC-USDT'), btc)
        self.reader.get('XRP-USDT')
        self.assertIs(self.reader.get('BTC-USDT'), btc)
        self.reader.get('ETH-USDT')
        self.assertEqual(self.transport.call_count, 4)
        self.assertLessEqual(len(self.reader._cache), 2)

    def test_slow_response_not_cached_past_ttl(self):
        def slow(*args, **kwargs):
            self.now += 11
            return response()
        self.transport.side_effect = slow
        self.reader.get('BTC-USDT')
        self.reader.get('BTC-USDT')
        self.assertEqual(self.transport.call_count, 2)

    def test_cache_objects_remain_immutable(self):
        rules = self.reader.get('BTC-USDT')
        with self.assertRaises(FrozenInstanceError):
            rules.tick_size = Decimal('1')
        self.assertEqual(self.reader.get('BTC-USDT').tick_size, Decimal('.25'))

    def test_invalid_options(self):
        for kwargs in ({'ttl': 0}, {'ttl': -1}, {'ttl': True}, {'ttl': float('nan')},
                       {'ttl': float('inf')}, {'capacity': 0}, {'capacity': 1.5},
                       {'capacity': True}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                OkxSpotRulesReader(self.transport, self.clock, **kwargs)
        for transport, clock in ((None, self.clock), (self.transport, None)):
            with self.assertRaises(ValueError):
                OkxSpotRulesReader(transport, clock)

    def test_invalid_requested_ids_never_reach_transport(self):
        for value in (None, True, '', 'BTC', 'BTC-USDT-SWAP', ' BTC-USDT', 'BTC-', 'BTC/USDT'):
            with self.subTest(value=value), self.assertRaises(InstrumentRulesError):
                self.reader.get(value)
        self.transport.assert_not_called()
