import unittest
from smtm import SimulationDataProvider
from smtm import SimulationOperator
from smtm import SimulationTrader
from smtm import StrategyBuyAndHold
from smtm import Analyzer
from unittest.mock import *
import requests
import threading
import time


class SimulationIntegrationTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_ITG_run_simulation_with_bnh_strategy(self):
        trading_snapshot = [
            {
                "request": {
                    "id": "1617434671.201",
                    "type": "buy",
                    "price": 11288000.0,
                    "amount": 0.000885896527285613,
                    "date_time": "2020-04-30T14:50:00",
                },
                "type": "buy",
                "price": 11288000.0,
                "amount": 0.000885896527285613,
                "msg": "success",
                "balance": 89995,
                "date_time": "2020-04-30T14:51:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434671.324",
                    "type": "buy",
                    "price": 11304000.0,
                    "amount": 0.0008846426043878273,
                    "date_time": "2020-04-30T14:51:00",
                },
                "type": "buy",
                "price": 11304000.0,
                "amount": 0.0008846426043878273,
                "msg": "success",
                "balance": 79990,
                "date_time": "2020-04-30T14:52:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434671.45",
                    "type": "buy",
                    "price": 11292000.0,
                    "amount": 0.000885582713425434,
                    "date_time": "2020-04-30T14:52:00",
                },
                "type": "buy",
                "price": 11292000.0,
                "amount": 0.000885582713425434,
                "msg": "success",
                "balance": 69985,
                "date_time": "2020-04-30T14:53:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434671.578",
                    "type": "buy",
                    "price": 11313000.0,
                    "amount": 0.0008839388314328649,
                    "date_time": "2020-04-30T14:53:00",
                },
                "type": "buy",
                "price": 11313000.0,
                "amount": 0.0008839388314328649,
                "msg": "success",
                "balance": 59980,
                "date_time": "2020-04-30T14:54:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434671.703",
                    "type": "buy",
                    "price": 11330000.0,
                    "amount": 0.00088261253309797,
                    "date_time": "2020-04-30T14:54:00",
                },
                "type": "buy",
                "price": 11330000.0,
                "amount": 0.00088261253309797,
                "msg": "success",
                "balance": 49975,
                "date_time": "2020-04-30T14:55:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434671.831",
                    "type": "buy",
                    "price": 11310000.0,
                    "amount": 0.0008841732979664014,
                    "date_time": "2020-04-30T14:55:00",
                },
                "type": "buy",
                "price": 11310000.0,
                "amount": 0.0008841732979664014,
                "msg": "success",
                "balance": 39970,
                "date_time": "2020-04-30T14:56:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434671.955",
                    "type": "buy",
                    "price": 11351000.0,
                    "amount": 0.0008809796493700995,
                    "date_time": "2020-04-30T14:56:00",
                },
                "type": "buy",
                "price": 11351000.0,
                "amount": 0.0008809796493700995,
                "msg": "success",
                "balance": 29965,
                "date_time": "2020-04-30T14:57:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434672.081",
                    "type": "buy",
                    "price": 11324000.0,
                    "amount": 0.0008830801836806782,
                    "date_time": "2020-04-30T14:57:00",
                },
                "type": "buy",
                "price": 11324000.0,
                "amount": 0.0008830801836806782,
                "msg": "success",
                "balance": 19960,
                "date_time": "2020-04-30T14:58:00",
                "kind": 2,
            },
            {
                "request": {
                    "id": "1617434672.207",
                    "type": "buy",
                    "price": 11335000.0,
                    "amount": 0.000882223202470225,
                    "date_time": "2020-04-30T14:58:00",
                },
                "type": "buy",
                "price": 11335000.0,
                "amount": 0.000882223202470225,
                "msg": "success",
                "balance": 9955,
                "date_time": "2020-04-30T14:59:00",
                "kind": 2,
            },
        ]

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
