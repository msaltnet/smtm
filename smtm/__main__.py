"""시뮬레이터

Example) python -m smtm --count 200 --end 2020-12-20T17:50:30 --term 0.01 --strategy=1
"""
import time
import signal
import argparse
import threading
import requests
from . import (
    LogManager,
    Analyzer,
    SimulationTrader,
    SimulationDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    SimulationOperator,
)


class SmtmSimulator:
    """smtm 시뮬레이터"""

    def __init__(self, end=None, count=100, term=None, strategy=0):
        self.logger = LogManager.get_logger("SmtmSimulator")
        self.__stop = False
        self.end = "2020-12-20T16:23:00"
        self.count = 100
        self.term = term
        self.operator = None
        self.strategy = int(strategy)

        if end is not None:
            self.end = end

        if self.strategy != 0 and self.strategy != 1:
            self.strategy = 0
            self.logger.info(f"invalid strategy: {self.strategy}, replaced with 0")

        if self.end is not None:
            self.end = self.end.replace("T", " ")

        if count is not None:
            self.count = count

        if self.term is None:
            self.term = 2

        self.term = float(self.term)
        self.logger.info(f"end: {self.end}")
        self.logger.info(f"count: {self.count}")
        self.logger.info(f"term: {self.term}")
        self.logger.info("simulation is started ===================")

        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

    def main(self):
        """main 함수"""
        operator = SimulationOperator()
        self.operator = operator
        if self.strategy == 0:
            strategy = StrategyBuyAndHold()
        else:
            strategy = StrategySma0()

        operator.initialize_simulation(
            requests,
            threading,
            SimulationDataProvider(),
            strategy,
            SimulationTrader(),
            Analyzer(),
            end=self.end,
            count=self.count,
            budget=50000,
        )
        operator.setup(self.term)

        if operator.start() is not True:
            self.logger.warning("Fail start")
            return

        def print_score():
            operator.get_score(lambda x: self.logger.info(x))

        threading.Timer(5, print_score).start()
        while not self.__stop:
            time.sleep(1)

    def stop(self, signum, frame):
        """시뮬레이터 중지"""
        self.__stop = True
        if self.operator is not None:
            self.operator.stop()
        self.logger.info(f"Receive Signal {signum} {frame}")
        self.logger.info("Stop Singing")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--end",
        help="simulation end datetime yyyy-MM-dd HH:mm:ss ex)2020-02-10T17:50:37",
        default=None,
    )
    parser.add_argument("--count", help="simulation tick count", default=None)
    parser.add_argument("--term", help="simulation tick interval (seconds)", default=None)
    parser.add_argument("--strategy", help="strategy 0: buy and hold, 1: sma0", default=0)
    args = parser.parse_args()

    simulator = SmtmSimulator(args.end, args.count, args.term, args.strategy)
    simulator.main()
