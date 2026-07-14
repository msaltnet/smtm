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
        self.quotes[currency] = float(price)
        self._check_conditionals(currency, float(price))

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
            if ord_type not in self.SUPPORTED_ORD_TYPES:
                callback(order_spec.make_rejected_result(
                    request, f"unsupported ord_type: {ord_type}"))
                continue
            if order_spec.is_conditional(request):
                self._register_conditional(request, callback)
                continue
            result = self._execute_request(request)
            self.order_history.append(result)
            callback(result)

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

    def _execute_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        currency = request.get("currency", self.currency)
        result = {
            "request": request,
            "type": request.get("type"),
            "price": request.get("price", 0),
            "amount": request.get("amount", 0),
            "msg": "success",
            "balance": self.balance,
            "state": "done",
            "date_time": request.get(
                "date_time", datetime.now().strftime(self.ISO_DATEFORMAT)
            ),
        }

        fill_price = self.quotes.get(currency)
        if fill_price is None:
            return self._fail(result, "시세 없음")

        amount = float(request.get("amount", 0))
        if amount <= 0:
            return self._fail(result, "잘못된 수량")

        result["price"] = fill_price
        result["amount"] = amount

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
        fee = trade_value * self.commission_ratio
        total_cost = trade_value + fee
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
        fee = trade_value * self.commission_ratio
        new_amount = round(old_amount - amount, 6)

        self.balance += trade_value - fee
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
        return result

    def _register_conditional(self, request, callback):
        self.pending_conditionals.append({"request": request, "callback": callback})
        callback({
            "request": request,
            "type": request.get("type"),
            "price": request.get("price", 0),
            "amount": request.get("amount", 0),
            "msg": "success",
            "balance": self.balance,
            "state": "requested",
            "date_time": request.get(
                "date_time", datetime.now().strftime(self.ISO_DATEFORMAT)
            ),
        })

    def _condition_fired(self, request, price):
        ord_type = order_spec.get_ord_type(request)
        trigger = float(request.get("trigger", 0) or 0)
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
                self.order_history.append(result)
                entry["callback"](result)
            else:
                remaining.append(entry)
        self.pending_conditionals = remaining

    def _fill_conditional(self, request, currency, price):
        amount = float(request.get("amount", 0) or 0)
        result = {
            "request": request,
            "type": request.get("type"),
            "price": price,
            "amount": amount,
            "msg": "success",
            "balance": self.balance,
            "state": "done",
            "date_time": datetime.now().strftime(self.ISO_DATEFORMAT),
        }
        if amount <= 0:
            return self._fail(result, "잘못된 수량")
        if request.get("type") == "sell":
            self._sell(currency, price, amount, result)
        elif request.get("type") == "buy":
            self._buy(currency, price, amount, result)
        else:
            return self._fail(result, "지원하지 않는 주문 유형")
        result["balance"] = self.balance
        return result
