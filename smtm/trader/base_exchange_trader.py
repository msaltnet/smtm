import os
import copy
import threading
from datetime import datetime
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

    def _request_post(self, url, headers=None, params=None, data=None):
        try:
            kwargs = {"headers": headers}
            if params is not None:
                kwargs["params"] = params
            if data is not None:
                kwargs["data"] = data
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
