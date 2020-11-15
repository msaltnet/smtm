from abc import *

# 전체 시스템을 운영하는 운영자
class Operator(metaclass=ABCMeta):
    dp = None
    algorithm = None
    trader = None
    interval = 10 # default 10 second

    # 초기화 할 때 필수 모듈의 인스턴스를 전달 받는다
    # Data Provider, Algorithm, Trader
    @abstractmethod
    def initialize(self, http, dataProvider, algorithm, trader):
        self.http = http
        self.dp = dataProvider
        self.algorithm = algorithm
        self.trader = trader

        if self.dp is not None:
            self.dp(self.http)

    # 운영에 필요한 기본 정보를 전달 받는다
    # interval : 거래 간격
    @abstractmethod
    def setup(self, interval):
        self.interval = interval

    # 자동 거래를 시작한다
    @abstractmethod
    def start(self, threading):
        if self.dp is None:
            return False

        self.timer = threading.Timer(self.interval, self.process)
        return True

    # 주기적으로 자동 거래를 실행한다
    @abstractmethod
    def process(self):
        if self.dp is None:
            return False

        self.dp.get_info()
