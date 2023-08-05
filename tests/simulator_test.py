import unittest
from smtm import Simulator, Config
from unittest.mock import *


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.interval = Config.candle_interval
        Config.candle_interval = 60

    def tearDown(self):
        Config.candle_interval = self.interval

    @patch("signal.signal")
    @patch("builtins.input", side_effect=EOFError)
    def test_main_call_signal_to_listen_sigterm(self, mock_input, mock_signal):
        simulator = Simulator()
        simulator.main()
        mock_signal.assert_called_with(ANY, simulator.stop)

    def test_run_single_call_start_and_terminate(self):
        simulator = Simulator()
        simulator.start = MagicMock()
        simulator.initialize = MagicMock()
        simulator.terminate = MagicMock()
        simulator.operator = MagicMock()
        simulator.operator.state = "terminated"
        simulator.run_single()
        simulator.start.assert_called()
        simulator.initialize.assert_called()
        simulator.terminate.assert_called()

    @patch("builtins.print")
    def test_print_help_print_guide_correctly(self, mock_print):
        simulator = Simulator()
        simulator.command_list = [{"guide": "orange"}]
        simulator.print_help()
        self.assertEqual(mock_print.call_args_list[0][0][0], "command list =================")
        self.assertEqual(mock_print.call_args_list[1][0][0], "orange")

    @patch("builtins.print")
    def test_on_command_just_print_error_message_when_invalid_command(self, mock_print):
        simulator = Simulator()
        simulator.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": ["help", "h"],
                "need_value": False,
            },
        ]
        simulator.execute_command = MagicMock()
        simulator.on_command("hell")
        simulator.execute_command.assert_not_called()
        mock_print.assert_called_once_with("invalid command")

    def test_on_command_call_action_correclty(self):
        simulator = Simulator()
        simulator.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": ["help", "h"],
                "action": MagicMock(),
            },
            {
                "guide": "c, count         set simulation count",
                "cmd": ["count", "c"],
                "action": MagicMock(),
            },
            {
                "guide": "i, interval         set simulation interval",
                "cmd": ["interval", "i"],
                "action": MagicMock(),
            },
        ]
        simulator.on_command("h")
        simulator.on_command("coun")
        simulator.command_list[0]["action"].assert_called_once()
        simulator.command_list[1]["action"].assert_not_called()
        simulator.on_command("iNTERval")
        simulator.command_list[2]["action"].assert_called_once()

    @patch("builtins.input", side_effect=["", "", "5"])
    def test_initialize_with_command_print_guide_and_call_action_correctly(self, mock_input):
        simulator = Simulator()
        simulator.config_list = [
            {
                "guide": "년월일.시분초 형식으로 시작 시점 입력. 예. 201220.162300",
                "value": "time_value",
                "action": MagicMock(),
            },
            {
                "guide": "년월일.시분초 형식으로 종료 시점 입력. 예. 201220.162300",
                "value": "end_value",
                "action": MagicMock(),
            },
            {
                "guide": "거래 간격 입력. 예. 1",
                "value": "interval_value",
                "action": MagicMock(),
            },
        ]
        simulator.initialize_with_command()
        simulator.config_list[0]["action"].assert_called_with("time_value")
        simulator.config_list[1]["action"].assert_called_with("end_value")
        simulator.config_list[2]["action"].assert_called_with("5")

    @patch("smtm.SimulationTrader.initialize_simulation")
    @patch("smtm.SimulationDataProvider.initialize_simulation")
    @patch("smtm.SimulationOperator.set_interval")
    @patch("smtm.SimulationOperator.initialize")
    def test_initialize_call_initialize(self, mock_initialize, mock_set_interval, mock_dp, mock_tr):
        simulator = Simulator(budget=7000, from_dash_to="201220.170000-201220.180000")
        simulator._make_tag = MagicMock(return_value="orange")
        simulator.interval = 0.1
        simulator.initialize()
        self.assertEqual(simulator.need_init, False)
        mock_initialize.assert_called_once()
        mock_set_interval.assert_called_once_with(0.1)
        mock_dp.assert_called_once_with(end="2020-12-20T18:00:00", count=60)
        mock_tr.assert_called_once_with(end="2020-12-20T18:00:00", count=60, budget=7000)
        simulator._make_tag.assert_called_once()
        self.assertEqual(simulator.operator.tag, "orange")

    def test_start_call_operator_start(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.need_init = True
        simulator.start()
        simulator.operator.start.assert_not_called()

        simulator.need_init = False
        simulator.start()
        simulator.operator.start.assert_called()

    def test_stop_call_operator_stop(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.stop(None, None)
        simulator.operator.stop.assert_called()
        self.assertEqual(simulator.need_init, True)

    def test_terminate_call_operator_stop(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.terminate()
        simulator.operator.stop.assert_called()

    def test__set_start_str_should_set_value(self):
        simulator = Simulator()
        simulator._set_start_str("mango")
        self.assertEqual(simulator.start_str, "mango")

    def test__set_end_str_should_set_value(self):
        simulator = Simulator()
        simulator._set_end_str("banana")
        self.assertEqual(simulator.end_str, "banana")

    def test__set_interval_should_set_value(self):
        simulator = Simulator()
        simulator._set_interval("1000.7")
        self.assertEqual(type(simulator.interval), float)

    def test__set_budget_should_set_value(self):
        simulator = Simulator()
        simulator._set_budget("1000000000")
        self.assertEqual(simulator.budget, 1000000000)
        self.assertEqual(type(simulator.budget), int)

        simulator._set_budget("-500")
        self.assertEqual(simulator.budget, 1000000000)

    def test__set_strategy_should_set_value(self):
        simulator = Simulator()
        simulator._set_strategy("BNH")
        self.assertEqual(simulator.strategy, "BNH")
        self.assertEqual(type(simulator.budget), int)

    def test__print_score_should_call_operator_get_score(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator._print_score()
        simulator.operator.get_score.assert_called_once()

    @patch("builtins.print")
    def test__print_trading_result_should_print_result_correctly(self, mock_print):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.operator.get_trading_results.return_value = [
            {
                "date_time": "today",
                "type": "buy",
                "price": 5000,
                "amount": 3,
            }
        ]
        simulator._print_trading_result()
        simulator.operator.get_trading_results.assert_called_once()
        self.assertEqual(mock_print.call_args_list[0][0][0], "@today, buy")
        self.assertEqual(mock_print.call_args_list[1][0][0], "5000 x 3")

    @patch("builtins.print")
    def test__print_trading_result_should_not_print_when_empty_result(self, mock_print):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.operator.get_trading_results.return_value = []
        simulator._print_trading_result()
        simulator.operator.get_score.assert_not_called()
