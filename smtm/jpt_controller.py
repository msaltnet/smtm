"""Jupyter notebook용 시스템 운영 인터페이스

Jupyter notebook에서 사용하기 좋게 만든 Operator를 사용해서 시스템을 컨트롤하는 모듈
"""
import signal
import time
from IPython.display import clear_output
from IPython.display import Image, display
from . import (
    LogManager,
    Analyzer,
    UpbitTrader,
    UpbitDataProvider,
    StrategyBuyAndHold,
    Controller,
)


class JptController(Controller):
    """smtm 컨트롤러"""

    def __init__(self, interval=10, strategy=0, budget=50000):
        super().__init__(interval=interval, strategy=strategy, budget=budget)
        self.logger = LogManager.get_logger("JptController")

    def main(self):
        """main 함수"""

        self.operator.initialize(
            UpbitDataProvider(),
            self.strategy,
            UpbitTrader(),
            Analyzer(),
            budget=self.budget,
        )

        self.operator.set_interval(self.interval)
        strategy_name = "Buy and Hold" if isinstance(self.strategy, StrategyBuyAndHold) else "SMA0"
        print("##### smtm is intialized #####")
        print(f"interval: {self.interval}, strategy: {strategy_name}")
        print("==============================")

        self.logger.info(f"interval: {self.interval}")
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

        while not self.terminating:
            try:
                key = input(self.MAIN_STATEMENT)
                clear_output(wait=False)
                time.sleep(0.1)
                self.logger.debug(f"Execute command {key}")
                self._on_command(key)
            except EOFError:
                break

    def _get_score(self):
        def print_score_and_main_statement(score):
            print("current score ==========")
            print(score)
            if len(score) > 4 and score[4] is not None:
                display(Image(filename=score[4]))

        self.operator.get_score(print_score_and_main_statement)
