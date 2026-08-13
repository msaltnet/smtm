import copy
import math
from datetime import datetime
from typing import Any, Callable, Dict, List

from ..log_manager import LogManager
from . import order_spec
from .trader import Trader


class SimulationTrader(Trader):
    """In-memory virtual trading Trader using externally injected market quotes."""

    NAME = "Simulation Trader"
    CODE = "SIM"
    SUPPORTED_ORD_TYPES = frozenset({"limit", "market", "stop_loss", "take_profit"})
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    RESOURCE_EPSILON = 1e-12
    MINIMUM_AMOUNT = 1e-6

    def __init__(self, budget=50000, currency="BTC", commission_ratio=0):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.balance = float(budget)
        self.currency = currency
        self.commission_ratio = 0
        self.assets = {}
        self.quotes = {}
        self.order_history = []
        self.pending_orders = {}
        self.pending_conditionals = []  # [{"request":..., "callback":...}]

    def update_quote(self, currency: str, price: float) -> None:
        valid_price = self._positive_finite(price)
        if not isinstance(currency, str) or not currency.strip() or \
                valid_price is None:
            self.logger.warning("Ignoring invalid simulation quote: %r=%r", currency,
                                price)
            return
        self.quotes[currency] = valid_price
        self._check_pending_orders(currency, valid_price)
        self._check_conditionals(currency, valid_price)

    def send_request(
        self,
        request_list: List[Dict[str, Any]],
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        for request in request_list:
            if request.get("type") == "cancel":
                self.cancel_request(request.get("id"))
                continue
            ord_type = order_spec.get_ord_type(request)
            validation_error = self._validate_request(request, ord_type)
            if validation_error:
                self._reject(request, callback, validation_error)
                continue
            if order_spec.is_conditional(request):
                self._register_conditional(request, callback)
                continue
            if ord_type == order_spec.MARKET:
                self._submit_market(request, callback)
            elif ord_type == order_spec.LIMIT:
                self._submit_limit(request, callback)

    def cancel_request(self, request_id: str) -> None:
        self.pending_conditionals = [
            e for e in self.pending_conditionals
            if e["request"].get("id") != request_id
        ]

    def cancel_all_requests(self) -> None:
        return

    def get_account_info(self) -> Dict[str, Any]:
        return {
            "balance": self.balance,
            "available_balance": self._available_balance(),
            "reserved_balance": self._reserved_balance(),
            "asset": copy.deepcopy(self.assets),
            "available_asset": {
                currency: self._available_asset(currency)
                for currency in self.assets
            },
            "reserved_asset": self._reserved_assets(),
            "quote": dict(self.quotes),
            "open_orders": [
                {
                    "request": copy.deepcopy(entry["request"]),
                    "state": "requested",
                    "reserved_balance": entry["reserved_balance"],
                    "reserved_asset": entry["reserved_asset"],
                }
                for entry in self.pending_orders.values()
            ],
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }

    @staticmethod
    def _positive_finite(value):
        if isinstance(value, bool):
            return None
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        return number if math.isfinite(number) and number > 0 else None

    @staticmethod
    def _numeric(value):
        try:
            number = float(value)
        except (TypeError, ValueError, OverflowError):
            return 0
        return number if math.isfinite(number) else 0

    def _result(self, request, state, message, price=0, amount=0, fee=0):
        return {
            "request": copy.deepcopy(request),
            "type": request.get("type"),
            "price": self._numeric(price),
            "amount": self._numeric(amount),
            "fee": self._numeric(fee),
            "msg": message,
            "balance": self.balance,
            "state": state,
            "date_time": request.get("date_time") or datetime.now().strftime(
                self.ISO_DATEFORMAT
            ),
        }

    def _finish(self, result, callback):
        if result["state"] in {"done", "failed"}:
            self.order_history.append(copy.deepcopy(result))
        callback(result)
        return result

    def _reject(self, request, callback, message):
        return self._finish(self._result(request, "failed", message), callback)

    def _validate_request(self, request, ord_type):
        if ord_type not in self.SUPPORTED_ORD_TYPES:
            return f"지원하지 않는 주문 유형: {ord_type}"

        request_id = request.get("id")
        if not isinstance(request_id, str) or not request_id.strip():
            return "잘못된 주문 ID"
        if request_id in self.pending_orders:
            return "중복 주문 ID"

        order_type = request.get("type")
        if order_type not in {"buy", "sell"}:
            return f"지원하지 않는 매매 유형: {order_type}"

        if self._valid_amount(request.get("amount")) is None:
            return "잘못된 수량"

        if ord_type == order_spec.LIMIT and \
                self._positive_finite(request.get("price")) is None:
            return "잘못된 가격"

        if ord_type in {order_spec.STOP_LOSS, order_spec.TAKE_PROFIT}:
            if self._positive_finite(request.get("trigger")) is None:
                return "잘못된 트리거"
            if order_type != "sell":
                return "매도 조건 주문만 지원"
        return None

    def _reserved_balance(self):
        return sum(entry["reserved_balance"] for entry in self.pending_orders.values())

    def _reserved_assets(self):
        reserved = {}
        for entry in self.pending_orders.values():
            amount = entry["reserved_asset"]
            if amount:
                currency = entry["currency"]
                reserved[currency] = reserved.get(currency, 0) + amount
        return reserved

    def _available_balance(self):
        return self._normalize_resource(self.balance - self._reserved_balance())

    def _available_asset(self, currency):
        _, amount = self.assets.get(currency, (0, 0))
        return self._normalize_resource(
            amount - self._reserved_assets().get(currency, 0)
        )

    @classmethod
    def _normalize_resource(cls, value):
        return 0.0 if abs(value) <= cls.RESOURCE_EPSILON else value

    @classmethod
    def _resource_available(cls, required, available):
        return required <= available + cls.RESOURCE_EPSILON

    def _valid_amount(self, value):
        amount = self._positive_finite(value)
        if amount is None or amount < self.MINIMUM_AMOUNT:
            return None
        return amount

    def _queue(self, request, callback, reserved_balance=0, reserved_asset=0):
        self.pending_orders[request["id"]] = {
            "request": copy.deepcopy(request),
            "callback": callback,
            "currency": request.get("currency", self.currency),
            "reserved_balance": reserved_balance,
            "reserved_asset": reserved_asset,
        }
        callback(self._result(
            request, "requested", "success", request.get("price", 0),
            request.get("amount", 0),
        ))

    def _submit_market(self, request, callback):
        currency = request.get("currency", self.currency)
        fill_price = self._positive_finite(self.quotes.get(currency))
        if fill_price is None:
            return self._reject(request, callback, "시세 없음")
        return self._finish(self._fill(request, callback, fill_price), callback)

    def _limit_fires(self, request, quote):
        limit_price = self._positive_finite(request.get("price"))
        if limit_price is None:
            return False
        if request.get("type") == "buy":
            return quote <= limit_price
        if request.get("type") == "sell":
            return quote >= limit_price
        return False

    def _submit_limit(self, request, callback):
        currency = request.get("currency", self.currency)
        quote = self._positive_finite(self.quotes.get(currency))
        if quote is not None and self._limit_fires(request, quote):
            return self._finish(self._fill(request, callback, quote), callback)

        amount = self._valid_amount(request.get("amount"))
        if request.get("type") == "buy":
            reservation = self._positive_finite(request.get("price")) * amount
            if not self._resource_available(
                    reservation, self._available_balance()):
                return self._reject(request, callback, "잔고 부족")
            return self._queue(request, callback, reserved_balance=reservation)
        if not self._resource_available(amount, self._available_asset(currency)):
            return self._reject(request, callback, "보유 수량 부족")
        return self._queue(request, callback, reserved_asset=amount)

    def _fill(self, request, callback, fill_price):
        currency = request.get("currency", self.currency)
        amount = self._valid_amount(request.get("amount"))
        if amount is None:
            return self._result(request, "failed", "잘못된 수량")

        fee = fill_price * amount * self.commission_ratio
        result = self._result(request, "done", "success", fill_price, amount, fee)

        if request.get("type") == "buy":
            trade_value = fill_price * amount
            if not self._resource_available(
                    trade_value + fee, self._available_balance()):
                return self._fail(result, "잔고 부족")

            old_price, old_amount = self.assets.get(currency, (0, 0))
            new_amount = round(old_amount + amount, 6)
            new_value = old_price * old_amount + trade_value
            avg_price = round(new_value / new_amount, 6) if new_amount else 0
            self.balance = self._normalize_resource(
                self.balance - trade_value - fee
            )
            self.assets[currency] = (avg_price, new_amount)
        elif request.get("type") == "sell":
            old_price, old_amount = self.assets.get(currency, (0, 0))
            if not self._resource_available(
                    amount, self._available_asset(currency)):
                return self._fail(result, "보유 수량 부족")

            trade_value = fill_price * amount
            new_amount = round(old_amount - amount, 6)
            self.balance = self._normalize_resource(
                self.balance + trade_value - fee
            )
            if new_amount <= 0:
                self.assets.pop(currency, None)
            else:
                self.assets[currency] = (old_price, new_amount)
        else:
            return self._fail(result, "지원하지 않는 주문 유형")

        result["balance"] = self.balance
        return result

    def _check_pending_orders(self, currency, quote):
        pending_ids = [
            request_id for request_id, entry in self.pending_orders.items()
            if entry["currency"] == currency
        ]
        for request_id in pending_ids:
            entry = self.pending_orders.get(request_id)
            if entry is not None and self._limit_fires(entry["request"], quote):
                self._fill_pending(request_id, quote)

    def _fill_pending(self, request_id, quote):
        entry = self.pending_orders.pop(request_id, None)
        if entry is not None:
            result = self._fill(entry["request"], entry["callback"], quote)
            return self._finish(result, entry["callback"])
        return None

    def _buy(self, currency: str, price: float, amount: float, result: Dict[str, Any]):
        trade_value = price * amount
        total_cost = trade_value
        if total_cost > self.balance:
            self._fail(result, "잔고 부족")
            return

        old_price, old_amount = self.assets.get(currency, (0, 0))
        new_amount = round(old_amount + amount, 6)
        new_value = old_price * old_amount + trade_value
        avg_price = round(new_value / new_amount, 6) if new_amount else 0

        self.balance -= total_cost
        self.assets[currency] = (avg_price, new_amount)

    def _sell(self, currency: str, price: float, amount: float, result: Dict[str, Any]):
        old_price, old_amount = self.assets.get(currency, (0, 0))
        if old_amount < amount:
            self._fail(result, "보유 수량 부족")
            return

        trade_value = price * amount
        new_amount = round(old_amount - amount, 6)

        self.balance += trade_value
        if new_amount <= 0:
            self.assets.pop(currency, None)
        else:
            self.assets[currency] = (old_price, new_amount)

    @staticmethod
    def _fail(result: Dict[str, Any], message: str) -> Dict[str, Any]:
        result["state"] = "failed"
        result["msg"] = message
        result["price"] = 0
        result["amount"] = 0
        result["fee"] = 0
        return result

    def _register_conditional(self, request, callback):
        self.pending_conditionals.append({
            "request": copy.deepcopy(request), "callback": callback,
        })
        callback(self._result(
            request, "requested", "success", request.get("price", 0),
            request.get("amount", 0),
        ))

    def _condition_fired(self, request, price):
        ord_type = order_spec.get_ord_type(request)
        trigger = self._positive_finite(request.get("trigger"))
        if trigger is None:
            return False
        if ord_type == order_spec.STOP_LOSS:
            return price <= trigger
        if ord_type == order_spec.TAKE_PROFIT:
            return price >= trigger
        return False

    def _check_conditionals(self, currency, price):
        remaining = []
        for entry in self.pending_conditionals:
            request = entry["request"]
            if request.get("currency", self.currency) == currency and \
                    self._condition_fired(request, price):
                result = self._fill_conditional(request, currency, price)
                self._finish(result, entry["callback"])
            else:
                remaining.append(entry)
        self.pending_conditionals = remaining

    def _fill_conditional(self, request, currency, price):
        amount = self._positive_finite(request.get("amount"))
        if amount is None:
            return self._result(request, "failed", "잘못된 수량")
        result = self._result(request, "done", "success", price, amount)
        if request.get("type") == "sell":
            self._sell(currency, price, amount, result)
        elif request.get("type") == "buy":
            self._buy(currency, price, amount, result)
        else:
            return self._fail(result, "지원하지 않는 주문 유형")
        result["balance"] = self.balance
        return result
