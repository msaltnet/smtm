from .log_manager import LogManager
from .operator import Operator

class SimulationOperator(Operator):
    def __init__(self):
        self.logger = LogManager.get_logger(__name__)

    def initialize(self, http, threading, dataProvider, algorithm, trader, end, count, budget):
        super().initialize(http, threading, dataProvider, algorithm, trader)
        self.trader.initialize(http, end, count, budget)

    def setup(self, interval):
        super().setup(interval)

    def start(self):
        return super().start()

    def stop(self):
        super().stop()