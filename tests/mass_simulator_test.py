import unittest
from smtm import MassSimulator
from unittest.mock import *


class MassSimulatorTests(unittest.TestCase):
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

    @patch("smtm.LogManager.set_stream_level")
    def test_run_should_call_run_single_correctly(self, mock_set_stream_level):
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
        mass.run_single = MagicMock(side_effect=["mango", "orange"])
        mass.run("mass_config_file_name")

        mock_set_stream_level.assert_called_once_with(30)
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
        self.assertEqual(mass.result[0], "mango")
        self.assertEqual(mass.result[1], "orange")
        self.assertEqual(len(mass.result), 2)

    def test_run_single_should_start_and_stop_operator(self):
        mock_op = MagicMock()
        mock_op.stop.return_value = "mango_result"
        result = MassSimulator.run_single(mock_op)
        mock_op.start.assert_called_once()
        mock_op.stop.assert_called_once()
        self.assertEqual(result, "mango_result")

    @patch("json.dump")
    @patch("builtins.open", new_callable=mock_open)
    def test_make_config_json_should_make_json_file_correctly(self, mock_file, mock_json):
        result = MassSimulator.make_config_json(
            title="get_money",
            budget=50000000000,
            strategy_num=7,
            interval=0.777,
            currency="USD",
            from_dash_to="210804.000000-210804.030000",
            offset_min=120,
        )
        self.assertEqual(result, "output/generated_config.json")
        config = mock_json.call_args[0][0]
        self.assertEqual(config["title"], "get_money")
        self.assertEqual(config["budget"], 50000000000)
        self.assertEqual(config["strategy"], 7)
        self.assertEqual(config["interval"], 0.777)
        self.assertEqual(config["currency"], "USD")
        self.assertEqual(len(config["period_list"]), 2)
        self.assertEqual(config["period_list"][0]["start"], "2021-08-04T00:00:00")
        self.assertEqual(config["period_list"][0]["end"], "2021-08-04T02:00:00")
        self.assertEqual(config["period_list"][1]["start"], "2021-08-04T02:00:00")
        self.assertEqual(config["period_list"][1]["end"], "2021-08-04T04:00:00")
