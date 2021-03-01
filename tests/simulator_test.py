import unittest
from smtm import Simulator
from unittest.mock import *


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("signal.signal")
    @patch("builtins.input", side_effect=EOFError)
    def test_main_call_signal_to_listen_sigterm(self, mock_input, mock_signal):
        simulator = Simulator()
        simulator.main()
        mock_signal.assert_called_with(ANY, simulator.stop)

    def test_create_command_make_command_static_info(self):
        simulator = Simulator()
        simulator.command_list = []
        self.assertEqual(len(simulator.command_list), 0)
        simulator.create_command()
        self.assertEqual(len(simulator.command_list), 12)

    @patch("builtins.print")
    def test_print_help_print_guide_correctly(self, mock_print):
        simulator = Simulator()
        simulator.command_list = [{"guide": "orange"}]
        simulator.print_help()
        self.assertEqual(mock_print.call_args_list[0][0][0], "command list =================")
        self.assertEqual(mock_print.call_args_list[1][0][0], "orange")

    def test_on_command_call_exactly_when_need_value_is_False(self):
        simulator = Simulator()
        simulator.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": "help",
                "short": "h",
                "need_value": False,
            },
        ]
        simulator.execute_command = MagicMock()
        simulator.on_command("hell")
        simulator.execute_command.assert_not_called()
        simulator.on_command("help")
        simulator.execute_command.assert_called_once_with("help", None)

    @patch("builtins.print")
    def test_on_command_just_print_error_message_when_invalid_command(self, mock_print):
        simulator = Simulator()
        simulator.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": "help",
                "short": "h",
                "need_value": False,
            },
        ]
        simulator.execute_command = MagicMock()
        simulator.on_command("hell")
        simulator.execute_command.assert_not_called()
        mock_print.assert_called_once_with("invalid command")

    @patch("builtins.input")
    def test_on_command_call_with_value(self, mock_input):
        simulator = Simulator()
        simulator.command_list = [
            {
                "guide": "c, count         set simulation count",
                "cmd": "count",
                "short": "c",
                "need_value": True,
                "value_guide": "input simulation count (ex. 100) :",
            },
        ]
        mock_input.return_value = "mango"
        simulator.execute_command = MagicMock()
        simulator.on_command("c")
        mock_input.assert_called_once_with("input simulation count (ex. 100) :")
        simulator.execute_command.assert_called_once_with("c", "mango")

    def test_execute_command_call_action_correclty(self):
        simulator = Simulator()
        simulator.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": "help",
                "short": "h",
                "need_value": False,
                "action": MagicMock(),
            },
            {
                "guide": "c, count         set simulation count",
                "cmd": "count",
                "short": "c",
                "need_value": True,
                "value_guide": "input simulation count (ex. 100) :",
                "action": MagicMock(),
            },
        ]
        simulator.execute_command("h", None)
        simulator.command_list[0]["action"].assert_called_once()
        simulator.command_list[1]["action"].assert_not_called()
        simulator.execute_command("c", 77)
        simulator.command_list[1]["action"].assert_called_once_with(77)

    @patch("builtins.print")
    def test_execute_command_just_print_error_message_when_invalid_command(self, mock_print):
        simulator = Simulator()
        simulator.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": "help",
                "short": "h",
                "need_value": False,
                "action": MagicMock(),
            },
        ]
        simulator.execute_command("hell", None)
        simulator.command_list[0]["action"].assert_not_called()
        mock_print.assert_called_once_with("invalid command")

    @patch("builtins.print")
    def test_execute_command_call_on_query_command(self, mock_print):
        simulator = Simulator()
        simulator.operator.state = "mango"
        simulator.operator.get_score = MagicMock()
        simulator.execute_command("q", "state")
        mock_print.assert_called_once_with("mango")
        simulator.execute_command("q", "score")
        simulator.operator.get_score.assert_called_once_with(ANY)

    def test_execute_command_call_set_end(self):
        simulator = Simulator()
        simulator.end = "mango"
        simulator.execute_command("e", "2021T01-11")
        self.assertEqual(simulator.end, "2021 01-11")

    def test_execute_command_call_set_count(self):
        simulator = Simulator()
        simulator.count = 999
        simulator.execute_command("c", "777")
        self.assertEqual(simulator.count, 777)

    def test_execute_command_call_set_interval(self):
        simulator = Simulator()
        simulator.interval = 0.0001
        simulator.execute_command("int", "0.05")
        self.assertEqual(simulator.interval, 0.05)

    def test_execute_command_call_set_budget(self):
        simulator = Simulator()
        simulator.budget = 500
        simulator.execute_command("b", "90000")
        self.assertEqual(simulator.budget, 90000)

    def test_execute_command_call_set_strategy(self):
        simulator = Simulator()
        simulator.strategy = -1
        simulator.execute_command("st", "0")
        self.assertEqual(simulator.strategy, 0)

    def test_initialize_call_initialize_simulation(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.interval = 0.1
        simulator.initialize()
        self.assertEqual(simulator.is_initialized, True)
        simulator.operator.initialize_simulation.assert_called_once()
        simulator.operator.set_interval.assert_called_once_with(0.1)

    def test_start_call_operator_start(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.is_initialized = False
        simulator.start()
        simulator.operator.start.assert_not_called()

        simulator.is_initialized = True
        simulator.start()
        simulator.operator.start.assert_called()

    def test_stop_call_operator_stop(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.stop(None, None)
        simulator.operator.stop.assert_called()

    def test_terminate_call_operator_stop(self):
        simulator = Simulator()
        simulator.operator = MagicMock()
        simulator.terminate()
        simulator.operator.stop.assert_called()
