"""대량시뮬레이터

SimulationOperator를 사용해서 대량 시뮬레이션을 수행하는 모듈
"""
import json
import time
from . import (
    LogManager,
    DateConverter,
    SimulationDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    SimulationOperator,
    SimulationTrader,
    Analyzer,
)


class MassSimulator:
    """대량시뮬레이터
    설정 파일을 사용하여 대량 시뮬레이션 진행
    """

    def __init__(self):
        self.logger = LogManager.get_logger("MassSimulator")

    def _load_config(self, config_file):
        with open(config_file) as json_file:
            json_data = json.load(json_file)
        return json_data

    @staticmethod
    def run_single(operator):
        operator.start()
        while operator.state == "running":
            time.sleep(0.5)

        operator.stop()

    @staticmethod
    def get_initialized_operator(budget, strategy_num, interval, currency, start, end, tag):
        dt = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=999999999999999)
        end = dt[0][1]
        count = dt[0][2]

        data_provider = SimulationDataProvider(currency=currency)
        data_provider.initialize_simulation(end=end, count=count)

        strategy = StrategyBuyAndHold() if strategy_num == 0 else StrategySma0()
        strategy.is_simulation = True

        trader = SimulationTrader(currency=currency)
        trader.initialize_simulation(end=end, count=count, budget=budget)

        analyzer = Analyzer()
        analyzer.is_simulation = True

        operator = SimulationOperator()
        operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=budget,
        )
        operator.tag = tag
        operator.set_interval(interval)
        return operator

    def run(self, config_file):
        """설정 파일의 내용으로 기간을 변경하며 시뮬레이션 진행"""
        config = self._load_config(config_file)
        title = config["title"]
        budget = config["budget"]
        strategy = config["strategy"]
        interval = config["interval"]
        currency = config["currency"]
        period_list = config["period_list"]
        for idx, period in enumerate(period_list):
            tag = f"MASS-{title}-{idx}"
            operator = self.get_initialized_operator(
                budget, strategy, interval, currency, period["start"], period["end"], tag
            )
            self.run_single(operator)
