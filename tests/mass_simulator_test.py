import unittest
from smtm import MassSimulator
from unittest.mock import *


class DataRepositoryTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("smtm.SimulationDataProvider.initialize_simulation")
    @patch("smtm.SimulationTrader.initialize_simulation")
    @patch("smtm.SimulationOperator.initialize")
    @patch("smtm.SimulationOperator.set_interval")
    def test_get_initialized_operator_should_initialize_correctly(
        self, mock_interval, mock_op_init, mock_tr_init, mock_dp_init
    ):
        budget = 50000
        strategy_num = 1
        interval = 60
        currency = "BTC"
        start = "2020-04-30T17:00:00"
        end = "2020-04-30T18:00:00"
        tag = "mango-test"
        operator = MassSimulator.get_initialized_operator(
            budget, strategy_num, interval, currency, start, end, tag
        )
        mock_dp_init.assert_called_once_with(end=end, count=60)
        mock_tr_init.assert_called_once_with(end=end, count=60, budget=budget)
        mock_op_init.assert_called_once_with(ANY, ANY, ANY, ANY, budget=budget)
        mock_interval.assert_called_once_with(60)
        self.assertEqual(operator.tag, tag)

    def test_run_should_call_run_single_correctly(self):
        mass = MassSimulator()
        mass._load_config = MagicMock(
            return_value={
                "title": "BnH-2Hour",
                "budget": 50000,
                "strategy": 0,
                "interval": 1,
                "currency": "BTC",
                "period_list": [
                    {"start": "2020-04-30T17:00:00", "end": "2020-04-30T19:00:00"},
                    {"start": "2020-04-30T18:00:00", "end": "2020-04-30T20:00:00"},
                ],
            }
        )
        mass.get_initialized_operator = MagicMock(side_effect=["mango_operator", "orange_operator"])
        mass.run_single = MagicMock()
        mass.run("mass_config_file_name")

        mass._load_config.assert_called_once_with("mass_config_file_name")
        self.assertEqual(mass.run_single.call_args_list[0][0][0], "mango_operator")
        self.assertEqual(mass.run_single.call_args_list[1][0][0], "orange_operator")
        self.assertEqual(mass.get_initialized_operator.call_args_list[0][0][0], 50000)
        self.assertEqual(mass.get_initialized_operator.call_args_list[0][0][1], 0)
        self.assertEqual(mass.get_initialized_operator.call_args_list[0][0][2], 1)
        self.assertEqual(mass.get_initialized_operator.call_args_list[0][0][3], "BTC")
        self.assertEqual(
            mass.get_initialized_operator.call_args_list[0][0][4], "2020-04-30T17:00:00"
        )
        self.assertEqual(
            mass.get_initialized_operator.call_args_list[0][0][5], "2020-04-30T19:00:00"
        )
        self.assertEqual(mass.get_initialized_operator.call_args_list[0][0][6], "MASS-BnH-2Hour-0")

        self.assertEqual(mass.get_initialized_operator.call_args_list[1][0][0], 50000)
        self.assertEqual(mass.get_initialized_operator.call_args_list[1][0][1], 0)
        self.assertEqual(mass.get_initialized_operator.call_args_list[1][0][2], 1)
        self.assertEqual(mass.get_initialized_operator.call_args_list[1][0][3], "BTC")
        self.assertEqual(
            mass.get_initialized_operator.call_args_list[1][0][4], "2020-04-30T18:00:00"
        )
        self.assertEqual(
            mass.get_initialized_operator.call_args_list[1][0][5], "2020-04-30T20:00:00"
        )
        self.assertEqual(mass.get_initialized_operator.call_args_list[1][0][6], "MASS-BnH-2Hour-1")

    def test_run_single_should_start_and_stop_operator(self):
        mock_op = MagicMock()
        MassSimulator.run_single(mock_op)
        mock_op.start.assert_called_once()
        mock_op.stop.assert_called_once()
