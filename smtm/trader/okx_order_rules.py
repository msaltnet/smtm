"""Opt-in public OKX spot rules. No trader integration or order mutation."""
from collections import OrderedDict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
import math
import re


class InstrumentRulesError(ValueError):
    """Metadata or an order value cannot safely be represented by these rules."""


def _positive_decimal(value, name):
    if isinstance(value, bool):
        raise InstrumentRulesError(f"invalid {name}")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise InstrumentRulesError(f"invalid {name}") from None
    if not result.is_finite() or result <= 0:
        raise InstrumentRulesError(f"invalid {name}")
    return result


def _on_grid(value, step):
    # Integer ratios avoid float error and ambient Decimal context rounding.
    vn, vd = value.as_integer_ratio()
    sn, sd = step.as_integer_ratio()
    return (vn * sd) % (vd * sn) == 0


def _instrument_id(value):
    if (not isinstance(value, str) or len(value.split('-')) != 2
            or any(not part or not part.isascii() or not part.isalnum()
                   for part in value.split('-'))):
        raise InstrumentRulesError("invalid spot instrument ID")
    return value


@dataclass(frozen=True)
class OkxSpotRules:
    """Validated immutable metadata; eligibility is not permission to trade.

    Prices are quote/base; lot_size and min_size are base quantities, never
    quote-currency market-buy budgets. Valid suspended/non-USDT spot metadata
    is representable and deliberately distinct from eligibility.
    """
    instrument_id: str
    base_currency: str
    quote_currency: str
    instrument_type: str
    state: str
    tick_size: Decimal
    lot_size: Decimal
    min_size: Decimal

    def __post_init__(self):
        _instrument_id(self.instrument_id)
        if (self.instrument_type != 'SPOT'
                or self.instrument_id.split('-') != [self.base_currency, self.quote_currency]
                or not isinstance(self.state, str) or not self.state
                or self.state.strip() != self.state):
            raise InstrumentRulesError("invalid spot instrument identity or state")
        for name in ('tick_size', 'lot_size', 'min_size'):
            value = getattr(self, name)
            if not isinstance(value, Decimal):
                raise InstrumentRulesError(f"{name} must be Decimal")
            _positive_decimal(value, name)

    @property
    def is_live_usdt_spot(self):
        return self.instrument_type == 'SPOT' and self.quote_currency == 'USDT' and self.state == 'live'

    def validate_price(self, price):
        if not _on_grid(_positive_decimal(price, 'price'), self.tick_size):
            raise InstrumentRulesError("price is not a multiple of tickSz")

    def validate_base_quantity(self, quantity):
        quantity = _positive_decimal(quantity, 'base quantity')
        if quantity < self.min_size:
            raise InstrumentRulesError("base quantity is below minSz")
        if not _on_grid(quantity, self.lot_size):
            raise InstrumentRulesError("base quantity is not a multiple of lotSz")

    def validate_limit_order(self, price, base_quantity):
        """Check representability only, without rounding or eligibility changes."""
        self.validate_price(price)
        self.validate_base_quantity(base_quantity)

    @classmethod
    def from_response(cls, instrument_id, response):
        _instrument_id(instrument_id)
        if (not isinstance(response, dict) or isinstance(response.get('code'), bool)
                or str(response.get('code')) != '0'
                or not isinstance(response.get('data'), list)
                or len(response['data']) != 1):
            raise InstrumentRulesError("invalid OKX instrument response")
        item = response['data'][0]
        if not isinstance(item, dict) or item.get('instId') != instrument_id:
            raise InstrumentRulesError("unexpected OKX instrument")
        if item.get('sCode') not in (None, '', '0', 0) or isinstance(item.get('sCode'), bool):
            raise InstrumentRulesError("OKX instrument error")
        increments = {}
        for field in ('tickSz', 'lotSz', 'minSz'):
            # OKX public metadata specifies strings, not JSON booleans/numbers.
            if (not isinstance(item.get(field), str)
                    or re.fullmatch(r'[+]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?',
                                    item[field]) is None):
                raise InstrumentRulesError(f"invalid {field}")
            increments[field] = _positive_decimal(item[field], field)
        return cls(instrument_id, item.get('baseCcy'), item.get('quoteCcy'),
                   item.get('instType'), item.get('state'),
                   increments['tickSz'], increments['lotSz'], increments['minSz'])


class OkxSpotRulesReader:
    """Bounded LRU/TTL reader using only an injected public transport and clock.

    transport(path, params=...) returns a decoded JSON envelope. clock() must
    be monotonic seconds. Neither is invoked at construction. Single-owner
    reader: callers sharing an instance across threads must serialize access.
    """
    PATH = '/api/v5/public/instruments'

    def __init__(self, transport, clock, ttl=60, capacity=128):
        if not callable(transport) or not callable(clock):
            raise ValueError("transport and clock must be callable")
        if isinstance(ttl, bool) or not isinstance(ttl, (float, int)) or not math.isfinite(ttl) or ttl <= 0:
            raise ValueError("ttl must be positive finite seconds")
        if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity <= 0:
            raise ValueError("capacity must be a positive integer")
        self._transport, self._clock = transport, clock
        self._ttl, self._capacity = ttl, capacity
        self._cache = OrderedDict()

    def get(self, instrument_id, refresh=False):
        _instrument_id(instrument_id)
        now = self._clock()
        for key, (expires, _) in list(self._cache.items()):
            if now >= expires:
                del self._cache[key]
        cached = self._cache.pop(instrument_id, None)
        if cached is not None and not refresh:
            self._cache[instrument_id] = cached
            return cached[1]
        # Invalidate before transport/parsing so explicit or expired failures
        # cannot resurrect stale eligibility on a subsequent read.
        response = self._transport(self.PATH, params={'instType': 'SPOT', 'instId': instrument_id})
        rules = OkxSpotRules.from_response(instrument_id, response)
        # TTL starts at request start, conservatively accounting for latency.
        if self._clock() < now + self._ttl:
            self._cache[instrument_id] = (now + self._ttl, rules)
            while len(self._cache) > self._capacity:
                self._cache.popitem(last=False)
        return rules
