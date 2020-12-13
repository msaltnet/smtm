from . import LogManager

class Operator():
    '''
    전체 시스템의 운영을 담당하는 클래스
    '''
    dp = None
    strategy = None
    trader = None
    interval = 10 # default 10 second
    isTimerRunning = False
    threading = None

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)

    def initialize(self, http, threading, dataProvider, strategy, trader):
        '''
        운영에 필요한 모듈과 정보를 설정 및 각 모듈 초기화 수행

        Http: http 클라이언트 requests 인스턴스
        Data Provider: Data Provider 인스턴스
        Strategy: Strategy 인스턴스
        Trader: Trader 인스턴스
        '''
        self.http = http
        self.dp = dataProvider
        self.strategy = strategy
        self.trader = trader
        self.threading = threading

        if self.dp is not None:
            self.dp.initialize(self.http)

    def setup(self, interval):
        '''
        운영에 필요한 기본 정보를 설정한다

        interval : 매매 프로세스 간격
        '''
        self.interval = interval

    def start(self):
        '''자동 거래를 시작한다'''

        if self.dp is None or self.threading is None:
            return False

        if self.isTimerRunning:
            return False

        self.__process()
        return True

    def __start_timer(self):
        '''설정된 간격의 시간이 지난 후 자동 거래를 시작하도록 타이머 설정'''

        if self.dp is None or self.threading is None:
            return False

        if self.isTimerRunning:
            return False

        self.timer = self.threading.Timer(self.interval, self.__process)
        self.timer.start()

        self.isTimerRunning = True
        return True

    def __process(self):
        '''자동 거래를 실행 후 일정 시간 뒤 거래를 트리거한다'''
        if self.dp is None:
            return False
        self.logger.debug("process is started")
        self.isTimerRunning = False
        try:
            self.strategy.update_trading_info(self.dp.get_info())
            self.strategy.get_request()
        finally:
            self.logger.debug("process is completed")
        self.__start_timer()
        return True

    def stop(self):
        '''거래를 중단한다'''
        try:
            self.timer.cancel()
        except AttributeError as identifier:
            self.logger.warning(identifier)
        self.isTimerRunning = False
