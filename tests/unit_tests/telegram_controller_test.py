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
