from . import Operator

# 거래소로부터 과거 데이터를 수집해서 순차적으로 제공
class SimulatorOperator(Operator):
    def initialize(self, http, dataProvider, algorithm, trader):
        super().initialize(http, dataProvider, algorithm, trader)

    def setup(self, interval):
        super().setup(interval)

    def start(self, threading):
        return super().start(threading)

    def process(self):
        return super().process()