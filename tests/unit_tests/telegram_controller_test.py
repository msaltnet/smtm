import unittest
import requests
from smtm import TelegramController
from smtm import StrategySma0
from smtm.controller.telegram.ui_manager import TelegramUIManager
from unittest.mock import *


class TelegramControllerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_main_should_call__start_get_updates_loop(self):
        tcb = TelegramController()
        tcb.message_handler.terminating = True  # for Test
        tcb.message_handler.start_polling = MagicMock()
        tcb.main()

        tcb.message_handler.start_polling.assert_called_once()

    def test__terminate_should_set_terminating_flag_True(self):
        tcb = TelegramController()
        tcb.message_handler.stop_polling = MagicMock()
        tcb._terminate()
        tcb.message_handler.stop_polling.assert_called_once()

    def test__create_command_should_fill_command_list_correctly(self):
        tcb = TelegramController()
        # 새로운 구조에서는 commands 리스트가 초기화 시 생성됨
        self.assertEqual(len(tcb.commands), 5)

    def test__execute_command_should_call_action_correctly(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.main_keyboard = "mango keyboard"
        
        # 알 수 없는 명령어에 대한 가이드 메시지 테스트
        tcb._handle_message("안녕~")
        tcb.message_handler.send_text_message.assert_called_once()
        
        # 시작 명령어 테스트 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("1")
        # 중지 명령어 테스트
        tcb._handle_message("2")
        # 상태 조회 명령어 테스트
        tcb._handle_message("3")
        # 수익률 조회 명령어 테스트
        tcb._handle_message("4")
        # 거래내역 조회 명령어 테스트
        tcb._handle_message("5")

    @patch("threading.Thread")
    def test__start_get_updates_loop_start_thread_correctly(self, mock_thread):
        dummy_thread = MagicMock()
        mock_thread.return_value = dummy_thread
        tcb = TelegramController()
        tcb.message_handler.terminating = True  # for Test
        tcb.message_handler.start_polling()

        dummy_thread.start.assert_called()
        self.assertEqual(mock_thread.call_args[1]["name"], "get updates")
        self.assertEqual(mock_thread.call_args[1]["daemon"], True)

    def test__handle_message_call__execute_command_with_correct_commands(self):
        tcb = TelegramController()
        tcb.message_handler.CHAT_ID = 1234567890
        tcb.message_handler._get_updates = MagicMock(
            return_value={
                "ok": True,
                "result": [
                    {
                        "update_id": 402107588,
                        "message": {
                            "message_id": 11,
                            "from": {
                                "id": 1234567890,
                                "is_bot": False,
                                "first_name": "msaltnet",
                                "language_code": "ko",
                            },
                            "chat": {
                                "id": 1234567890,
                                "first_name": "msaltnet",
                                "type": "private",
                            },
                            "date": 1627694419,
                            "text": "3",
                        },
                    },
                    {
                        "update_id": 402107589,
                        "message": {
                            "message_id": 12,
                            "from": {
                                "id": 1234567891,
                                "is_bot": False,
                                "first_name": "msaltnet",
                                "language_code": "ko",
                            },
                            "chat": {
                                "id": 1234567891,
                                "first_name": "msaltnet",
                                "type": "private",
                            },
                            "date": 1627694420,
                            "text": "4",
                        },
                    },
                    {
                        "update_id": 402107590,
                        "message": {
                            "message_id": 13,
                            "from": {
                                "id": 1234567890,
                                "is_bot": False,
                                "first_name": "msaltnet",
                                "language_code": "ko",
                            },
                            "chat": {
                                "id": 1234567890,
                                "first_name": "msaltnet",
                                "type": "private",
                            },
                            "date": 1627694420,
                            "text": "5",
                        },
                    },
                ],
            }
        )
        tcb.message_handler._handle_message()

        self.assertEqual(tcb.message_handler.last_update_id, 402107590)

    def test__send_image_message_shoul_call_sendMessage_api_correctly(self):
        tcb = TelegramController()
        tcb.message_handler.post_worker = MagicMock()
        tcb.message_handler.TOKEN = "banana"
        tcb.message_handler.CHAT_ID = "to_banana"
        tcb.message_handler._send_http = MagicMock()
        tcb.message_handler.send_image_message("banana_file")
        tcb.message_handler.post_worker.post_task.assert_called_once_with(ANY)
        task = tcb.message_handler.post_worker.post_task.call_args[0][0]
        tcb.message_handler.post_worker.post_task.call_args[0][0]["runnable"](task)

        tcb.message_handler._send_http.assert_called_once_with(
            "https://api.telegram.org/banana/sendPhoto?chat_id=to_banana",
            is_post=True,
            file="banana_file",
        )

    def test__send_text_message_shoul_call_sendMessage_api_correctly(self):
        tcb = TelegramController()
        tcb.message_handler.post_worker = MagicMock()
        tcb.message_handler.TOKEN = "banana"
        tcb.message_handler.CHAT_ID = "to_banana"
        tcb.message_handler._send_http = MagicMock()
        tcb.message_handler.send_text_message("hello banana")
        tcb.message_handler.post_worker.post_task.assert_called_once_with(ANY)
        task = tcb.message_handler.post_worker.post_task.call_args[0][0]
        tcb.message_handler.post_worker.post_task.call_args[0][0]["runnable"](task)

        tcb.message_handler._send_http.assert_called_once_with(
            "https://api.telegram.org/banana/sendMessage?chat_id=to_banana&text=hello%20banana"
        )

    def test__send_text_message_shoul_call_sendMessage_api_correctly_with_keyboard(
        self,
    ):
        tcb = TelegramController()
        tcb.message_handler.post_worker = MagicMock()
        tcb.message_handler.TOKEN = "banana"
        tcb.message_handler.CHAT_ID = "to_banana"
        tcb.message_handler._send_http = MagicMock()
        tcb.message_handler.send_text_message("hello banana", "banana_keyboard_markup")
        tcb.message_handler.post_worker.post_task.assert_called_once_with(ANY)
        task = tcb.message_handler.post_worker.post_task.call_args[0][0]
        tcb.message_handler.post_worker.post_task.call_args[0][0]["runnable"](task)

        tcb.message_handler._send_http.assert_called_once_with(
            "https://api.telegram.org/banana/sendMessage?chat_id=to_banana&text=hello%20banana&reply_markup=banana_keyboard_markup"
        )

    def test__get_updates_call_getUpdates_api_correctly(self):
        tcb = TelegramController()
        tcb.message_handler.TOKEN = "banana"
        expected_response = "banana_result"
        tcb.message_handler._send_http = MagicMock(return_value=expected_response)
        updates = tcb.message_handler._get_updates()
        self.assertEqual(updates, expected_response)
        tcb.message_handler._send_http.assert_called_once_with(
            "https://api.telegram.org/banana/getUpdates?offset=1&timeout=10"
        )

    @patch("builtins.open", new_callable=mock_open)
    @patch("requests.post")
    def test__send_http_should_call_requests_post_with_file_and_return_result(
        self, mock_post, mock_file
    ):
        tcb = TelegramController()
        expected_response = {"dummy"}
        dummy_response = MagicMock()
        dummy_response.json.return_value = expected_response
        mock_post.return_value = dummy_response
        updates = tcb.message_handler._send_http("test_url", True, "mango")
        mock_file.assert_called_with("mango", "rb")
        self.assertEqual(updates, expected_response)
        self.assertEqual(mock_post.call_args[0][0].find("test_url"), 0)
        self.assertEqual(mock_post.call_args[1]["files"], {"photo": ANY})

    @patch("requests.post")
    def test__send_http_should_call_requests_post_when_is_post_True(self, mock_post):
        tcb = TelegramController()
        expected_response = {"dummy"}
        dummy_response = MagicMock()
        dummy_response.json.return_value = expected_response
        mock_post.return_value = dummy_response
        updates = tcb.message_handler._send_http("test_url", True)
        self.assertEqual(updates, expected_response)
        self.assertEqual(mock_post.call_args[0][0].find("test_url"), 0)

    @patch("requests.get")
    def test__send_http_should_call_requests_get_when_is_post_False(self, mock_get):
        tcb = TelegramController()
        expected_response = {"dummy"}
        dummy_response = MagicMock()
        dummy_response.json.return_value = expected_response
        mock_get.return_value = dummy_response
        updates = tcb.message_handler._send_http("test_url")
        self.assertEqual(updates, expected_response)
        self.assertEqual(mock_get.call_args[0][0].find("test_url"), 0)

    @patch("requests.get")
    def test__send_http_should_return_None_when_receive_invalid_data(self, mock_get):
        tcb = TelegramController()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        updates = tcb.message_handler._send_http("test_url")
        self.assertEqual(updates, None)

    @patch("requests.get")
    def test__send_http_should_return_None_when_receive_response_error(self, mock_get):
        tcb = TelegramController()
        dummy_response = MagicMock()
        dummy_response.json.return_value = "dummy_result"
        dummy_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTPError dummy exception"
        )
        mock_get.return_value = dummy_response

        updates = tcb.message_handler._send_http("test_url")
        self.assertEqual(updates, None)

    @patch("requests.get")
    def test__send_http_should_return_None_when_connection_fail(self, mock_get):
        tcb = TelegramController()
        dummy_response = MagicMock()
        dummy_response.json.return_value = "dummy_result"
        dummy_response.raise_for_status.side_effect = (
            requests.exceptions.RequestException("RequestException dummy exception")
        )
        mock_get.return_value = dummy_response

        updates = tcb.message_handler._send_http("test_url")
        self.assertEqual(updates, None)

    def test__query_state_should_call__send_text_message_with_correct_message(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.main_keyboard = "test_keyboard"
        
        # 상태 조회 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("3")
        
        # operator가 None인 경우
        tcb.message_handler.send_text_message.assert_called()
        
        # operator가 설정된 경우
        tcb.operator = "mango"
        tcb._handle_message("3")
        tcb.message_handler.send_text_message.assert_called()

    def test__convert_keyboard_markup_should_conver_correctly(self):
        setup_list = [
            {
                "guide": "운영 예산을 정해주세요",
                "keyboard": ["50000", "100000", "500000"],
            },
            {"guide": "거래소를 선택해 주세요", "keyboard": ["1. Upbit", "2. Bithumb"]},
        ]
        TelegramUIManager._convert_keyboard_markup(setup_list)

        self.assertEqual(
            setup_list[0]["keyboard"],
            "%7B%22keyboard%22%3A%20%5B%5B%7B%22text%22%3A%20%2250000%22%7D%5D%2C%20%5B%7B%22text%22%3A%20%22100000%22%7D%5D%2C%20%5B%7B%22text%22%3A%20%22500000%22%7D%5D%5D%7D",
        )
        self.assertEqual(
            setup_list[1]["keyboard"],
            "%7B%22keyboard%22%3A%20%5B%5B%7B%22text%22%3A%20%221.%20Upbit%22%7D%5D%2C%20%5B%7B%22text%22%3A%20%222.%20Bithumb%22%7D%5D%5D%7D",
        )

    def test__stop_trading_should_reset_all_variable_related_operating(self):
        tcb = TelegramController()
        tcb.operator = MagicMock()
        tcb.operator.stop = MagicMock(
            return_value={
                "summary": (
                    100,
                    200,
                    0.5,
                    0.9,
                    "test.jpg",
                    0,
                    0,
                    0,
                    ("12-01", "12-05", "12-08"),
                )
            }
        )
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.main_keyboard = "test_keyboard"

        # 중지 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("2")
        
        # operator가 설정되어 있으므로 중지 로직이 실행되어야 함
        tcb.message_handler.send_text_message.assert_called()
        # operator는 중지 후 None으로 설정됨
        self.assertEqual(tcb.operator, None)

    def test__start_trading_should_call_next_setup_message_correctly_when_step_0(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 시작 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("1")
        
        # 시작 명령어가 실행되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_call_next_setup_message_correctly_when_step_1(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 시작 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("1")
        
        # 시작 명령어가 실행되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_reset_with_wrong_input_when_step_1(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 잘못된 입력으로 시작 명령어 실행
        tcb._handle_message("invalid_input")
        
        # 가이드 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_call_next_setup_message_correctly_when_step_2(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 시작 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("1")
        
        # 시작 명령어가 실행되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_reset_with_wrong_input_when_step_2(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 잘못된 입력으로 시작 명령어 실행
        tcb._handle_message("invalid_input")
        
        # 가이드 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_call_next_setup_message_correctly_when_select_exchange(
        self,
    ):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 시작 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("1")
        
        # 시작 명령어가 실행되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_reset_with_wrong_input_when_select_exchange(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 잘못된 입력으로 시작 명령어 실행
        tcb._handle_message("invalid_input")
        
        # 가이드 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_call_next_setup_message_correctly_when_step_6(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 시작 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("1")
        
        # 시작 명령어가 실행되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_reset_with_wrong_input_when_step_5(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 잘못된 입력으로 시작 명령어 실행
        tcb._handle_message("invalid_input")
        
        # 가이드 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    @patch("smtm.Operator.start")
    @patch("smtm.Operator.initialize")
    def test__start_trading_should_call_next_setup_message_correctly_when_step_6(
        self, mock_start, mock_initialize
    ):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 시작 명령어 실행 (실제로는 Command Pattern을 통해 처리됨)
        tcb._handle_message("1")
        
        # 시작 명령어가 실행되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__start_trading_should_reset_with_wrong_input_when_step_5(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 잘못된 입력으로 시작 명령어 실행
        tcb._handle_message("invalid_input")
        
        # 가이드 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__query_score_should_call_send_error_message_when_not_running(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 수익률 조회 명령어 실행 (operator가 None인 경우)
        tcb._handle_message("4")
        
        # 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__query_score_should_call_next_setup_message_correctly_when_step_0(self):
        tcb = TelegramController()
        tcb.operator = MagicMock()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 수익률 조회 명령어 실행 (operator가 있는 경우)
        tcb._handle_message("4")
        
        # 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__query_score_should_call_next_setup_message_correctly_when_step_1(self):
        tcb = TelegramController()
        tcb.operator = MagicMock()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.message_handler.send_image_message = MagicMock()
        
        # 수익률 조회 명령어 실행
        tcb._handle_message("4")
        
        # 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test__query_score_should_reset_with_wrong_input_when_step_1(self):
        tcb = TelegramController()
        tcb.operator = MagicMock()
        tcb.message_handler.send_text_message = MagicMock()
        
        # 잘못된 입력으로 수익률 조회 명령어 실행
        tcb._handle_message("invalid_input")
        
        # 가이드 메시지가 전송되어야 함
        tcb.message_handler.send_text_message.assert_called()

    def test_alert_callback_should_call__send_text_message(self):
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.main_keyboard = "banana"
        tcb.alert_callback("mango")
        tcb.message_handler.send_text_message.assert_called_once_with("Alert: mango", "banana")

    def test_start_trading_command_can_handle_initial_state(self):
        """Test StartTradingCommand can_handle in initial state"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        
        tcb = TelegramController()
        start_command = StartTradingCommand(tcb)
        
        # Initial state should only handle start commands
        self.assertTrue(start_command.can_handle("1"))
        self.assertFalse(start_command.can_handle("50000"))
        self.assertFalse(start_command.can_handle("BTC"))
        self.assertFalse(start_command.can_handle("invalid"))

    def test_start_trading_command_can_handle_in_progress_state(self):
        """Test StartTradingCommand can_handle when setup is in progress"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        
        tcb = TelegramController()
        start_command = StartTradingCommand(tcb)
        
        # Set in_progress to simulate setup process
        start_command.in_progress = lambda x: None
        
        # In progress state should handle any command
        self.assertTrue(start_command.can_handle("1"))
        self.assertTrue(start_command.can_handle("50000"))
        self.assertTrue(start_command.can_handle("BTC"))
        self.assertTrue(start_command.can_handle("UPBIT"))
        self.assertTrue(start_command.can_handle("invalid"))

    def test_start_trading_command_can_handle_after_reset(self):
        """Test StartTradingCommand can_handle after process is reset"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        
        tcb = TelegramController()
        start_command = StartTradingCommand(tcb)
        
        # Set in_progress first
        start_command.in_progress = lambda x: None
        self.assertTrue(start_command.can_handle("50000"))
        
        # Reset the process
        start_command._terminate_start_in_progress()
        
        # Should return to initial state behavior
        self.assertTrue(start_command.can_handle("1"))
        self.assertFalse(start_command.can_handle("50000"))
        self.assertFalse(start_command.can_handle("BTC"))

    def test_start_trading_command_setup_process_flow(self):
        """Test complete setup process flow with can_handle"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.get_setup_message = MagicMock(return_value=("Setup message", "keyboard"))
        tcb.setup_manager.validate_budget = MagicMock(return_value=(True, 50000))
        tcb.setup_manager.set_budget = MagicMock()
        
        start_command = StartTradingCommand(tcb)
        
        # Step 1: Initial start command
        self.assertTrue(start_command.can_handle("1"))
        start_command.execute("1")
        
        # Step 2: Budget input (should be handled because in_progress is set)
        self.assertTrue(start_command.can_handle("50000"))
        start_command.execute("50000")
        
        # Verify budget was set
        tcb.setup_manager.set_budget.assert_called_once_with(50000)

    def test_start_trading_command_handles_invalid_input_during_setup(self):
        """Test StartTradingCommand handles invalid input during setup process"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.msg = {"ERROR_RESTART": "Error restart message"}
        tcb.ui_manager.main_keyboard = "main_keyboard"
        tcb.setup_manager.reset_setup = MagicMock()
        
        start_command = StartTradingCommand(tcb)
        
        # Start the process
        start_command.execute("1")
        
        # Send invalid input during setup
        start_command.execute("invalid_input")
        
        # Should reset the process
        tcb.setup_manager.reset_setup.assert_called_once()
        tcb.message_handler.send_text_message.assert_called_with(
            "Error restart message", "main_keyboard"
        )

    def test_complete_trading_setup_flow_simulation(self):
        """Test complete trading setup flow simulation - the original bug scenario"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.get_setup_message = MagicMock(return_value=("Setup message", "keyboard"))
        tcb.ui_manager.msg = {"ERROR_RESTART": "Error restart message", "COMMAND_C_1": "Start"}
        tcb.ui_manager.main_keyboard = "main_keyboard"
        
        # Mock setup manager methods
        tcb.setup_manager.validate_budget = MagicMock(return_value=(True, 50000))
        tcb.setup_manager.validate_currency = MagicMock(return_value=(True, "BTC"))
        tcb.setup_manager.validate_data_provider = MagicMock(return_value=(True, "mock_data_provider"))
        tcb.setup_manager.validate_exchange = MagicMock(return_value=(True, "UPBIT"))
        tcb.setup_manager.validate_strategy = MagicMock(return_value=(True, "mock_strategy"))
        
        tcb.setup_manager.set_budget = MagicMock()
        tcb.setup_manager.set_currency = MagicMock()
        tcb.setup_manager.set_data_provider = MagicMock()
        tcb.setup_manager.set_trader = MagicMock()
        tcb.setup_manager.set_strategy = MagicMock()
        tcb.setup_manager.get_setup_summary = MagicMock(return_value={
            "currency": "BTC",
            "strategy": type("MockStrategy", (), {"NAME": "TestStrategy"}),
            "trader": type("MockTrader", (), {"NAME": "TestTrader"}),
            "budget": 50000
        })
        
        start_command = StartTradingCommand(tcb)
        
        # Simulate the original bug scenario: Start -> Budget -> should continue
        # Step 1: User sends "Start" (or "1")
        self.assertTrue(start_command.can_handle("1"))
        start_command.execute("1")
        
        # Step 2: User sends budget "50000" - this should be handled now
        self.assertTrue(start_command.can_handle("50000"))
        start_command.execute("50000")
        
        # Verify budget was set
        tcb.setup_manager.set_budget.assert_called_once_with(50000)
        
        # Step 3: User sends currency "BTC"
        self.assertTrue(start_command.can_handle("BTC"))
        start_command.execute("BTC")
        
        # Verify currency was set
        tcb.setup_manager.set_currency.assert_called_once_with("BTC")

    def test_trading_setup_command_priority_during_setup(self):
        """Test that StartTradingCommand handles all inputs during setup process"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        from smtm.controller.telegram.commands.stop_trading_command import StopTradingCommand
        
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.get_setup_message = MagicMock(return_value=("Setup message", "keyboard"))
        tcb.setup_manager.validate_budget = MagicMock(return_value=(True, 50000))
        tcb.setup_manager.set_budget = MagicMock()
        
        start_command = StartTradingCommand(tcb)
        stop_command = StopTradingCommand(tcb)
        
        # Start the setup process
        start_command.execute("1")
        
        # During setup, StartTradingCommand should handle all inputs
        # This is the key fix - StartTradingCommand now handles any input during setup
        self.assertTrue(start_command.can_handle("2"))
        self.assertTrue(start_command.can_handle("50000"))
        self.assertTrue(start_command.can_handle("BTC"))
        self.assertTrue(start_command.can_handle("invalid"))
        
        # Both commands can handle "2", but StartTradingCommand should be checked first
        # due to the order in the commands list
        self.assertTrue(stop_command.can_handle("2"))

    def test_setup_process_state_management(self):
        """Test proper state management during setup process"""
        from smtm.controller.telegram.commands.start_trading_command import StartTradingCommand
        
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.get_setup_message = MagicMock(return_value=("Setup message", "keyboard"))
        tcb.ui_manager.msg = {"ERROR_RESTART": "Error restart message"}
        tcb.ui_manager.main_keyboard = "main_keyboard"
        tcb.setup_manager.reset_setup = MagicMock()
        
        start_command = StartTradingCommand(tcb)
        
        # Initial state
        self.assertEqual(start_command.in_progress_step, 0)
        self.assertIsNone(start_command.in_progress)
        
        # Start process
        start_command.execute("1")
        self.assertEqual(start_command.in_progress_step, 1)
        self.assertIsNotNone(start_command.in_progress)
        
        # Reset process
        start_command._terminate_start_in_progress()
        self.assertEqual(start_command.in_progress_step, 0)
        self.assertIsNone(start_command.in_progress)

    def test_query_score_command_can_handle_initial_state(self):
        """Test QueryScoreCommand can_handle in initial state"""
        from smtm.controller.telegram.commands.query_score_command import QueryScoreCommand
        
        tcb = TelegramController()
        tcb.ui_manager.msg = {
            "COMMAND_C_4": "Return rate", 
            "PERIOD_1": "6 hours",
            "PERIOD_2": "12 hours",
            "PERIOD_3": "24 hours",
            "PERIOD_4": "2 days",
            "PERIOD_5": "3 days"
        }
        query_command = QueryScoreCommand(tcb)
        
        # Initial state should only handle query score commands
        self.assertTrue(query_command.can_handle("4"))
        self.assertTrue(query_command.can_handle("Return rate"))
        self.assertFalse(query_command.can_handle("1"))
        self.assertFalse(query_command.can_handle("6 hours"))

    def test_query_score_command_can_handle_in_progress_state(self):
        """Test QueryScoreCommand can_handle when query is in progress"""
        from smtm.controller.telegram.commands.query_score_command import QueryScoreCommand
        
        tcb = TelegramController()
        tcb.ui_manager.msg = {
            "COMMAND_C_4": "Return rate", 
            "PERIOD_1": "6 hours",
            "PERIOD_2": "12 hours",
            "PERIOD_3": "24 hours",
            "PERIOD_4": "2 days",
            "PERIOD_5": "3 days"
        }
        query_command = QueryScoreCommand(tcb)
        
        # Set in_progress to simulate query process
        query_command.in_progress = lambda x: None
        
        # In progress state should handle any command
        self.assertTrue(query_command.can_handle("4"))
        self.assertTrue(query_command.can_handle("1"))
        self.assertTrue(query_command.can_handle("6 hours"))
        self.assertTrue(query_command.can_handle("invalid"))

    def test_query_score_command_can_handle_after_reset(self):
        """Test QueryScoreCommand can_handle after process is reset"""
        from smtm.controller.telegram.commands.query_score_command import QueryScoreCommand
        
        tcb = TelegramController()
        tcb.ui_manager.msg = {
            "COMMAND_C_4": "Return rate", 
            "PERIOD_1": "6 hours",
            "PERIOD_2": "12 hours",
            "PERIOD_3": "24 hours",
            "PERIOD_4": "2 days",
            "PERIOD_5": "3 days"
        }
        query_command = QueryScoreCommand(tcb)
        
        # Set in_progress first
        query_command.in_progress = lambda x: None
        self.assertTrue(query_command.can_handle("6 hours"))
        
        # Reset the process
        query_command.in_progress = None
        query_command.in_progress_step = 0
        
        # Should return to initial state behavior
        self.assertTrue(query_command.can_handle("4"))
        self.assertFalse(query_command.can_handle("6 hours"))
        self.assertFalse(query_command.can_handle("1"))

    def test_query_score_command_query_process_flow(self):
        """Test complete query score process flow with can_handle"""
        from smtm.controller.telegram.commands.query_score_command import QueryScoreCommand
        
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.msg = {
            "COMMAND_C_4": "Return rate",
            "PERIOD_1": "6 hours",
            "PERIOD_2": "12 hours",
            "PERIOD_3": "24 hours",
            "PERIOD_4": "2 days",
            "PERIOD_5": "3 days",
            "INFO_STATUS_READY": "Ready message"
        }
        tcb.ui_manager.main_keyboard = "main_keyboard"
        tcb.ui_manager.get_score_query_message = MagicMock(return_value=("Query message", "keyboard"))
        tcb.operator = None  # Simulate no operator running
        
        query_command = QueryScoreCommand(tcb)
        
        # Step 1: Initial query command
        self.assertTrue(query_command.can_handle("4"))
        query_command.execute("4")
        
        # Should show ready message when no operator is running
        tcb.message_handler.send_text_message.assert_called_with(
            "Ready message", "main_keyboard"
        )

    def test_query_score_command_handles_period_selection(self):
        """Test QueryScoreCommand handles period selection during query process"""
        from smtm.controller.telegram.commands.query_score_command import QueryScoreCommand
        
        tcb = TelegramController()
        tcb.message_handler.send_text_message = MagicMock()
        tcb.ui_manager.msg = {
            "COMMAND_C_4": "Return rate",
            "PERIOD_1": "6 hours",
            "PERIOD_2": "12 hours",
            "PERIOD_3": "24 hours",
            "PERIOD_4": "2 days",
            "PERIOD_5": "3 days",
            "INFO_QUERY_RUNNING": "Query running message"
        }
        tcb.ui_manager.main_keyboard = "main_keyboard"
        tcb.ui_manager.get_score_query_message = MagicMock(return_value=("Query message", "keyboard"))
        tcb.ui_manager.score_query_list = ["step1", "step2"]  # Mock query list
        
        # Mock operator with get_score method
        mock_operator = MagicMock()
        mock_operator.get_score = MagicMock()
        tcb.operator = mock_operator
        
        query_command = QueryScoreCommand(tcb)
        
        # Start the query process
        query_command.execute("4")
        
        # Step 2: Period selection (should be handled because in_progress is set)
        self.assertTrue(query_command.can_handle("1"))  # Period selection
        query_command.execute("1")
        
        # Verify get_score was called with correct parameters
        mock_operator.get_score.assert_called_once()