import unittest
from smtm import SimulationDataProvider
from smtm import SimulationOperator
from smtm import SimulationTrader
from smtm import StrategyBuyAndHold
from smtm import StrategySma0
from smtm import Analyzer
from smtm import LogManager
from .data import simulation_data
from unittest.mock import *
import requests
import threading
import time


class SimulationIntegrationTests(unittest.TestCase):
    def setUp(self):
        LogManager.set_stream_level(20)
        pass

    def tearDown(self):
        pass

    def test_ITG_run_simulation_with_bnh_strategy(self):
        trading_snapshot = simulation_data.get_data("bnh_snapshot")
        operator = SimulationOperator()
        strategy = StrategyBuyAndHold()
        end_date = "2020-04-30T07:30:00Z"
        count = 100
        budget = 100000
        interval = 0.1
        TIME_LIMIT = 15
        operator.initialize_simulation(
            requests,
            threading,
            SimulationDataProvider(),
            strategy,
            SimulationTrader(),
            Analyzer(),
            end=end_date,
            count=count,
            budget=budget,
        )

        operator.set_interval(interval)
        operator.start()
        start_time = time.time()
        while operator.state == "running":
            time.sleep(0.5)
            if time.time() - start_time > TIME_LIMIT:
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
            if time.time() - start_time > TIME_LIMIT:
                self.assertTrue(False, "Time out")
                break

        self.assertIsNotNone(report)
        self.assertEqual(report[0], 100000)
        self.assertEqual(report[1], 97718)
        self.assertEqual(report[2], -2.282)
        self.assertEqual(report[3]["KRW-BTC"], -2.059)

    def test_ITG_run_simulation_with_sma0_strategy(self):
        trading_snapshot = simulation_data.get_data("sma0_snapshot")
        operator = SimulationOperator()
        strategy = StrategySma0()
        end_date = "2020-04-30T07:30:00Z"
        count = 100
        budget = 100000
        interval = 0.1
        TIME_LIMIT = 15
        operator.initialize_simulation(
            requests,
            threading,
            SimulationDataProvider(),
            strategy,
            SimulationTrader(),
            Analyzer(),
            end=end_date,
            count=count,
            budget=budget,
        )

        operator.set_interval(interval)
        operator.start()
        start_time = time.time()
        while operator.state == "running":
            time.sleep(0.5)
            if time.time() - start_time > TIME_LIMIT:
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
            if time.time() - start_time > TIME_LIMIT:
                self.assertTrue(False, "Time out")
                break

        self.assertIsNotNone(report)
        self.assertEqual(report[0], 100000)
        self.assertEqual(report[1], 98357)
        self.assertEqual(report[2], -1.643)
        self.assertEqual(report[3]["KRW-BTC"], -2.059)

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
