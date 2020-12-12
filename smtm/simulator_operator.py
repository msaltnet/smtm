from . import Operator

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