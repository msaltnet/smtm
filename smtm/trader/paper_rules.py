"""Public, limit-order metadata for opt-in PAPER only. No account endpoints."""
from dataclasses import dataclass
from fractions import Fraction
import math
import re
import time
import requests
from .okx_order_rules import OkxSpotRules
from ..log_manager import LogManager


class PaperRulesError(ValueError):
    pass


def number(value, zero=False):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, Fraction)):
        raise PaperRulesError("invalid rule/order number")
    try:
        result = Fraction(str(value))
    except (ValueError, ZeroDivisionError):
        raise PaperRulesError("invalid rule/order number") from None
    if result < 0 or (not zero and result == 0):
        raise PaperRulesError("non-positive rule/order number")
    return result


@dataclass(frozen=True)
class PaperRules:
    exchange: str
    currency: str
    step: Fraction
    minimum_quantity: Fraction
    tick: Fraction
    minimum_notional: Fraction = Fraction(0)
    maximum_quantity: Fraction = None
    maximum_notional: Fraction = None
    minimum_price: Fraction = None
    maximum_price: Fraction = None

    def validate(self, price, amount):
        price, amount = number(price), number(amount)
        if amount < self.minimum_quantity or amount % self.step:
            raise PaperRulesError("quantity below minimum or off step")
        if price % self.tick:
            raise PaperRulesError("price off tick")
        if self.maximum_quantity is not None and amount > self.maximum_quantity:
            raise PaperRulesError("quantity above maximum")
        if self.minimum_price is not None and price < self.minimum_price:
            raise PaperRulesError("price below minimum")
        if self.maximum_price is not None and price > self.maximum_price:
            raise PaperRulesError("price above maximum")
        notional = price * amount
        if notional < self.minimum_notional:
            raise PaperRulesError("notional below minimum")
        if self.maximum_notional is not None and notional > self.maximum_notional:
            raise PaperRulesError("notional above maximum")

    def size_buy(self, price, budget):
        # Downward only: never inflate a small budget to meet an exchange minimum.
        price = (number(price) // self.tick) * self.tick
        if price <= 0:
            raise PaperRulesError("price below tick")
        amount = (number(budget) / price // self.step) * self.step
        self.validate(price, amount)
        # The legacy simulator accepts floats. Reject unrepresentable grids rather
        # than silently changing their meaning at this boundary.
        p, a = float(price), float(amount)
        self.validate(p, a)
        return p, a


def parse_rules(exchange, currency, response):
    if exchange == "OKX":
        r = OkxSpotRules.from_response(currency + "-USDT", response)
        if not r.is_live_usdt_spot:
            raise PaperRulesError("instrument is not live USDT spot")
        item = response["data"][0]
        if item.get("upcChg"):
            raise PaperRulesError("scheduled instrument changes require revalidation")
        return PaperRules(exchange, currency, Fraction(r.lot_size),
                          Fraction(r.min_size), Fraction(r.tick_size))
    if exchange != "BNC":
        raise PaperRulesError("public minimum-order metadata unavailable for exchange")
    items = response.get("symbols") if isinstance(response, dict) else None
    if not isinstance(items, list) or len(items) != 1:
        raise PaperRulesError("invalid symbol response")
    item = items[0]
    if (item.get("symbol") != currency + "USDT" or item.get("baseAsset") != currency
            or item.get("quoteAsset") != "USDT" or item.get("status") != "TRADING"
            or item.get("isSpotTradingAllowed") is not True
            or "LIMIT" not in item.get("orderTypes", [])):
        raise PaperRulesError("symbol is not eligible USDT spot LIMIT")
    filters = item.get("filters")
    if not isinstance(filters, list):
        raise PaperRulesError("missing filters")
    by_type = {}
    for f in filters:
        if not isinstance(f, dict) or f.get("filterType") in by_type:
            raise PaperRulesError("invalid or duplicate filter")
        by_type[f.get("filterType")] = f
    lot, price = by_type["LOT_SIZE"], by_type["PRICE_FILTER"]
    # These are static size/price rules, not a reproduction of all exchange
    # controls (e.g. percent-price bands or account-specific order counts).
    mins, maxs = [], []
    for key in ("MIN_NOTIONAL", "NOTIONAL"):
        if key in by_type:
            mins.append(number(by_type[key]["minNotional"]))
            if key == "NOTIONAL":
                maxs.append(number(by_type[key]["maxNotional"]))
    if not mins:
        raise PaperRulesError("missing notional rule")
    def bound(value):
        value = number(value, zero=True)
        return value if value else None
    r = PaperRules(exchange, currency, number(lot["stepSize"]), number(lot["minQty"]),
                   number(price["tickSize"]), max(mins), number(lot["maxQty"]),
                   min(maxs) if maxs else None, bound(price["minPrice"]), bound(price["maxPrice"]))
    if r.maximum_quantity < r.minimum_quantity or (r.maximum_notional is not None
            and r.maximum_notional < r.minimum_notional):
        raise PaperRulesError("inconsistent bounds")
    return r


class PublicPaperRulesReader:
    """60-second monotonic cache, measured from request start; no stale fallback."""
    def __init__(self, exchange, currency, transport=None, clock=time.monotonic):
        if not isinstance(currency, str) or re.fullmatch(r"[A-Z0-9]{1,20}", currency) is None:
            raise PaperRulesError("invalid currency")
        self.exchange, self.currency = exchange, currency
        self.transport = transport or self._get
        self.clock = clock
        self.rules = None
        self.started = self.expires = None
        self.error = "metadata not loaded"

    @staticmethod
    def _get(url, params):
        # Explicit public GET only, no keys/account configuration or redirects.
        response = requests.get(url, params=params, timeout=5, allow_redirects=False)
        if response.status_code != 200:
            error = PaperRulesError(f"public metadata request failed (HTTP {response.status_code})")
            error.http_status = response.status_code
            raise error
        return response.json()

    def require_fresh(self):
        now = self.clock()
        if (self.rules is None or not isinstance(now, (int, float)) or isinstance(now, bool)
                or not math.isfinite(now) or not self.started <= now < self.expires):
            raise PaperRulesError(self.error or "metadata expired")
        return self.rules

    def refresh(self):
        try:
            return self.require_fresh()
        except PaperRulesError:
            self.rules = None
        self.error = "metadata unavailable or expired"
        start = self.clock()
        if not isinstance(start, (int, float)) or isinstance(start, bool) or not math.isfinite(start):
            raise PaperRulesError("invalid metadata clock")
        if self.exchange == "BNC":
            url, params = "https://api.binance.com/api/v3/exchangeInfo", {"symbol": self.currency + "USDT"}
        elif self.exchange == "OKX":
            url, params = "https://www.okx.com/api/v5/public/instruments", {"instType": "SPOT", "instId": self.currency + "-USDT"}
        else:
            self.error = "public minimum-order metadata unavailable for exchange"
            raise PaperRulesError(self.error)
        try:
            rules = parse_rules(self.exchange, self.currency, self.transport(url, params))
            self.started, self.expires, self.rules = start, start + 60, rules
            self.require_fresh()
        except Exception as error:
            self.rules = None
            # Do not log raw exception text: transport errors can embed URLs or payloads.
            status = getattr(error, "http_status", None)
            status = status if type(status) is int and 100 <= status <= 599 else None
            LogManager.get_logger(__name__).warning(
                "public rules refresh failed (%s %s): category=%s http_status=%s",
                self.exchange, self.currency, type(error).__name__, status)
            raise PaperRulesError(self.error) from None
        self.error = "metadata expired"
        return rules


def validate_profile_paper_rules(profile):
    enabled = profile.get("paper_exchange_rules", False)
    if type(enabled) is not bool:
        raise ValueError("paper_exchange_rules must be boolean")
    if enabled and (profile.get("virtual") is not True or
                    profile.get("cash_accounting") != "fractional" or
                    (profile.get("strategy") or "BNH") != "BNH"):
        raise ValueError("paper_exchange_rules requires virtual:true, cash_accounting:fractional and BNH")
    return enabled
