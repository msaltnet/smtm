"""대량시뮬레이션을 위핸 MassSimulator 클래스

SimulationOperator과 설정 파일을 사용해서 대량 시뮬레이션을 수행하는 모듈
"""
import copy
import os
import json
import time
import sys
from multiprocessing import Pool, TimeoutError, current_process
from datetime import datetime
from datetime import timedelta
import psutil
import pandas as pd
import matplotlib.pyplot as plt
from . import (
    LogManager,
    DateConverter,
    SimulationDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    StrategyRsi,
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
        """
        analyzed_result: 수익률 분석 결과 (평균, 표준편차, 최대, 최소)
        """
        self.logger = LogManager.get_logger("MassSimulator")
        self.result = []
        self.start = 0
        self.last_print = 0
        self.config = {}
        self.analyzed_result = None
        LogManager.change_log_file("mass-simulation.log")

        if os.path.isdir("output") is False:
            os.mkdir("output")

    @staticmethod
    def memory_usage():
        """현재 프로세스의 이름과 메모리 사용양을 화면에 출력"""
        # current process RAM usage
        process = psutil.Process()
        rss = process.memory_info().rss / 2 ** 20  # Bytes to MB
        print(f"[{current_process().name}] memory usage: {rss: 10.5f} MB")
        # print(f"[{current_process().name}] memory usage: {p.memory_info().rss} MB")

    @staticmethod
    def _load_config(config_file):
        with open(config_file, encoding="utf-8") as json_file:
            json_data = json.load(json_file)
        return json_data

    def print_state(self, is_start=False, is_end=False):
        """현재 시뮬레이터의 상태를 화면에 표시"""
        iso_format = "%Y-%m-%dT%H:%M:%S"
        now = datetime.now()
        now_string = now.strftime(iso_format)
        if is_start:
            print("Mass Simulation ========================================")
            print(f"Title: {self.config['title']}, Currency: {self.config['currency']}")
            print(f"Description: {self.config['description']}")
            print(f"Budget: {self.config['budget']}, Strategy: {self.config['strategy']}")
            print(
                f"{self.config['period_list'][0]['start']} ~ {self.config['period_list'][-1]['end']} ({len(self.config['period_list'])})"
            )
            print("========================================================")
            self.start = self.last_print = now
            print(f"{now_string}     +0          simulation start!")
            return

        if is_end:
            total_diff = now - self.start
            print(f"{now_string}     +{total_diff.total_seconds():<10} simulation completed")
            print("Result Summary =========================================")
            print(f"수익률 평균: {self.analyzed_result[0]:8}")
            print(f"수익률 편차: {self.analyzed_result[1]:8}")
            print(f"수익률 최대: {self.analyzed_result[2]:8}")
            print(f"수익률 최소: {self.analyzed_result[3]:8}")
            print("========================================================")
            return

        delta = now - self.last_print
        diff = delta.total_seconds()
        if diff > self.MIN_PRINT_STATE_SEC:
            self.last_print = now
            total_diff = now - self.start
            print(f"{now_string}     +{total_diff.total_seconds():<10} simulation is running")

    @staticmethod
    def run_single(operator):
        """시뮬레이션 1회 실행"""
        operator.start()
        while operator.state == "running":
            time.sleep(0.1)

        last_report = (None, None, None, None)

        def get_score_callback(report):
            nonlocal last_report
            last_report = report

        operator.get_score(get_score_callback)
        operator.stop()
        return last_report

    @staticmethod
    def get_initialized_operator(budget, strategy_num, interval, currency, start, end, tag):
        """시뮬레이션 오퍼레이션 생성 후 주어진 설정 값으로 초기화 하여 반환"""
        dt = DateConverter.to_end_min(start_iso=start, end_iso=end)
        end = dt[0][1]
        count = dt[0][2]

        data_provider = SimulationDataProvider(currency=currency)
        data_provider.initialize_simulation(end=end, count=count)

        strategy_number = int(strategy_num)
        if strategy_number == 0:
            strategy = StrategyBuyAndHold()
        elif strategy_number == 1:
            strategy = StrategySma0()
        elif strategy_number == 2:
            strategy = StrategyRsi()
        else:
            raise UserWarning(f"Invalid Strategy! {strategy_number}")

        strategy.is_simulation = True

        trader = SimulationTrader(currency=currency)
        trader.initialize_simulation(end=end, count=count, budget=budget)

        analyzer = Analyzer()
        analyzer.is_simulation = True

        operator = SimulationOperator(periodic_record_enable=False)
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

    def run(self, config_file, process=-1):
        """설정 파일의 내용으로 기간을 변경하며 시뮬레이션 진행"""
        self.config = self._load_config(config_file)
        process_num = process
        if process_num < 1:
            process_num = os.cpu_count()

        if process_num > len(self.config["period_list"]):
            process_num = len(self.config["period_list"])

        # 시뮬레이션 준비
        config_list = []
        period_object_list = []
        for i in range(len(self.config["period_list"])):
            period_object_list.append({"idx": i, "period": self.config["period_list"][i]})
        separated_periods = self.make_chunk(period_object_list, process_num)
        for i in range(process_num):
            config_list.append(
                {
                    "title": self.config["title"],
                    "budget": self.config["budget"],
                    "strategy": self.config["strategy"],
                    "interval": self.config["interval"],
                    "currency": self.config["currency"],
                    "partial_idx": i,
                    "partial_period_list": separated_periods[i],
                }
            )

        # 시뮬레이션 수행
        self.result = [None for x in range(len(self.config["period_list"]))]
        self.print_state(is_start=True)
        self._execute_simulation(config_list, process_num)

        # 결과 분석
        self.analyze_result(self.result, self.config)
        self.print_state(is_end=True)

    def _execute_simulation(self, config_list, process_num):
        is_running = True
        result_list = []
        self.memory_usage()
        with Pool(processes=process_num) as pool:
            try:
                async_result = pool.map_async(
                    MassSimulator._execute_single_process_simulation, config_list
                )
                while is_running:
                    try:
                        result_list = async_result.get(timeout=0.5)
                        is_running = False
                    except TimeoutError:
                        self.print_state()

                for result in result_list:
                    self._update_result(result)
            except KeyboardInterrupt:
                print("Terminating......")
                sys.exit(0)

    def _update_result(self, partial_result):
        for result in partial_result:
            idx = result["idx"]
            self.result[idx] = result["result"]

    @staticmethod
    def _execute_single_process_simulation(config):
        LogManager.set_stream_level(30)
        LogManager.change_log_file(f"mass-simulation-{config['partial_idx']}.log")
        period_list = config["partial_period_list"]
        result_list = []
        MassSimulator.memory_usage()
        print(f"partial simulation start @{current_process().name}")
        for period in period_list:
            tag = f"MASS-{config['title']}-{period['idx']}"
            operator = MassSimulator.get_initialized_operator(
                config["budget"],
                config["strategy"],
                config["interval"],
                config["currency"],
                period["period"]["start"],
                period["period"]["end"],
                tag,
            )
            try:
                report = MassSimulator.run_single(operator)
                result_list.append({"idx": period["idx"], "result": report})
                print(f"     #{period['idx']} return: {report[2]}")
            except KeyboardInterrupt:
                print(f"Terminating......@{current_process().name}")
                operator.stop()

        return result_list

    @staticmethod
    def _round(num):
        return round(num, 3)

    def analyze_result(self, result_list, config):
        """수익률 비교 결과를 파일로 저장"""
        title = config["title"]
        period_list = config["period_list"]

        strategy_number = int(config["strategy"])
        if strategy_number == 0:
            strategy_name = StrategyBuyAndHold.NAME
        elif strategy_number == 1:
            strategy_name = StrategySma0.NAME
        elif strategy_number == 2:
            strategy_name = StrategyRsi.NAME
        else:
            raise UserWarning(f"Invalid Strategy! {strategy_number}")

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
        self.analyzed_result = (
            self._round(dataframe["final_return"].mean()),
            self._round(dataframe["final_return"].std()),
            self._round(df_final["final_return"].iloc[0]),
            self._round(df_final["final_return"].iloc[-1]),
        )

        with open(f"{self.RESULT_FILE_OUTPUT}{title}.result", "w", encoding="utf-8") as result_file:
            # 기본 정보
            result_file.write(f"Title: {title}\n")
            result_file.write(f"Description: {config['description']}\n")
            result_file.write(
                f"Strategy: {strategy_name}, Budget: {config['budget']}, Currency: {config['currency']}\n"
            )
            result_file.write(
                f"{period_list[0]['start']} ~ {period_list[-1]['end']} ({len(final_return_list)})\n"
            )

            result_file.write(f"수익률 평균: {self.analyzed_result[0]:8}\n")
            result_file.write(f"수익률 편차: {self.analyzed_result[1]:8}\n")
            result_file.write(
                f"수익률 최대: {self.analyzed_result[2]:8}, {df_final['final_return'].index[0]:3}\n"
            )
            result_file.write(
                f"수익률 최소: {self.analyzed_result[3]:8}, {df_final['final_return'].index[-1]:3}\n"
            )

            if len(final_return_list) > 10:
                result_file.write("수익률 TOP 10 ===============================================\n")
                for i in range(10):
                    result_file.write(
                        f"{self._round(df_final['final_return'].iloc[i]):8}, {df_final['final_return'].index[i]:3}\n"
                    )

                result_file.write("수익률 WORST 10 ===============================================\n")
                for i in range(10):
                    idx = -1 * (i + 1)
                    result_file.write(
                        f"{self._round(df_final['final_return'].iloc[idx]):8}, {df_final['final_return'].index[idx]:3}\n"
                    )

                result_file.write("순간 최대 수익률 BEST 10 =====================================\n")
                for i in range(10):
                    result_file.write(
                        f"{self._round(df_max['max_return'].iloc[i]):8}, {df_max['max_return'].index[i]:3}\n"
                    )

                result_file.write("순간 최저 수익률 WORST 10 =====================================\n")
                for i in range(10):
                    result_file.write(
                        f"{self._round(df_mix['min_return'].iloc[i]):8}, {df_mix['min_return'].index[i]:3}\n"
                    )

            result_file.write("순번, 인덱스, 구간 수익률, 최대 수익률, 최저 수익률 ===\n")
            count = 0
            for index, row in df_final.iterrows():
                count += 1
                result_file.write(
                    f"{count:4}, {index:6}, {self._round(row['final_return']):11}, {self._round(row['max_return']):11}, {self._round(row['min_return']):11}\n"
                )

            self.draw_graph(
                final_return_list,
                mean=self._round(dataframe["final_return"].mean()),
                filename=f"{self.RESULT_FILE_OUTPUT}{title}.jpg",
            )

    @staticmethod
    def draw_graph(return_list, mean=0, filename="mass-simulation-result.jpg"):
        """수익률 막대 그래프를 파일로 저장"""
        idx = list(range(len(return_list)))
        mean = [mean for i in range(len(return_list))]
        plt.bar(idx, return_list)
        plt.plot(mean, "r")
        plt.savefig(filename, dpi=300, pad_inches=0.25)

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
        """대량 시뮬레이션을 위한 설정 파일 생성
        config: {
            "title": 타이틀
            "description": 시뮬레이션 설명
            "budget": 예산
            "strategy": 사용할 전략 번호
            "interval": 거래 간의 시간 간격
            "currency": 암호 화폐 종류
            "period_list": [
                {
                    "start": 시뮬레이션 기간 시작
                    "end": 시뮬레이션 기간 종료
                }
            ],
        }
        """
        iso_format = "%Y-%m-%dT%H:%M:%S"
        config = {
            "title": title,
            "description": "write descriptionf here",
            "budget": budget,
            "strategy": int(strategy_num),
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

        with open(filepath, "w", encoding="utf-8") as dump_file:
            json.dump(config, dump_file)
        return filepath

    @staticmethod
    def make_chunk(original, num):
        """전달 받은 리스트를 num개로 분할하여 반환"""
        if len(original) < num or num == 1:
            return [copy.deepcopy(original)]

        div = divmod(len(original), num)
        result = []
        last = 0

        for i in range(num):
            if i < div[1]:
                count = div[0] + 1
            else:
                count = div[0]

            result.append(original[last : last + count])
            last += count

        return result
