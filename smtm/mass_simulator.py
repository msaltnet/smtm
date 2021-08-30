"""대량시뮬레이터

SimulationOperator를 사용해서 대량 시뮬레이션을 수행하는 모듈
"""
import json
import time
from datetime import timedelta
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

    CONFIG_FILE_OUTPUT = "output/generated_config.json"

    def __init__(self):
        self.logger = LogManager.get_logger("MassSimulator")
        self.result = []

    def _load_config(self, config_file):
        with open(config_file) as json_file:
            json_data = json.load(json_file)
        return json_data

    @staticmethod
    def run_single(operator):
        operator.start()
        while operator.state == "running":
            time.sleep(0.5)

        return operator.stop()

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
        LogManager.set_stream_level(30)
        title = config["title"]
        budget = config["budget"]
        strategy = config["strategy"]
        interval = config["interval"]
        currency = config["currency"]
        period_list = config["period_list"]
        self.result = [None for x in range(len(period_list))]
        for idx, period in enumerate(period_list):
            tag = f"MASS-{title}-{idx}"
            operator = self.get_initialized_operator(
                budget, strategy, interval, currency, period["start"], period["end"], tag
            )
            self.result[idx] = self.run_single(operator)

    @staticmethod
    def make_config_json(
        title="",
        budget=50000,
        strategy_num=0,
        interval=0.1,
        currency="BTC",
        from_dash_to="210804.000000-210811.000000",
        offset_min=120,
    ):
        iso_format = "%Y-%m-%dT%H:%M:%S"
        config = {
            "title": title,
            "description": "write descriptionf here",
            "budget": budget,
            "strategy": strategy_num,
            "interval": interval,
            "currency": currency,
            "period_list": [],
        }

        start_end = from_dash_to.split("-")
        start_dt = DateConverter.num_2_datetime(start_end[0])
        end_dt = DateConverter.num_2_datetime(start_end[1])
        delta = end_dt - start_dt
        while delta.total_seconds() > 0:
            inter_end_dt = start_dt + timedelta(minutes=offset_min)
            config["period_list"].append(
                {"start": start_dt.strftime(iso_format), "end": inter_end_dt.strftime(iso_format)}
            )
            start_dt = inter_end_dt
            delta = end_dt - start_dt

        with open(MassSimulator.CONFIG_FILE_OUTPUT, "w") as f:
            json.dump(config, f)
        return MassSimulator.CONFIG_FILE_OUTPUT
