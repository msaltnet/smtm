import time
import unittest
from smtm import (
    SimulationDataProvider,
    SimulationOperator,
    SimulationTrader,
    StrategyFactory,
    Analyzer,
    LogManager,
    Config,
)
from .data import simulation_data
from unittest.mock import *


class SimulationOperatorIntegrationTests(unittest.TestCase):
    def setUp(self):
        LogManager.set_stream_level(20)
        self.interval = Config.candle_interval
        Config.candle_interval = 60

    def tearDown(self):
        Config.candle_interval = self.interval

    def test_ITG_run_simulation_with_bnh_strategy(self):
        trading_snapshot = simulation_data.get_data("bnh_snapshot")
        operator = SimulationOperator()
        strategy = StrategyFactory.create("BNH")
        strategy.is_simulation = True
        count = 100
        budget = 100000
        interval = 0.0001
        time_limit = 15
        end_str = "2020-04-30T16:30:00"

        data_provider = SimulationDataProvider(interval=Config.candle_interval)
        data_provider.initialize_simulation(end=end_str, count=count)
        trader = SimulationTrader()
        trader.initialize_simulation(end=end_str, count=count, budget=budget)
        analyzer = Analyzer()
        analyzer.is_simulation = True

        operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=budget,
        )

        operator.set_interval(interval)
        operator.start()
        start_time = time.time()
        while operator.state == "running":
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        trading_results = operator.get_trading_results()
        self.check_equal_results_list(trading_results, trading_snapshot)

        waiting = True
        start_time = time.time()
        report = None

        def callback(return_report):
            nonlocal report
            nonlocal waiting
            report = return_report
            waiting = False
            self.assertFalse(waiting)

        operator.get_score(callback)

        while waiting:
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        self.assertIsNotNone(report)
        self.assertEqual(report[0], 100000)
        self.assertEqual(report[1], 97220)
        self.assertEqual(report[2], -2.78)
        self.assertEqual(report[3]["KRW-BTC"], -2.693)

    def check_equal_results_list(self, a, b):
        self.assertEqual(len(a), len(b))
        for i in range(len(a)):
            self.assertEqual(a[i]["request"]["type"], b[i]["request"]["type"])
            self.assertEqual(a[i]["request"]["price"], b[i]["request"]["price"])
            self.assertEqual(a[i]["request"]["amount"], b[i]["request"]["amount"])
            self.assertEqual(a[i]["request"]["date_time"], b[i]["request"]["date_time"])

            self.assertEqual(a[i]["type"], b[i]["type"])
            self.assertEqual(a[i]["price"], b[i]["price"])
            self.assertEqual(a[i]["amount"], b[i]["amount"])
            self.assertEqual(a[i]["msg"], b[i]["msg"])
            self.assertEqual(a[i]["balance"], b[i]["balance"])
            self.assertEqual(a[i]["date_time"], b[i]["date_time"])
            self.assertEqual(a[i]["kind"], b[i]["kind"])

    def test_ITG_run_simulation_with_sma_strategy(self):
        operator = SimulationOperator()
        strategy = StrategyFactory.create("SMA")
        strategy.is_simulation = True
        count = 100
        budget = 100000
        interval = 0.0001
        time_limit = 30
        end_str = "2022-04-30T16:30:00"

        data_provider = SimulationDataProvider()
        data_provider.initialize_simulation(end=end_str, count=count)
        trader = SimulationTrader()
        trader.initialize_simulation(end=end_str, count=count, budget=budget)
        analyzer = Analyzer()
        analyzer.is_simulation = True

        operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=budget,
        )

        operator.set_interval(interval)
        operator.start()
        start_time = time.time()
        while operator.state == "running":
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        waiting = True
        start_time = time.time()
        report = None

        def callback(return_report):
            nonlocal report
            nonlocal waiting
            report = return_report
            waiting = False
            self.assertFalse(waiting)

        operator.get_score(callback)

        while waiting:
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        self.assertIsNotNone(report)
        self.assertEqual(report[0], 100000)

    def test_ITG_run_simulation_with_rsi_strategy(self):
        operator = SimulationOperator()
        strategy = StrategyFactory.create("RSI")
        strategy.is_simulation = True
        count = 100
        budget = 100000
        interval = 0.0001
        time_limit = 30
        end_str = "2022-04-30T16:30:00"

        data_provider = SimulationDataProvider()
        data_provider.initialize_simulation(end=end_str, count=count)
        trader = SimulationTrader()
        trader.initialize_simulation(end=end_str, count=count, budget=budget)
        analyzer = Analyzer()
        analyzer.is_simulation = True

        operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=budget,
        )

        operator.set_interval(interval)
        operator.start()
        start_time = time.time()
        while operator.state == "running":
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        waiting = True
        start_time = time.time()
        report = None

        def callback(return_report):
            nonlocal report
            nonlocal waiting
            report = return_report
            waiting = False
            self.assertFalse(waiting)

        operator.get_score(callback)

        while waiting:
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        self.assertIsNotNone(report)
        self.assertEqual(report[0], 100000)

    def test_ITG_run_simulation_with_sml_strategy(self):
        operator = SimulationOperator()
        strategy = StrategyFactory.create("SML")
        strategy.is_simulation = True
        count = 100
        budget = 100000
        interval = 0.0001
        time_limit = 30
        end_str = "2022-07-29T04:30:00"

        data_provider = SimulationDataProvider()
        data_provider.initialize_simulation(end=end_str, count=count)
        trader = SimulationTrader()
        trader.initialize_simulation(end=end_str, count=count, budget=budget)
        analyzer = Analyzer()
        analyzer.is_simulation = True

        operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=budget,
        )

        operator.set_interval(interval)
        operator.start()
        start_time = time.time()
        while operator.state == "running":
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        waiting = True
        start_time = time.time()
        report = None

        def callback(return_report):
            nonlocal report
            nonlocal waiting
            report = return_report
            waiting = False
            self.assertFalse(waiting)

        operator.get_score(callback)

        while waiting:
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        self.assertIsNotNone(report)
        self.assertEqual(report[0], 100000)


class SimulationOperator3mIntervalIntegrationTests(unittest.TestCase):
    def setUp(self):
        LogManager.set_stream_level(20)
        self.interval = Config.candle_interval
        Config.candle_interval = 180

    def tearDown(self):
        Config.candle_interval = self.interval

    def test_ITG_run_simulation_with_bnh_strategy(self):
        trading_snapshot = simulation_data.get_data("bnh_3m_snapshot")
        operator = SimulationOperator()
        strategy = StrategyFactory.create("BNH")
        strategy.is_simulation = True
        count = 100
        budget = 100000
        interval = 0.0001
        time_limit = 15
        end_str = "2020-04-30T16:30:00"

        data_provider = SimulationDataProvider(interval=Config.candle_interval)
        data_provider.initialize_simulation(end=end_str, count=count)
        trader = SimulationTrader()
        trader.initialize_simulation(end=end_str, count=count, budget=budget)
        analyzer = Analyzer()
        analyzer.is_simulation = True

        operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=budget,
        )

        operator.set_interval(interval)
        operator.start()
        start_time = time.time()
        while operator.state == "running":
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        trading_results = operator.get_trading_results()

        self.check_equal_results_list(trading_results, trading_snapshot)
        waiting = True
        start_time = time.time()
        report = None

        def callback(return_report):
            nonlocal report
            nonlocal waiting
            report = return_report
            waiting = False
            self.assertFalse(waiting)

        operator.get_score(callback)

        while waiting:
            time.sleep(0.5)
            if time.time() - start_time > time_limit:
                self.assertTrue(False, "Time out")
                break

        self.assertIsNotNone(report)
        self.assertEqual(report[0], 100000)
        self.assertEqual(report[1], 97066)
        self.assertEqual(report[2], -2.934)
        self.assertEqual(report[3]["KRW-BTC"], -2.693)

    def check_equal_results_list(self, a, b):
        self.assertEqual(len(a), len(b))
        for i in range(len(a)):
            self.assertEqual(a[i]["request"]["type"], b[i]["request"]["type"])
            self.assertEqual(a[i]["request"]["price"], b[i]["request"]["price"])
            self.assertEqual(a[i]["request"]["amount"], b[i]["request"]["amount"])
            self.assertEqual(a[i]["request"]["date_time"], b[i]["request"]["date_time"])

            self.assertEqual(a[i]["type"], b[i]["type"])
            self.assertEqual(a[i]["price"], b[i]["price"])
            self.assertEqual(a[i]["amount"], b[i]["amount"])
            self.assertEqual(a[i]["msg"], b[i]["msg"])
            self.assertEqual(a[i]["balance"], b[i]["balance"])
            self.assertEqual(a[i]["date_time"], b[i]["date_time"])
            self.assertEqual(a[i]["kind"], b[i]["kind"])
