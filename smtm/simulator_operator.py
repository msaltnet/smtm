from . import Operator

# 거래소로부터 과거 데이터를 수집해서 순차적으로 제공
class SimulatorOperator(Operator):
    def initialize(self, http, threading, dataProvider, algorithm, trader):
        print('child initialize')
        super().initialize(http, threading, dataProvider, algorithm, trader)

    def setup(self, interval):
        print('child setup')
        super().setup(interval)

    def start(self, threading):
        print('child start')
        return super().start(threading)

    def process(self):
        print('child process')
        return super().process()

    def stop(self):
        print('child stop')
        return super().stop()