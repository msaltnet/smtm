import unittest
from datetime import datetime
from datetime import timedelta
from smtm import MassSimulator, Config
from unittest.mock import *


class MassSimulatorUtilTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("builtins.print")
    @patch("psutil.Process")
    def test_memory_usage_should_print_correctly(self, mock_process, mock_print):
        dummy_memory_info_return = MagicMock()
        dummy_memory_info_return.rss = 777000000.123456789
        dummy_process_return = MagicMock()
        dummy_process_return.memory_info.return_value = dummy_memory_info_return
        mock_process.return_value = dummy_process_return
        MassSimulator.memory_usage()
        mock_print.assert_called_with("[MainProcess] memory usage:  741.00494 MB")


class MassSimulatorAnalyzeTests(unittest.TestCase):
    @patch("builtins.open", new_callable=mock_open)
    def test_analyze_result_should_call_file_write_correctly(self, mock_file):
        mass = MassSimulator()
        dummy_config = {
            "title": "BnH-2Hour",
            "budget": 50000,
            "strategy": "BNH",
            "interval": 1,
            "currency": "BTC",
            "description": "mass-simluation-unit-test",
            "period_list": [
                {"start": "2020-04-30T17:00:00", "end": "2020-04-30T19:00:00"},
                {"start": "2020-04-30T18:00:00", "end": "2020-04-30T20:00:00"},
            ],
        }
        dummy_result = [
            (0, 0, 1.12, 0, 0, 0, 2.99, 1.88),
            (0, 0, 2.25, 0, 0, 0, 1.99, -1.88),
            (0, 0, 2.01, 0, 0, 0, 4.99, 2.88),
        ]
        mass.draw_graph = MagicMock()
        mass.analyze_result(dummy_result, dummy_config)
        self.assertEqual(mock_file.call_args_list[1][0][0], "output/BnH-2Hour.result")
        self.assertEqual(mock_file.call_args_list[1][0][1], "w")
        self.assertEqual(mock_file.call_args_list[1][1]["encoding"], "utf-8")

        handle = mock_file()
        expected = [
            "Title: BnH-2Hour\n",
            "Description: mass-simluation-unit-test\n",
            "Strategy: Buy and Hold, Budget: 50000, Currency: BTC\n",
            "2020-04-30T17:00:00 ~ 2020-04-30T20:00:00 (3)\n",
            "수익률 평균:    1.793\n",
            "수익률 편차:    0.595\n",
            "수익률 최대:     2.25,   1\n",
            "수익률 최소:     1.12,   0\n",
            "순번, 인덱스, 구간 수익률, 최대 수익률, 최저 수익률 ===\n",
            "   1,      1,        2.25,       -1.88,        1.99\n",
            "   2,      2,        2.01,        2.88,        4.99\n",
            "   3,      0,        1.12,        1.88,        2.99\n",
        ]

        for idx, val in enumerate(expected):
            self.assertEqual(
                handle.write.call_args_list[idx][0][0],
                val,
            )
        self.assertEqual(mass.analyzed_result[0], 1.793)
        self.assertEqual(mass.analyzed_result[1], 0.595)
        self.assertEqual(mass.analyzed_result[2], 2.25)
        self.assertEqual(mass.analyzed_result[3], 1.12)
        mass.draw_graph.assert_called_with(
            [1.12, 2.25, 2.01], mean=1.793, filename="output/BnH-2Hour.jpg"
        )

    @patch("matplotlib.pyplot.bar")
    @patch("matplotlib.pyplot.plot")
    @patch("matplotlib.pyplot.savefig")
    def test_draw_graph_should_call_plt_correctly(self, mock_savefig, mock_plot, mock_bar):
        MassSimulator.draw_graph([1.12, 2.25, 2.01], mean=1.793, filename="mango.jpg")
        mock_bar.assert_called_once_with([0, 1, 2], [1.12, 2.25, 2.01])
        mock_plot.assert_called_once_with([1.793, 1.793, 1.793], "r")
        mock_savefig.assert_called_once_with("mango.jpg", dpi=300, pad_inches=0.25)


class MassSimulatorInitializeTests(unittest.TestCase):
    def setUp(self):
        self.interval = Config.candle_interval
        Config.candle_interval = 60

    def tearDown(self):
        Config.candle_interval = self.interval

    @patch("smtm.SimulationDataProvider.initialize_simulation")
    @patch("smtm.SimulationTrader.initialize_simulation")
    @patch("smtm.SimulationOperator.initialize")
    @patch("smtm.SimulationOperator.set_interval")
    def test_get_initialized_operator_should_initialize_correctly(
        self, mock_interval, mock_op_init, mock_tr_init, mock_dp_init
    ):
        budget = 50000
        strategy_code = "BNH"
        interval = 60
        currency = "BTC"
        start = "2020-04-30T17:00:00"
        end = "2020-04-30T18:00:00"
        tag = "mango-test"
        operator = MassSimulator.get_initialized_operator(
            budget, strategy_code, interval, currency, start, end, tag
        )
        mock_dp_init.assert_called_once_with(end=end, count=60)
        mock_tr_init.assert_called_once_with(end=end, count=60, budget=budget)
        mock_op_init.assert_called_once_with(ANY, ANY, ANY, ANY, budget=budget)
        mock_interval.assert_called_once_with(60)
        self.assertEqual(operator.tag, tag)


class MassSimulatorRunTests(unittest.TestCase):
    @patch("smtm.LogManager.set_stream_level")
    def test_run_should_call_run_simulation_correctly(self, mock_set_stream_level):
        mass = MassSimulator()
        dummy_config = {
            "title": "BnH-2Hour",
            "budget": 50000,
            "strategy": 0,
            "interval": 1,
            "currency": "BTC",
            "description": "mass-simluation-unit-test",
            "period_list": [
                {"start": "2020-04-30T17:00:00", "end": "2020-04-30T19:00:00"},
                {"start": "2020-04-30T18:00:00", "end": "2020-04-30T20:00:00"},
            ],
        }
        mass._load_config = MagicMock(return_value=dummy_config)
        mass.analyze_result = MagicMock()
        mass.print_state = MagicMock()
        mass._execute_simulation = MagicMock()
        mass.run("mass_config_file_name", 2)

        mass._load_config.assert_called_once_with("mass_config_file_name")
        self.assertEqual(
            mass._execute_simulation.call_args[0][0],
            [
                {
                    "title": "BnH-2Hour",
                    "budget": 50000,
                    "strategy": 0,
                    "interval": 1,
                    "currency": "BTC",
                    "partial_idx": 0,
                    "partial_period_list": [
                        {
                            "idx": 0,
                            "period": {
                                "start": "2020-04-30T17:00:00",
                                "end": "2020-04-30T19:00:00",
                            },
                        },
                    ],
                },
                {
                    "title": "BnH-2Hour",
                    "budget": 50000,
                    "strategy": 0,
                    "interval": 1,
                    "currency": "BTC",
                    "partial_idx": 1,
                    "partial_period_list": [
                        {
                            "idx": 1,
                            "period": {
                                "start": "2020-04-30T18:00:00",
                                "end": "2020-04-30T20:00:00",
                            },
                        },
                    ],
                },
            ],
        )
        self.assertEqual(mass._execute_simulation.call_args[0][1], 2)
        mass.analyze_result.assert_called_once_with(mass.result, dummy_config)
        mass.print_state.assert_called()

    def test_run_single_should_start_and_stop_operator(self):
        mock_op = MagicMock()
        MassSimulator.run_single(mock_op)
        mock_op.start.assert_called_once()
        mock_op.stop.assert_called_once()
        mock_op.get_score.assert_called_once()


class MassSimulatorTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("json.dump")
    @patch("builtins.open", new_callable=mock_open)
    def test_make_config_json_should_make_json_file_correctly(self, mock_file, mock_json):
        result = MassSimulator.make_config_json(
            title="get_money",
            budget=50000000000,
            strategy_code="SMA",
            interval=0.777,
            currency="USD",
            from_dash_to="210804.000000-210804.030000",
            offset_min=120,
        )
        self.assertEqual(result, "output/generated_config.json")
        config = mock_json.call_args[0][0]
        self.assertEqual(config["title"], "get_money")
        self.assertEqual(config["budget"], 50000000000)
        self.assertEqual(config["strategy"], "SMA")
        self.assertEqual(config["interval"], 0.777)
        self.assertEqual(config["currency"], "USD")
        self.assertEqual(len(config["period_list"]), 2)
        self.assertEqual(config["period_list"][0]["start"], "2021-08-04T00:00:00")
        self.assertEqual(config["period_list"][0]["end"], "2021-08-04T02:00:00")
        self.assertEqual(config["period_list"][1]["start"], "2021-08-04T02:00:00")
        self.assertEqual(config["period_list"][1]["end"], "2021-08-04T04:00:00")

    @patch("builtins.print")
    def test_print_state_print_correctly_when_is_start_true(self, mock_print):
        mass = MassSimulator()
        mass.config = {
            "title": "mass simulation test",
            "currency": "ETH",
            "description": "unit test config",
            "budget": 5000000,
            "strategy": "show me the money",
            "period_list": [{"start": "today", "end": "tomorrow"}],
        }
        mass.print_state(is_start=True)
        self.assertEqual(
            mock_print.call_args_list[1][0][0], "Title: mass simulation test, Currency: ETH"
        )
        self.assertEqual(mock_print.call_args_list[2][0][0], "Description: unit test config")
        self.assertEqual(
            mock_print.call_args_list[3][0][0], "Budget: 5000000, Strategy: show me the money"
        )
        self.assertEqual(mock_print.call_args_list[4][0][0], "today ~ tomorrow (1)")
        self.assertEqual(
            mock_print.call_args_list[6][0][0].find("+0          simulation start!"), 24
        )

    @patch("builtins.print")
    def test_print_state_print_correctly_when_is_end_true(self, mock_print):
        mass = MassSimulator()
        mass.config = {
            "title": "mass simulation test",
            "currency": "ETH",
            "description": "unit test config",
            "budget": 5000000,
            "strategy": "show me the money",
            "period_list": [{"start": "today", "end": "tomorrow"}],
        }
        mass.analyzed_result = (123.45, 456, 789, 10)
        mass.start = mass.last_print = datetime.now() - timedelta(seconds=4)
        mass.print_state(is_end=True)
        self.assertEqual(mock_print.call_args_list[0][0][0].find("simulation completed"), 36)
        self.assertEqual(mock_print.call_args_list[2][0][0], "수익률 평균:   123.45")
        self.assertEqual(mock_print.call_args_list[3][0][0], "수익률 편차:      456")
        self.assertEqual(mock_print.call_args_list[4][0][0], "수익률 최대:      789")
        self.assertEqual(mock_print.call_args_list[5][0][0], "수익률 최소:       10")

    @patch("builtins.print")
    def test_print_state_print_correctly(self, mock_print):
        mass = MassSimulator()
        mass.start = mass.last_print = datetime.now() - timedelta(seconds=4)
        mass.print_state()
        self.assertEqual(mock_print.call_args[0][0].find("simulation is running"), 36)

    def test__update_result_should_update_result_correctly(self):
        mass = MassSimulator()
        mass.result.append(0)
        mass._update_result([{"idx": 0, "result": "mango"}])
        self.assertEqual(mass.result[0], "mango")

    def test__execute_single_process_simulation_should_run_simulation(self):
        dummy_config = {
            "title": "BnH-2Hour",
            "budget": 50000,
            "strategy": 0,
            "interval": 1,
            "currency": "BTC",
            "description": "mass-simluation-unit-test",
            "partial_idx": 1,
            "partial_period_list": [
                {
                    "idx": 7,
                    "period": {"start": "2020-04-30T17:00:00", "end": "2020-04-30T19:00:00"},
                },
                {
                    "idx": 8,
                    "period": {"start": "2020-04-30T18:00:00", "end": "2020-04-30T20:00:00"},
                },
            ],
        }
        backup_run_single = MassSimulator.run_single
        backup_memory_usage = MassSimulator.memory_usage
        MassSimulator.run_single = MagicMock(return_value="mango_result")
        MassSimulator.memory_usage = MagicMock()
        MassSimulator.get_initialized_operator = MagicMock(return_value="dummy_operator")
        result = MassSimulator._execute_single_process_simulation(dummy_config)

        MassSimulator.memory_usage.assert_called_once()
        MassSimulator.run_single.assert_called_with("dummy_operator")
        self.assertEqual(result[0]["idx"], 7)
        self.assertEqual(result[0]["result"], "mango_result")
        self.assertEqual(result[1]["idx"], 8)
        self.assertEqual(result[1]["result"], "mango_result")
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[0][0][0], 50000)
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[0][0][1], 0)
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[0][0][2], 1)
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[0][0][3], "BTC")
        self.assertEqual(
            MassSimulator.get_initialized_operator.call_args_list[0][0][4], "2020-04-30T17:00:00"
        )
        self.assertEqual(
            MassSimulator.get_initialized_operator.call_args_list[0][0][5], "2020-04-30T19:00:00"
        )
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[1][0][0], 50000)
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[1][0][1], 0)
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[1][0][2], 1)
        self.assertEqual(MassSimulator.get_initialized_operator.call_args_list[1][0][3], "BTC")
        self.assertEqual(
            MassSimulator.get_initialized_operator.call_args_list[1][0][4], "2020-04-30T18:00:00"
        )
        self.assertEqual(
            MassSimulator.get_initialized_operator.call_args_list[1][0][5], "2020-04-30T20:00:00"
        )
        MassSimulator.run_single = backup_run_single
        MassSimulator.memory_usage = backup_memory_usage

    def test_make_chunk_should_make_chunk_list_from_original_list(self):
        a = [1, 2, 3, 4, 5, 6, 7]
        a_result = MassSimulator.make_chunk(a, 3)
        self.assertEqual(a_result[0], [1, 2, 3])
        self.assertEqual(a_result[1], [4, 5])
        self.assertEqual(a_result[2], [6, 7])

        a_result = MassSimulator.make_chunk(a, 4)
        self.assertEqual(a_result[0], [1, 2])
        self.assertEqual(a_result[1], [3, 4])
        self.assertEqual(a_result[2], [5, 6])
        self.assertEqual(a_result[3], [7])

        a_result = MassSimulator.make_chunk(a, 2)
        self.assertEqual(a_result[0], [1, 2, 3, 4])
        self.assertEqual(a_result[1], [5, 6, 7])

        b = ["a", "b", "c", "d", "e"]
        b_result = MassSimulator.make_chunk(b, 2)
        self.assertEqual(b_result[0], ["a", "b", "c"])
        self.assertEqual(b_result[1], ["d", "e"])

        b_result = MassSimulator.make_chunk(b, 4)
        self.assertEqual(b_result[0], ["a", "b"])
        self.assertEqual(b_result[1], ["c"])
        self.assertEqual(b_result[2], ["d"])
        self.assertEqual(b_result[3], ["e"])
