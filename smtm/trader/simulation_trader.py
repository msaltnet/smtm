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

    def __init__(self, budget=50000, currency="BTC", commission_ratio=0):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.balance = float(budget)
        self.currency = currency
        self.commission_ratio = 0
        self.assets = {}
        self.quotes = {}
        self.order_history = []
        self.pending_conditionals = []  # [{"request":..., "callback":...}]

    def update_quote(self, currency: str, price: float) -> None:
        valid_price = self._positive_finite(price)
        if not isinstance(currency, str) or not currency.strip() or \
                valid_price is None:
            self.logger.warning("Ignoring invalid simulation quote: %r=%r", currency,
                                price)
            return
        self.quotes[currency] = valid_price
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
            result = self._execute_request(request)
            self._finish(result, callback)

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
            "asset": dict(self.assets),
            "quote": dict(self.quotes),
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

        order_type = request.get("type")
        if order_type not in {"buy", "sell"}:
            return f"지원하지 않는 매매 유형: {order_type}"

        if self._positive_finite(request.get("amount")) is None:
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

    def _execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        currency = request.get("currency", self.currency)
        fill_price = self._positive_finite(self.quotes.get(currency))
        if fill_price is None:
            return self._result(request, "failed", "시세 없음")

        amount = self._positive_finite(request.get("amount"))
        if amount is None:
            return self._result(request, "failed", "잘못된 수량")

        result = self._result(request, "done", "success", fill_price, amount)

        if request.get("type") == "buy":
            self._buy(currency, fill_price, amount, result)
        elif request.get("type") == "sell":
            self._sell(currency, fill_price, amount, result)
        else:
            self._fail(result, "지원하지 않는 주문 유형")

        result["balance"] = self.balance
        return result

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
