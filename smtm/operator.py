"""시스템의 운영을 담당

이 모듈은 각 모듈을 컨트롤하여 전체 시스템을 운영한다.
"""

import time
from datetime import datetime
from .log_manager import LogManager
from .worker import Worker


class Operator:
    """
    전체 시스템의 운영을 담당하는 클래스

    Attributes:
        data_provider: 사용될 DataProvider 인스턴스
        strategy: 사용될 Strategy 인스턴스
        trader: 사용될 Trader 인스턴스
        threading: 타이머를 위해서 사용될 시스템 threading 인스턴스
        analyzer: 거래 분석용 Analyzer 인스턴스
        interval: 매매 프로세스가 수행되는 간격 # default 10 second
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self):
        self.http = None
        self.logger = LogManager.get_logger(__name__)
        self.data_provider = None
        self.strategy = None
        self.trader = None
        self.interval = 10  # default 10 second
        self.is_timer_running = False
        self.threading = None
        self.timer = None
        self.analyzer = None
        self.worker = Worker("Operator-Worker")
        self.state = None

    def initialize(self, http, threading, data_provider, strategy, trader, analyzer):
        """
        운영에 필요한 모듈과 정보를 설정 및 각 모듈 초기화 수행

        http: http 클라이언트 requests 객체
        threading: 타이머 동작을 위한 threading 객체
        data_provider: 운영에 사용될 DataProvider 객체
        strategy: 운영에 사용될 Strategy 객체
        trader: 운영에 사용될 Trader 객체
        analyzer: 운영에 사용될 Analyzer 객체
        """
        if self.state is not None:
            return

        self.http = http
        self.data_provider = data_provider
        self.strategy = strategy
        self.trader = trader
        self.threading = threading
        self.analyzer = analyzer
        self.state = "ready"

    def set_interval(self, interval):
        """자동 거래 시간 간격을 설정한다.

        interval : 매매 프로세스가 수행되는 간격
        """
        self.interval = interval

    def start(self):
        """자동 거래를 시작한다

        자동 거래는 설정된 시간 간격에 맞춰서 Worker를 사용해서 별도의 스레드에서 처리된다.
        """
        if self.state != "ready":
            return False

        if self.is_timer_running:
            return False

        self.logger.info("===== Start operating =====")
        self.state = "running"
        self.worker.start()
        self.worker.post_task({"runnable": self._excute_trading})
        return True

    def _start_timer(self):
        """설정된 간격의 시간이 지난 후 Worker가 자동 거래를 수행하도록 타이머 설정"""
        self.logger.debug(f"{self.is_timer_running} : {self.state} : {self.threading.get_ident()}")
        if self.is_timer_running or self.state != "running":
            return

        def on_timer_expired():
            self.worker.post_task({"runnable": self._excute_trading})

        self.timer = self.threading.Timer(self.interval, on_timer_expired)
        self.timer.start()

        self.is_timer_running = True
        return

    def _excute_trading(self, task):
        """자동 거래를 실행 후 타이머를 실행한다"""
        self.logger.debug("trading is started #####################")
        self.is_timer_running = False
        try:
            trading_info = self.data_provider.get_info()
            self.strategy.update_trading_info(trading_info)
            self.analyzer.put_trading_info(trading_info)

            def send_request_callback(result):
                self.logger.info("send_request_callback is called")
                self.strategy.update_result(result)
                self.analyzer.put_result(result)

            target_request = self.strategy.get_request()

            if target_request is not None and target_request["price"] != 0:
                self.trader.send_request(target_request, send_request_callback)
                self.analyzer.put_request(target_request)
        except AttributeError as msg:
            self.logger.error(f"excuting fail {msg}")

        self.logger.debug("trading is completed #####################")
        self._start_timer()
        return True

    def stop(self):
        """거래를 중단한다"""
        self.logger.info("===== Stop operating =====")
        try:
            self.timer.cancel()
        except AttributeError:
            self.logger.error("stop operation fail")
        self.is_timer_running = False
        self.state = "terminating"

        def on_terminated():
            self.state = "ready"

        self.worker.register_on_terminated(on_terminated)
        self.worker.stop()

    def get_score(self, callback):
        """현재 수익률을 인자로 전달받은 콜백함수를 호출한다"""

        if self.state != "running":
            self.logger.warning(f"invalid state : {self.state}")
            return

        def get_and_return_score(task):
            try:
                task["callback"](self.analyzer.get_return_report())
            except TypeError:
                self.logger.error("invalid callback")

        self.worker.post_task({"runnable": get_and_return_score, "callback": callback})

    def send_manual_trading_request(self, trading_type, price=0, amount=0, callback=None):
        if price == 0 or amount == 0 or callback is None:
            return

        if self.state != "running":
            self.logger.warning(f"invalid state : {self.state}")
            return

        now = datetime.now().strftime(self.ISO_DATEFORMAT)
        request = {
            "id": "M-" + str(round(time.time(), 3)),
            "type": trading_type,
            "price": price,
            "amount": amount,
            "date_time": now,
        }

        def send_trading_and_return_result(task):
            def send_manual_request_callback(result):
                self.logger.info("send_manual_request_callback is called")
                self.strategy.update_result(result)
                self.analyzer.put_result(result)
                try:
                    task["callback"](result)
                except TypeError:
                    self.logger.error("invalid callback")

            try:
                self.trader.send_request(task["request"], send_manual_request_callback)
                self.analyzer.put_request(task["request"])
            except KeyError:
                self.logger.error("invalid task")

        self.worker.post_task(
            {"runnable": send_trading_and_return_result, "callback": callback, "request": request}
        )
