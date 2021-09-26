"""대량시뮬레이터

SimulationOperator를 사용해서 대량 시뮬레이션을 수행하는 모듈
"""
import os
import json
import time
from datetime import datetime
from datetime import timedelta
import pandas as pd
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

    RESULT_FILE_OUTPUT = "output/"
    CONFIG_FILE_OUTPUT = "output/generated_config.json"
    MIN_PRINT_STATE_SEC = 3

    def __init__(self):
        self.logger = LogManager.get_logger("MassSimulator")
        self.result = []
        self.start = 0
        self.last_print = 0

        if os.path.isdir("output") is False:
            os.mkdir("output")

    def _load_config(self, config_file):
        with open(config_file, encoding="utf-8") as json_file:
            json_data = json.load(json_file)
        return json_data

    def print_state(self, is_start=False, is_end=False):
        """현재 시뮬레이터의 상태를 화면에 표시"""
        iso_format = "%Y-%m-%dT%H:%M:%S"
        now = datetime.now()
        now_string = now.strftime(iso_format)
        if is_start:
            self.start = self.last_print = now
            print(f"{now_string}     +0          simulation start!")
            return

        if is_end:
            total_diff = now - self.start
            print(f"{now_string}     +{total_diff.total_seconds():<10} simulation completed")
            return

        delta = now - self.last_print
        diff = delta.total_seconds()
        if diff > self.MIN_PRINT_STATE_SEC:
            self.last_print = now
            total_diff = now - self.start
            print(f"{now_string}     +{total_diff.total_seconds():<10} simulation is running")

    def run_single(self, operator):
        """시뮬레이션 1회 실행"""
        operator.start()
        while operator.state == "running":
            self.print_state()
            time.sleep(0.1)

        last_report = None

        def get_score_callback(report):
            nonlocal last_report
            last_report = report

        operator.get_score(get_score_callback)
        operator.stop()
        return last_report

    @staticmethod
    def get_initialized_operator(budget, strategy_num, interval, currency, start, end, tag):
        """시뮬레이션 오퍼레이션 생성 후 주어진 설정 값으로 초기화 하여 반환"""
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
        self.print_state(is_start=True)
        for idx, period in enumerate(period_list):
            tag = f"MASS-{title}-{idx}"
            operator = self.get_initialized_operator(
                budget, strategy, interval, currency, period["start"], period["end"], tag
            )
            start_time = datetime.now()
            self.result[idx] = self.run_single(operator)
            diff = datetime.now() - start_time
            print(
                f"{idx} simulation took {diff.total_seconds()} sec : {period['start']} - {period['end']}"
            )
        self.analyze_result(self.result, config)
        self.print_state(is_end=True)

    @staticmethod
    def _round(num):
        return round(num, 3)

    def analyze_result(self, result_list, config):
        """수익률 비교 결과를 파일로 저장"""
        title = config["title"]
        strategy_num = config["strategy"]
        period_list = config["period_list"]
        strategy = StrategyBuyAndHold.NAME if strategy_num == 0 else StrategySma0.NAME

        final_return_list = []
        min_return_list = []
        max_return_list = []
        for result in result_list:
            final_return_list.append(result[2])
            min_return_list.append(result[6])
            max_return_list.append(result[7])
        dataframe = pd.DataFrame(
            {
                "min_return": min_return_list,
                "max_return": max_return_list,
                "final_return": final_return_list,
            }
        )
        # 최종수익율
        df_final = dataframe.sort_values(by="final_return", ascending=False)

        # 순간 최대 수익율
        df_max = dataframe.sort_values(by="max_return", ascending=False)

        # 순간 최저 수익율
        df_mix = dataframe.sort_values(by="min_return")

        with open(f"{self.RESULT_FILE_OUTPUT}{title}.result", "w", encoding="utf-8") as f:
            # 기본 정보
            f.write(f"Title: {title}\n")
            f.write(f"Description: {config['description']}\n")
            f.write(
                f"Strategy: {strategy}, Budget: {config['budget']}, Currency: {config['currency']}\n"
            )
            f.write(
                f"{period_list[0]['start']} ~ {period_list[-1]['end']} ({len(final_return_list)})\n"
            )

            f.write(f"수익률 평균: {self._round(dataframe['final_return'].mean()):8}\n")
            f.write(f"수익률 편차: {self._round(dataframe['final_return'].std()):8}\n")
            f.write(
                f"수익률 최대: {self._round(df_final['final_return'].iloc[0]):8}, {df_final['final_return'].index[0]:3}\n"
            )
            f.write(
                f"수익률 최소: {self._round(df_final['final_return'].iloc[-1]):8}, {df_final['final_return'].index[-1]:3}\n"
            )

            if len(final_return_list) > 10:
                f.write("수익률 TOP 10 ===============================================\n")
                for i in range(10):
                    f.write(
                        f"{self._round(df_final['final_return'].iloc[i]):8}, {df_final['final_return'].index[i]:3}\n"
                    )

                f.write("수익률 WORST 10 ===============================================\n")
                for i in range(10):
                    idx = -1 * (i + 1)
                    f.write(
                        f"{self._round(df_final['final_return'].iloc[idx]):8}, {df_final['final_return'].index[idx]:3}\n"
                    )

                f.write("순간 최대 수익률 BEST 10 =====================================\n")
                for i in range(10):
                    f.write(
                        f"{self._round(df_max['max_return'].iloc[i]):8}, {df_max['max_return'].index[i]:3}\n"
                    )

                f.write("순간 최저 수익률 WORST 10 =====================================\n")
                for i in range(10):
                    f.write(
                        f"{self._round(df_mix['min_return'].iloc[i]):8}, {df_mix['min_return'].index[i]:3}\n"
                    )

            f.write("순번, 인덱스, 구간 수익률, 최대 수익률, 최저 수익률 ===\n")
            count = 0
            for index, row in df_final.iterrows():
                count += 1
                f.write(
                    f"{count:4}, {index:6}, {self._round(row['final_return']):11}, {self._round(row['max_return']):11}, {self._round(row['min_return']):11}\n"
                )

    @staticmethod
    def make_config_json(
        title="",
        budget=50000,
        strategy_num=0,
        interval=0.000001,
        currency="BTC",
        from_dash_to="210804.000000-210811.000000",
        offset_min=120,
        filepath=None,
    ):
        """대량 시뮬레이션을 위한 설정 파일 생성"""
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
        if filepath is None:
            filepath = MassSimulator.CONFIG_FILE_OUTPUT

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

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(config, f)
        return filepath
