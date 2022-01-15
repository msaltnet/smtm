"""Jupyter notebook용 자동 거래 시스템 운영 인터페이스 JptController 클래스

Jupyter notebook에서 사용하기 좋게 만든 자동 거래 시스템 컨트롤 모듈
"""
from IPython.display import Image, display
from . import (
    LogManager,
    Analyzer,
    UpbitTrader,
    UpbitDataProvider,
    BithumbTrader,
    BithumbDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    Operator,
)


class JptController:
    """Jupyter notebook용 자동 거래 시스템 컨트롤러"""

    def __init__(
        self,
        interval=10,
        strategy=0,
        budget=50000,
        market="BTC",
        commission_ratio=0.0005,
    ):
        self.interval = interval
        self.budget = budget
        self.strategy_num = strategy
        self.strategy = None
        self.market = market
        self.commission_ratio = commission_ratio
        self.operator = None
        self.need_init = True
        self.logger = LogManager.get_logger("JptController")

    def initialize(self, interval=10, strategy=0, budget=50000, is_bithumb=False):
        """설정 값으로 초기화"""
        self.interval = interval
        self.strategy_num = strategy
        self.budget = budget
        self.strategy = StrategyBuyAndHold() if self.strategy_num == 0 else StrategySma0()
        self.operator = Operator()
        if is_bithumb:
            data_provider = BithumbDataProvider(currency=self.market)
            trader = BithumbTrader(
                currency=self.market, commission_ratio=0.0005, budget=self.budget
            )
        else:
            data_provider = UpbitDataProvider(currency=self.market)
            trader = UpbitTrader(currency=self.market, commission_ratio=0.0005, budget=self.budget)

        self.operator.initialize(
            data_provider,
            self.strategy,
            trader,
            Analyzer(),
            budget=self.budget,
        )
        self.operator.set_interval(self.interval)
        self.need_init = False
        print("##### smtm is intialized #####")
        print(f"interval: {self.interval}, strategy: {self.strategy.NAME}, budget: {self.budget}")

    def start(self):
        """프로그램 시작, 재시작"""
        if self.operator is None or self.need_init:
            print("초기화가 필요합니다")
            return

        if self.operator.start() is not True:
            print("프로그램 시작을 실패했습니다")
            return
        print("자동 거래가 시작되었습니다")

    def stop(self):
        """프로그램 중지"""
        if self.operator is not None:
            self.operator.stop()
            self.need_init = True
            print("프로그램을 재시작하려면 초기화하세요")

    def get_state(self):
        """현재 상태 출력 출력"""
        state = "NOT INITIALIZED"
        if self.operator is not None:
            state = self.operator.state.upper()

        print(f"현재 시스템 상태: {state}")

    def get_score(self, index=None):
        """현재 수익률과 그래프 출력"""

        if self.operator is None:
            print("초기화가 필요합니다")
            return

        def print_score_and_main_statement(score):
            print("current score ==========")
            print(score)
            if len(score) > 4 and score[4] is not None:
                display(Image(filename=score[4]))

        self.operator.get_score(print_score_and_main_statement, index)

    def get_trading_record(self):
        """현재까지 거래 기록 출력"""

        if self.operator is None:
            print("초기화가 필요합니다")
            return

        results = self.operator.get_trading_results()
        if results is None or len(results) == 0:
            print("거래 기록이 없습니다")
            return

        for result in results:
            print(f"@{result['date_time']}, {result['type']}")
            print(f"{result['price']} x {result['amount']}")

    @staticmethod
    def set_log_level(value):
        """로그 레벨 설정
        (CRITICAL=50, ERROR=40, WARN=30, INFO=20, DEBUG=10)"""

        LogManager.set_stream_level(int(value))
        print(f"Log level set {value}")
        print("(CRITICAL=50, ERROR=40, WARN=30, INFO=20, DEBUG=10)")
