from abc import *

# 전체 시스템을 운영하는 운영자
class Operator(metaclass=ABCMeta):
    dp = None
    algorithm = None
    trader = None

    # 초기화 할 때 필수 모듈의 인스턴스를 전달 받는다.
    # Data Provider, Algorithm, Trader
    @abstractmethod
    def initialize(self, http, dataProvider, algorithm, trader):
        self.http = http
        self.dp = dataProvider
        self.algorithm = algorithm
        self.trader = trader

        if self.dp is not None:
            self.dp(self.http)