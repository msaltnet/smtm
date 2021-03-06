"""시뮬레이터"""
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
    SimulationOperator,
)


class SmtmSimulator:
    """smtm 시뮬레이터"""

    def __init__(self, end=None, count=100, term=None):
        self.logger = LogManager.get_logger("SmtmSimulator")
        self.__stop = False
        self.end = "2020-12-20T16:23:00"
        self.count = 100
        self.term = term
        self.operator = None

        if end is not None:
            self.end = end

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
        operator.initialize_simulation(
            requests,
            threading,
            SimulationDataProvider(),
            StrategyBuyAndHold(),
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
    args = parser.parse_args()

    simulator = SmtmSimulator(args.end, args.count, args.term)
    simulator.main()
