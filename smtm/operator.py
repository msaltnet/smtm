from . import LogManager

class Operator():
    """
    전체 시스템의 운영을 담당하는 클래스

    dp: 사용될 DataProvider 인스턴스
    strategy: 사용될 Strategy 인스턴스
    trader: 사용될 Trader 인스턴스
    threading: 타이머를 위해서 사용될 시스템 threading 인스턴스
    interval: 매매 프로세스가 수행되는 간격 # default 10 second
    """

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.dp = None
        self.strategy = None
        self.trader = None
        self.interval = 10 # default 10 second
        self.is_timer_running = False
        self.is_terminating = False
        self.threading = None
        self.is_initialized = False
        self.timer = None
        self.analyzer = None

    def initialize(self, http, threading, dataProvider, strategy, trader, analyzer):
        """
        운영에 필요한 모듈과 정보를 설정 및 각 모듈 초기화 수행

        http: http 클라이언트 requests 객체
        threading: 타이머 동작을 위한 threading 객체
        dataProvider: 운영에 사용될 DataProvider 객체
        strategy: 운영에 사용될 Strategy 객체
        trader: 운영에 사용될 Trader 객체
        analyzer: 운영에 사용될 Analyzer 객체
        """
        self.http = http
        self.dp = dataProvider
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
        """자동 거래를 시작한다"""
        if self.is_initialized != True:
            return False

        if self.is_timer_running:
            return False

        self.logger.info('===== Start operating =====')
        self._excute_trading()
        return True

    def _start_timer(self):
        """설정된 간격의 시간이 지난 후 자동 거래를 시작하도록 타이머 설정"""
        if (self.is_timer_running or self.is_initialized != True
            or self.is_terminating):
            return

        self.timer = self.threading.Timer(self.interval, self._excute_trading)
        self.timer.start()

        self.is_timer_running = True
        return

    def _excute_trading(self):
        """자동 거래를 실행 후 타이머를 실행한다"""
        self.logger.debug("trading is started #####################")
        self.is_timer_running = False
        try:
            self.strategy.update_trading_info(self.dp.get_info())
            def send_request_callback(result):
                self.logger.info("send_request_callback is called")
                self.strategy.update_result(result)
                self.analyzer.put_result(result)
            target_request = self.strategy.get_request()

            if target_request is not None and target_request.price != 0:
                self.trader.send_request(target_request, send_request_callback)
                self.analyzer.put_request(target_request)
        except AttributeError:
            self.logger.error('excuting fail')

        self.logger.debug("trading is completed #####################")
        self._start_timer()
        return True

    def stop(self):
        """거래를 중단한다"""
        self.logger.info('===== Stop operating =====')
        try:
            self.timer.cancel()
        except AttributeError:
            self.logger.error('stop operation fail')
        self.is_timer_running = False
        self.is_terminating = True
