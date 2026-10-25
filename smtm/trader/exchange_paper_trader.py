"""Strict limit-only PAPER simulator. Live traders never import this class."""
from .simulation_trader import SimulationTrader
from .paper_rules import PublicPaperRulesReader, PaperRulesError
from . import order_spec


class ExchangePaperTrader(SimulationTrader):
    # Never manufacture cash/assets or erase valid tiny lots via legacy tolerance.
    RESOURCE_EPSILON = 0.0

    def __init__(self, exchange, budget=50000, currency="BTC", reader=None):
        super().__init__(budget=budget, currency=currency)
        self.rules_reader = reader or PublicPaperRulesReader(exchange, currency)
        self.rules_error = None
        self.prepare_rules()

    def prepare_rules(self):
        try:
            self.rules_reader.refresh()
            self.rules_error = None
        except PaperRulesError as error:
            self.rules_error = str(error)

    def _rule_error(self, request, price=None):
        try:
            rules = self.rules_reader.require_fresh()
            if request.get("currency", self.currency) != self.currency:
                raise PaperRulesError("unexpected currency")
            if order_spec.get_ord_type(request) != order_spec.LIMIT:
                raise PaperRulesError("strict PAPER supports LIMIT only")
            rules.validate(request.get("price"), request.get("amount"))
            if price is not None:
                # Fill quote may be better than the limit, but must still meet
                # minimum notional. It is a candle replay, not an order-book fill.
                rules.validate(price, request.get("amount"))
        except (ValueError, TypeError, KeyError) as error:
            return "PAPER rules blocked: " + str(error)
        return None

    def _validate_request(self, request, ord_type):
        return super()._validate_request(request, ord_type) or self._rule_error(request)

    def _fill(self, request, callback, fill_price):
        error = self._rule_error(request, fill_price)
        if error:
            return self._result(request, "failed", error)
        currency = self.currency
        amount = self._valid_amount(request.get("amount"))
        value = fill_price * amount
        result = self._result(request, "done", "success", fill_price, amount, 0)
        old_price, old_amount = self.assets.get(currency, (0, 0))
        if request["type"] == "buy":
            if not self._resource_available(value, self._available_balance()):
                return self._fail(result, "잔고 부족")
            new_amount = old_amount + amount
            self.assets[currency] = ((old_price * old_amount + value) / new_amount, new_amount)
            self.balance = self._normalize_resource(self.balance - value)
        else:
            if not self._resource_available(amount, self._available_asset(currency)):
                return self._fail(result, "보유 수량 부족")
            remaining = self._normalize_resource(old_amount - amount)
            if remaining <= 0:
                self.assets.pop(currency, None)
            else:
                self.assets[currency] = (old_price, remaining)
            self.balance = self._normalize_resource(self.balance + value)
        result["balance"] = self.balance
        return result

    def _valid_amount(self, value):
        # Exchange lot size replaces the generic simulator's 1e-6 threshold.
        return self._positive_finite(value)
