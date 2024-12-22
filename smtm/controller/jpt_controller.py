from IPython.display import Image, display
from ..config import Config
from ..log_manager import LogManager
from ..analyzer import Analyzer
from ..trader.upbit_trader import UpbitTrader
from ..data.upbit_data_provider import UpbitDataProvider
from ..trader.bithumb_trader import BithumbTrader
from ..data.bithumb_data_provider import BithumbDataProvider
from ..strategy.strategy_factory import StrategyFactory
from ..operator import Operator


class JptController:
    """
    Jupyter notebook용 자동 거래 시스템 컨트롤러
    Controller for Jupyter notebook
    """

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
        self.strategy_code = strategy
        self.strategy = None
        self.market = market
        self.commission_ratio = commission_ratio
        self.operator = None
        self.need_init = True
        self.logger = LogManager.get_logger("JptController")

    def initialize(self, interval=10, strategy=0, budget=50000, is_bithumb=False):
        self.interval = interval
        self.strategy_code = strategy
        self.budget = budget

        self.strategy = StrategyFactory.create(self.strategy_code)
        if self.strategy is None:
            raise UserWarning(f"Invalid Strategy! {self.strategy_code}")

        self.operator = Operator()
        if is_bithumb:
            data_provider = BithumbDataProvider(currency=self.market)
            trader = BithumbTrader(
                currency=self.market, commission_ratio=0.0005, budget=self.budget
            )
        else:
            data_provider = UpbitDataProvider(
                currency=self.market, interval=Config.candle_interval
            )
            trader = UpbitTrader(
                currency=self.market, commission_ratio=0.0005, budget=self.budget
            )

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
        print(
            f"interval: {self.interval}, strategy: {self.strategy.NAME}, budget: {self.budget}"
        )

    def start(self):
        if self.operator is None or self.need_init:
            print("초기화가 필요합니다")
            return

        if self.operator.start() is not True:
            print("프로그램 시작을 실패했습니다")
            return
        print("자동 거래가 시작되었습니다")

    def stop(self):
        if self.operator is not None:
            self.operator.stop()
            self.need_init = True
            print("프로그램을 재시작하려면 초기화하세요")

    def get_state(self):
        state = "NOT INITIALIZED"
        if self.operator is not None:
            state = self.operator.state.upper()

        print(f"현재 시스템 상태: {state}")

    def get_score(self, index=None):
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
        """
        로그 레벨 설정 (CRITICAL=50, ERROR=40, WARN=30, INFO=20, DEBUG=10)
        """

        LogManager.set_stream_level(int(value))
        print(f"Log level set {value}")
        print("(CRITICAL=50, ERROR=40, WARN=30, INFO=20, DEBUG=10)")
