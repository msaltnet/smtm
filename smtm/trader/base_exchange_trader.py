import os
import copy
import threading
from datetime import datetime
from functools import wraps
import requests
from ..log_manager import LogManager
from ..http_session import request_with_retry
from .trader import Trader
from ..worker import Worker


class BaseExchangeTrader(Trader):
    """
    거래소 Trader의 공통 로직을 제공하는 기본 클래스

    Base class providing common logic for exchange traders.
    Subclasses must implement exchange-specific methods:
        - _execute_order(task)
        - cancel_request(request_id)
        - get_account_info()
        - get_trade_tick()
    """

    RESULT_CHECKING_INTERVAL = 5
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(
        self,
        budget,
        currency,
        commission_ratio,
        opt_mode,
        logger_name,
        worker_name,
        env_key_names,
    ):
        """
        Args:
            budget: 초기 예산
            currency: 거래 통화
            commission_ratio: 수수료 비율
            opt_mode: 가격 최적화 모드
            logger_name: 로거 이름
            worker_name: 워커 이름
            env_key_names: (ACCESS_KEY_ENV, SECRET_KEY_ENV, SERVER_URL_ENV) 환경변수 이름 튜플
        """
        self.logger = LogManager.get_logger(logger_name)
        self.worker = Worker(worker_name)
        self.worker.start()
        self.timer = None
        self.order_map = {}
        self._submissions = {}
        self._submission_context = threading.local()
        self.ACCESS_KEY = os.environ.get(env_key_names[0], "")
        self.SECRET_KEY = os.environ.get(env_key_names[1], "")
        self.SERVER_URL = os.environ.get(env_key_names[2], "")
        if not self.ACCESS_KEY or not self.SECRET_KEY or not self.SERVER_URL:
            self.logger.warning(f"{logger_name} API credentials are not set")
        self.is_opt_mode = opt_mode
        self.asset = (0, 0)  # avr_price, amount
        self.balance = budget
        self.commission_ratio = commission_ratio

    @staticmethod
    def track_submission(execute):
        """Reserve a logical creation's owner without changing the public API.

        Each adapter opts in. Thread-local context binds the eventual HTTP
        creation boundary to this invocation, including concurrent/reentrant
        calls. Cancellation is not a new submission.
        """
        @wraps(execute)
        def tracked(self, task):
            request = task["request"]
            if request["type"] == "cancel":
                return execute(self, task)
            request_id = request["id"]
            with self._order_lock:
                if request_id in self._submissions or request_id in self.order_map:
                    self.logger.warning("Duplicate order request ID suppressed")
                    return
                submission = {
                    "request": request, "callback": task["callback"],
                    "state": "preparing", "dispatched": False,
                    "exchange_id": None, "order": None,
                }
                self._submissions[request_id] = submission
            previous = getattr(self._submission_context, "current", None)
            self._submission_context.current = submission
            try:
                return execute(self, task)
            finally:
                self._submission_context.current = previous
                with self._order_lock:
                    if submission["state"] == "preparing":
                        submission["state"] = "not_dispatched"
                        submission.update(request=None, callback=None)

        return tracked

    def get_submission_status(self):
        """Return detached diagnostics, never a safe-to-release guarantee.

        Unknown outcomes keep their original request/callback in _submissions;
        only known exchange IDs enter order_map. Records are in-memory only.
        """
        with self._order_lock:
            return {request_id: {
                "state": record["state"],
                "dispatched": record["dispatched"],
                "exchange_id": record["exchange_id"],
            } for request_id, record in self._submissions.items()}

    def _mark_creation_dispatch(self):
        submission = getattr(self._submission_context, "current", None)
        if submission is None:
            return  # Direct private transport calls still get one attempt.
        with self._order_lock:
            if submission["dispatched"]:
                raise RuntimeError("Order creation already attempted")
            # Set before the physical call. A raised exception or unusable ACK
            # cannot establish non-execution, so uncertainty is the default.
            submission["dispatched"] = True
            submission["state"] = "unknown"

    @staticmethod
    def _usable_order_id(response, key, integer=False):
        if not isinstance(response, dict):
            return False
        value = response.get(key)
        if integer:
            return type(value) is int and 0 < value <= 2 ** 63 - 1
        return isinstance(value, str) and bool(value.strip()) and value == value.strip()

    def _submission_unacknowledged(self, task):
        submission = getattr(self._submission_context, "current", None)
        # Keep legacy local failure reporting, but never turn an ambiguous
        # physical creation into terminal failure or a new accounting result.
        if submission is None or not submission["dispatched"]:
            task["callback"]("error!")
        else:
            self.logger.warning("Order outcome unknown; automatic resubmission disabled")

    def _register_submitted_order(self, task, exchange_id, id_key):
        result = self._create_success_result(task["request"])
        # Terminal cancellation/polling can mutate order["result"] immediately
        # after publication. Its ACK callback must remain non-settling.
        acknowledgement = result.copy() if isinstance(result, dict) else result
        order = {id_key: exchange_id, "callback": task["callback"], "result": result,
                 "ack_pending": True}
        with self._order_lock:
            submission = self._submission_context.current
            submission.update(state="known", exchange_id=exchange_id, order=order)
            self.order_map[task["request"]["id"]] = order
        try:
            task["callback"](acknowledgement)
        finally:
            # Release terminal claiming only after the initial ACK callback
            # exits. Reentrant cancel/poll defers settlement instead of waiting
            # on this callback or delivering done before requested.
            with self._order_lock:
                order["ack_pending"] = False
                if self.order_map:
                    self._start_timer()

    def _settle_submission(self, request_id, order, result):
        # Existing adapters have already atomically claimed the terminal order.
        # Legacy manually inserted order_map entries may have no submission.
        with self._order_lock:
            submission = getattr(self, "_submissions", {}).get(request_id)
            if submission is not None and submission["order"] is not order:
                submission = None
            if submission is not None:
                submission["state"] = "settling"
        try:
            self._call_callback(order["callback"], result)
        except BaseException:
            with self._order_lock:
                if submission is not None:
                    submission["state"] = "settlement_failed"
            raise
        else:
            with self._order_lock:
                if submission is not None:
                    submission["state"] = "settled"
                    # Keep a compact attempted-ID tombstone to suppress replay.
                    submission.update(request=None, callback=None, order=None)

    @staticmethod
    def _create_success_result(request):
        return {
            "state": "requested",
            "request": request,
            "type": request["type"],
            "price": request["price"],
            "amount": request["amount"],
            "msg": "success",
        }

    def send_request(self, request_list, callback):
        """거래 요청을 처리한다

        request_list: 한 개 이상의 거래 요청 정보 리스트
        [{
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간
        }]
        callback(result): 결과를 전달할 콜백함수
        """
        for request in request_list:
            self.worker.post_task(
                {
                    "runnable": self._execute_order,
                    "request": request,
                    "callback": callback,
                }
            )

    def cancel_all_requests(self):
        """모든 거래 요청을 취소한다
        체결되지 않고 대기중인 모든 거래 요청을 취소한다
        """
        orders = copy.deepcopy(self.order_map)
        for request_id in orders.keys():
            self.cancel_request(request_id)

    def _start_timer(self):
        if self.timer is not None:
            return

        def post_query_result_task():
            self.worker.post_task({"runnable": self._update_order_result})

        self.timer = threading.Timer(
            self.RESULT_CHECKING_INTERVAL, post_query_result_task
        )
        self.timer.start()

    def _stop_timer(self):
        if self.timer is None:
            return

        self.timer.cancel()
        self.timer = None

    def _call_callback(self, callback, result):
        result_value = float(result["price"]) * float(result["amount"])
        fee = result_value * self.commission_ratio

        if result["state"] == "done" and result["type"] == "buy":
            old_value = self.asset[0] * self.asset[1]
            new_value = old_value + result_value
            new_amount = self.asset[1] + float(result["amount"])
            new_amount = round(new_amount, 6)
            if new_amount == 0:
                avr_price = 0
            else:
                avr_price = new_value / new_amount
            self.asset = (avr_price, new_amount)
            self.balance -= round(result_value + fee)
        elif result["state"] == "done" and result["type"] == "sell":
            old_avr_price = self.asset[0]
            new_amount = self.asset[1] - float(result["amount"])
            new_amount = round(new_amount, 6)
            if new_amount == 0:
                old_avr_price = 0
            self.asset = (old_avr_price, new_amount)
            self.balance += round(result_value - fee)

        callback(result)

    def _validate_credentials(self):
        """API 자격 증명이 설정되었는지 확인한다"""
        if not self.ACCESS_KEY or not self.SECRET_KEY or not self.SERVER_URL:
            self.logger.error("API credentials are not configured")
            return False
        return True

    def _request_get(self, url, headers=None, params=None):
        try:
            if params is not None:
                response = request_with_retry(
                    requests.get, url, params=params, headers=headers
                )
            else:
                response = request_with_retry(
                    requests.get, url, headers=headers
                )
            response.raise_for_status()
            result = response.json()
        except ValueError as err:
            self.logger.error(f"Invalid data from server: {err}")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result

    def _request_post(self, url, headers=None, params=None, data=None, *, creation=False):
        try:
            kwargs = {"headers": headers}
            if params is not None:
                kwargs["params"] = params
            if data is not None:
                kwargs["data"] = data
            if creation:
                self._mark_creation_dispatch()
                # No redirect replay (307/308) and no transient-error retry.
                response = request_with_retry(
                    requests.post, url, retries=0, allow_redirects=False, **kwargs)
                if not 200 <= response.status_code < 300:
                    return None
            else:
                response = request_with_retry(requests.post, url, **kwargs)
            response.raise_for_status()
            result = response.json()
        except ValueError as err:
            self.logger.error(f"Invalid data from server: {err}")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result
