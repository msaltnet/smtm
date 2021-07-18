import unittest
from smtm import Controller
from unittest.mock import *


class ControllerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("signal.signal")
    @patch("builtins.input", side_effect=EOFError)
    def test_main_call_signal_to_listen_sigterm(self, mock_input, mock_signal):
        controller = Controller()
        controller.operator = MagicMock()
        controller.main()
        mock_signal.assert_called_with(ANY, controller.terminate)

    def test_create_command_make_command_static_info(self):
        controller = Controller()
        controller.command_list = []
        self.assertEqual(len(controller.command_list), 0)
        controller.create_command()
        self.assertEqual(len(controller.command_list), 5)

    @patch("builtins.print")
    def test_print_help_print_guide_correctly(self, mock_print):
        controller = Controller()
        controller.command_list = [{"guide": "orange"}]
        controller.print_help()
        self.assertEqual(mock_print.call_args_list[0][0][0], "명령어 목록 =================")
        self.assertEqual(mock_print.call_args_list[1][0][0], "orange")

    def test__on_command_call_exactly_when_need_value_is_False(self):
        controller = Controller()
        dummy_action = MagicMock()
        controller.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": "help",
                "short": "h",
                "need_value": False,
                "action": dummy_action,
            },
        ]
        controller._on_command("help")
        dummy_action.assert_called()

    @patch("builtins.print")
    def test__on_command_just_print_error_message_when_invalid_command(self, mock_print):
        controller = Controller()
        controller.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": "help",
                "short": "h",
                "need_value": False,
            },
        ]
        controller._on_command("hell")
        mock_print.assert_called_once_with("잘못된 명령어가 입력되었습니다")

    @patch("builtins.input", side_effect=["1"])
    @patch("builtins.print")
    def test__on_query_command_should_handle_command_1(self, mock_print, mock_input):
        controller = Controller()
        controller.operator = MagicMock()
        controller.operator.state = "mango"
        controller._on_query_command()
        mock_print.assert_called_once_with("현재 상태: MANGO")

    @patch("builtins.input", side_effect=["state"])
    @patch("builtins.print")
    def test__on_query_command_should_handle_command_state(self, mock_print, mock_input):
        controller = Controller()
        controller.operator = MagicMock()
        controller.operator.state = "mango"
        controller._on_query_command()
        mock_print.assert_called_once_with("현재 상태: MANGO")

    @patch("builtins.input", side_effect=["2"])
    @patch("builtins.print")
    def test__on_query_command_should_handle_command_2(self, mock_print, mock_input):
        controller = Controller()
        controller.operator = MagicMock()
        controller._on_query_command()
        controller.operator.get_score.assert_called_once_with(ANY)

    @patch("builtins.input", side_effect=["score"])
    @patch("builtins.print")
    def test__on_query_command_should_handle_command_score(self, mock_print, mock_input):
        controller = Controller()
        controller.operator = MagicMock()
        controller._on_query_command()
        controller.operator.get_score.assert_called_once_with(ANY)

    @patch("builtins.input", side_effect=["3"])
    @patch("builtins.print")
    def test__on_query_command_should_handle_command_3(self, mock_print, mock_input):
        controller = Controller()
        controller.operator = MagicMock()
        controller._on_query_command()
        controller.operator.get_trading_results.assert_called_once()

    @patch("builtins.input", side_effect=["result"])
    @patch("builtins.print")
    def test__on_query_command_should_handle_command_result(self, mock_print, mock_input):
        controller = Controller()
        controller.operator = MagicMock()
        controller._on_query_command()
        controller.operator.get_trading_results.assert_called_once()

    def test_start_call_operator_start(self):
        controller = Controller()
        controller.operator = MagicMock()
        controller.start()
        controller.operator.start.assert_called()

    def test_stop_call_operator_stop(self):
        controller = Controller()
        controller.operator = MagicMock()
        controller.stop()
        controller.operator.stop.assert_called()

    def test_terminate_call_operator_stop(self):
        controller = Controller()
        controller.operator = MagicMock()
        controller.terminate()
        controller.operator.stop.assert_called()
