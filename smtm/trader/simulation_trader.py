import copy
import math
from datetime import datetime
from typing import Any, Callable, Dict, List

from ..log_manager import LogManager
from . import order_spec
from .trader import Trader
from .admission import AdmissionOutcome
from .simulation_admission import SimulationAdmissionControl


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
        self._admission = SimulationAdmissionControl(self)
        self._submissions = {}

    def get_admission_control(self):
        """Return the inactive, synchronous opt-in capability."""
        return self._admission

    def update_quote(self, currency: str, price: float) -> None:
        with self._admission._legacy():
            self._update_quote(currency, price)

    def _update_quote(self, currency, price):
        valid_price = self._positive_finite(price)
        if not isinstance(currency, str) or not currency.strip() or \
                valid_price is None:
            self.logger.warning("Ignoring invalid simulation quote: %r=%r", currency,
                                price)
            return
        self.quotes[currency] = valid_price
        self._check_pending_orders(currency, valid_price)

    def send_request(
        self,
        request_list: List[Dict[str, Any]],
        callback: Callable[[Dict[str, Any]], None],
    ) -> None:
        with self._admission._legacy():
            self._send_request(request_list, callback)

    def _send_request(self, request_list, callback):
        for request in request_list:
            if request.get("type") == "cancel":
                self.cancel_request(request.get("id"))
                continue
            ord_type = order_spec.get_ord_type(request)
            validation_error = self._validate_request(request, ord_type)
            if validation_error:
                self._reject(request, callback, validation_error)
                continue
            if ord_type == order_spec.MARKET:
                self._submit_market(request, callback)
            elif ord_type == order_spec.LIMIT:
                self._submit_limit(request, callback)
            elif ord_type in {order_spec.STOP_LOSS, order_spec.TAKE_PROFIT}:
                self._submit_conditional(request, callback)

    def cancel_request(self, request_id: str) -> None:
        with self._admission._existing() as managed:
            if managed:
                return self._cancel_managed(request_id)
            return self._cancel_request(request_id)

    def _cancel_request(self, request_id):
        if not isinstance(request_id, str):
            return
        entry = self.pending_orders.pop(request_id, None)
        if entry is not None:
            result = self._result(entry["request"], "done", "canceled")
            self._finish(result, entry["callback"])

    def cancel_all_requests(self) -> None:
        with self._admission._existing() as managed:
            if managed:
                with self._admission._lock:
                    entries = list(self.pending_orders.items())
                for request_id, entry in entries:
                    self._cancel_managed(request_id, entry)
            else:
                for request_id in list(self.pending_orders):
                    self.cancel_request(request_id)

    def get_account_info(self) -> Dict[str, Any]:
        with self._admission._lock:
            return self._account_info()

    def _account_info(self):
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

    def get_submission_status(self):
        """Detached managed simulation diagnostics, not safe-to-release proof.

        Pending and callback-failed records retain their original owner. There
        is no exchange transport uncertainty, retry or automatic resolution.
        """
        with self._admission._lock:
            return {request_id: {
                "state": record["state"],
                "callback_failed": record["callback_failed"],
            } for request_id, record in self._submissions.items()}

    def _validate_managed_state(self):
        # Opening does not adopt arbitrary legacy Python objects whose numeric,
        # hash or copy hooks could reenter the final accounting lock.
        def number(value):
            return type(value) in (int, float) and math.isfinite(value) and value >= 0

        valid = (type(self.currency) is str and bool(self.currency.strip())
                 and number(self.balance) and number(self.commission_ratio)
                 and type(self.assets) is dict and type(self.quotes) is dict
                 and type(self.pending_orders) is dict)
        if valid:
            valid = all(type(key) is str and type(value) in (tuple, list)
                        and len(value) == 2 and all(number(item) for item in value)
                        for key, value in self.assets.items())
        if valid:
            valid = all(type(key) is str and number(value) and value > 0
                        for key, value in self.quotes.items())
        if not valid:
            raise RuntimeError("Managed simulation requires plain finite account state")

    def _submit_managed(self, run, requests, callback):
        for original in requests:
            # Caller copying/conversions and validation are preparation, outside
            # the final gate. Only plain numeric values enter accounting below.
            request = dict(original)
            for key in ("price", "amount", "trigger"):
                if key in request and not isinstance(request[key], bool):
                    try:
                        request[key] = float(request[key])
                    except (TypeError, ValueError, OverflowError):
                        request[key] = None
            request = self._snapshot_managed_data(request)
            request_id = request.get("id")
            if request.get("type") == "cancel":
                with self._admission._lock:
                    allowed = self._admission._allows_locked(run)
                if allowed:
                    self._cancel_managed(request_id)
                continue

            record = {
                "run": run, "request": request, "callback": callback,
                "state": "preparing", "callback_failed": False,
                "failure": None, "result": None, "entry": None,
            }
            with self._admission._lock:
                if isinstance(request_id, str) and request_id.strip():
                    if request_id in self._submissions:
                        continue  # Logical IDs cannot replay, even after close.
                    self._submissions[request_id] = record
                if not self._admission._allows_locked(run):
                    record.update(state="not_dispatched", request=None, callback=None)
                    continue

            try:
                ord_type = order_spec.get_ord_type(request)
                validation_error = self._validate_request(request, ord_type)
            except BaseException as error:
                with self._admission._lock:
                    record.update(state="not_dispatched", failure=error,
                                  request=None, callback=None)
                raise
            notifications = []
            with self._admission._lock:
                if not self._admission._allows_locked(run):
                    record.update(state="not_dispatched", request=None, callback=None)
                    continue
                # This is the atomic simulation claim, not a transport mark.
                # All accounting and reservation changes precede publication.
                record["state"] = "settling"
                try:
                    if validation_error:
                        self._reject(request, notifications.append, validation_error)
                    elif ord_type == order_spec.MARKET:
                        self._submit_market(request, notifications.append)
                    elif ord_type == order_spec.LIMIT:
                        self._submit_limit(request, notifications.append)
                    else:
                        self._submit_conditional(request, notifications.append)
                except BaseException as error:
                    record.update(state="settlement_failed", failure=error)
                    raise
                entry = (self.pending_orders.get(request_id)
                         if isinstance(request_id, str) else None)
                if entry is not None:
                    entry.update(callback=callback, admission_run=run,
                                 submission=record, ack_pending=True,
                                 cancel_requested=False, deferred_quote=None)
                    record.update(state="pending", entry=entry)
                else:
                    record["state"] = "settling"
                result = notifications[0]
                record["result"] = copy.deepcopy(result)
            self._deliver_managed(record, result)

    def _quote_managed(self, run, currency, price):
        valid_price = self._positive_finite(price)
        if type(currency) is not str or not currency.strip() or valid_price is None:
            return
        with self._admission._lock:
            if not self._admission._allows_locked(run):
                return
            self.quotes[currency] = valid_price
            entries = [
                (request_id, entry) for request_id, entry in self.pending_orders.items()
                if entry["currency"] == currency and entry.get("admission_run") is run
            ]
        for request_id, entry in entries:
            self._fill_managed_entry(run, request_id, entry, valid_price)

    def _fill_managed_entry(self, run, request_id, entry, price):
        with self._admission._lock:
            if not self._admission._allows_locked(run):
                return
            if (self.pending_orders.get(request_id) is not entry
                    or entry.get("admission_run") is not run
                    or entry["cancel_requested"]
                    or not self._pending_fires(entry["request"], price)):
                return
            if entry["ack_pending"]:
                if entry["deferred_quote"] is None:
                    entry["deferred_quote"] = price
                return  # Initial callback exits before any terminal callback.
            # Claim one exact entry, then let its callback cancel another before
            # examining that next entry. Never claim a fill after close.
            record = entry["submission"]
            record["state"] = "settling"
            del self.pending_orders[request_id]
            try:
                result = self._fill(entry["request"], entry["callback"], price)
                self.order_history.append(copy.deepcopy(result))
                record["result"] = copy.deepcopy(result)
            except BaseException as error:
                record.update(state="settlement_failed", failure=error)
                raise
        self._deliver_managed(record, result)

    def _cancel_managed(self, request_id, expected=None):
        if type(request_id) is not str:
            return
        with self._admission._lock:
            entry = self.pending_orders.get(request_id)
            if entry is None or (expected is not None and entry is not expected):
                return
            run = entry["admission_run"]

        def cancel():
            with self._admission._lock:
                if self.pending_orders.get(request_id) is not entry:
                    return
                if entry["ack_pending"]:
                    entry["cancel_requested"] = True
                    return  # Deliver requested before its terminal callback.
                record = entry["submission"]
                record["state"] = "settling"
                del self.pending_orders[request_id]
                try:
                    result = self._result(entry["request"], "done", "canceled")
                    self.order_history.append(copy.deepcopy(result))
                    record["result"] = copy.deepcopy(result)
                except BaseException as error:
                    record.update(state="settlement_failed", failure=error)
                    raise
            self._deliver_managed(record, result)

        self._admission._call(run, cancel, require_open=False)

    def _deliver_managed(self, record, result):
        # Accounting is already claimed. A callback failure cannot restore the
        # pending order, retry accounting, erase ownership, or invent uncertainty.
        error = None
        requested = result["state"] == "requested"
        entry = record["entry"]
        try:
            record["callback"](result)
        except BaseException as caught:
            error = caught
            with self._admission._lock:
                record["callback_failed"] = True
                if record["failure"] is None:
                    record["failure"] = caught
                if not requested:
                    record["state"] = "settlement_failed"
                self._admission._finish_locked(
                    record["run"], AdmissionOutcome.EXECUTION_FAILURE, caught)
        finally:
            with self._admission._lock:
                cancel = False
                if requested:
                    entry["ack_pending"] = False
                    cancel = entry["cancel_requested"]
                    deferred_quote = entry["deferred_quote"]
                elif error is None:
                    record["state"] = "settled"
                    if not record["callback_failed"]:
                        record.update(request=None, callback=None, result=None, entry=None)
        if cancel:
            try:
                self._cancel_managed(entry["request"]["id"], entry)
            except BaseException:
                if error is None:
                    raise
        elif requested and error is None and deferred_quote is not None:
            self._fill_managed_entry(record["run"], entry["request"]["id"],
                                     entry, deferred_quote)
        if error is not None:
            raise error

    @classmethod
    def _snapshot_managed_data(cls, value):
        # Later result/history snapshots are made under the state lock. Own plain
        # data now, so custom deepcopy/hash/equality hooks cannot run in that lock.
        if type(value) in (str, int, float, bool, type(None)):
            return value
        if type(value) is dict:
            if any(type(key) not in (str, int, float, bool, type(None)) for key in value):
                raise TypeError("Managed simulation request keys must be plain data")
            return {key: cls._snapshot_managed_data(item) for key, item in value.items()}
        if type(value) in (list, tuple):
            return [cls._snapshot_managed_data(item) for item in value]
        raise TypeError("Managed simulation requests must contain plain data")

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

    def _submit_conditional(self, request, callback):
        currency = request.get("currency", self.currency)
        quote = self._positive_finite(self.quotes.get(currency))
        if quote is not None and self._conditional_fires(request, quote):
            return self._finish(self._fill(request, callback, quote), callback)

        amount = self._valid_amount(request.get("amount"))
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
            if entry is not None and entry["currency"] == currency and \
                    self._pending_fires(entry["request"], quote):
                self._fill_pending(request_id, quote)

    def _pending_fires(self, request, quote):
        if order_spec.get_ord_type(request) == order_spec.LIMIT:
            return self._limit_fires(request, quote)
        return self._conditional_fires(request, quote)

    def _conditional_fires(self, request, quote):
        trigger = self._positive_finite(request.get("trigger"))
        if trigger is None:
            return False
        ord_type = order_spec.get_ord_type(request)
        if ord_type == order_spec.STOP_LOSS:
            return quote <= trigger
        if ord_type == order_spec.TAKE_PROFIT:
            return quote >= trigger
        return False

    def _fill_pending(self, request_id, quote):
        entry = self.pending_orders.pop(request_id, None)
        if entry is not None:
            result = self._fill(entry["request"], entry["callback"], quote)
            return self._finish(result, entry["callback"])
        return None

    @staticmethod
    def _fail(result: Dict[str, Any], message: str) -> Dict[str, Any]:
        result["state"] = "failed"
        result["msg"] = message
        result["price"] = 0
        result["amount"] = 0
        result["fee"] = 0
        return result
