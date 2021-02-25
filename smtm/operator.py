"""시스템의 운영을 담당

이 모듈은 각 모듈을 컨트롤하여 전체 시스템을 운영한다.
"""

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

    def __init__(self):
        self.http = None
        self.logger = LogManager.get_logger(__name__)
        self.data_provider = None
        self.strategy = None
        self.trader = None
        self.interval = 10  # default 10 second
        self.is_timer_running = False
        self.is_terminating = False
        self.threading = None
        self.is_initialized = False
        self.timer = None
        self.analyzer = None
        self.worker = Worker("Operator-Worker")

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
        self.http = http
        self.data_provider = data_provider
        self.strategy = strategy
        self.trader = trader
        self.threading = threading
        self.analyzer = analyzer
        self.is_initialized = True

    def setup(self, interval):
        """
        운영에 필요한 기본 정보를 설정한다

        interval : 매매 프로세스가 수행되는 간격
        """
        self.interval = interval

    def start(self):
        """자동 거래를 시작한다

        자동 거래는 설정된 시간 간격에 맞춰서 Worker를 사용해서 별도의 스레드에서 처리된다.
        """
        if self.is_initialized is not True:
            return False

        if self.is_timer_running:
            return False

        self.logger.info("===== Start operating =====")
        self.worker.start()
        self.worker.post_task({"runnable": self._excute_trading})
        return True

    def _start_timer(self):
        """설정된 간격의 시간이 지난 후 Worker가 자동 거래를 수행하도록 타이머 설정"""
        self.logger.debug(
            f"{self.is_timer_running} : {self.is_initialized} : {self.is_terminating}, {self.threading.get_ident()}"
        )
        if self.is_timer_running or self.is_initialized is not True or self.is_terminating:
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
        self.is_terminating = True
        self.worker.stop()
