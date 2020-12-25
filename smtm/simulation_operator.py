from .log_manager import LogManager
from .operator import Operator

class SimulationOperator(Operator):
    """
    각 모듈을 연동해 시뮬레이션을 진행하는 클래스
    """

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)

    def initialize(self, http, threading, dataProvider, algorithm, trader, end, count, budget):
        """
        시뮬레이션에 사용될 각 모듈을 전달 받아 초기화를 진행한다

        end: 언제까지의 거래기간 정보를 사용할 것인지에 대한 날짜 시간 정보
        count: 사용될 거래 정도 갯수
        budget: 사용될 예산
        """
        super().initialize(http, threading, dataProvider, algorithm, trader)
        self.trader.initialize(http, end, count, budget)

    def setup(self, interval):
        super().setup(interval)

    def start(self):
        return super().start()

    def stop(self):
        super().stop()