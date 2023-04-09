import unittest
import requests
from smtm import TelegramController
from smtm import StrategySma0
from unittest.mock import *


class TelegramControllerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_main_should_call__start_get_updates_loop(self):
        tcb = TelegramController()
        tcb.terminating = True  # for Test
        tcb._start_get_updates_loop = MagicMock()
        tcb.main()

        tcb._start_get_updates_loop.assert_called_once()

    def test__terminate_should_set_terminating_flag_True(self):
        tcb = TelegramController()
        tcb.post_worker = MagicMock()
        tcb._terminate()
        self.assertEqual(tcb.terminating, True)
        tcb.post_worker.stop.assert_called_once()

    def test__create_command_should_fill_command_list_correctly(self):
        tcb = TelegramController()
        tcb.command_list = []
        tcb._create_command()
        self.assertEqual(len(tcb.command_list), 5)

    def test__execute_command_should_call_action_correctly(self):
        tcb = TelegramController()
        tcb._send_text_message = MagicMock()
        tcb.main_keyboard = "mango keyboard"
        dummy_command_list = [
            {
                "guide": "{0:15}자동 거래 시작".format("1. 시작"),
                "cmd": ["시작", "1", "1. 시작"],
                "action": MagicMock(),
            },
            {
                "guide": "{0:15}자동 거래 중지".format("2. 중지"),
                "cmd": ["중지", "2", "2. 중지"],
                "action": MagicMock(),
            },
        ]
        tcb.command_list = dummy_command_list
        tcb._execute_command("안녕~")
        tcb._send_text_message.assert_called_once_with(
            "자동 거래 시작 전입니다.\n명령어를 입력해주세요.\n\n1. 시작          자동 거래 시작\n2. 중지          자동 거래 중지\n",
            "mango keyboard",
        )

        tcb._execute_command("1")
        dummy_command_list[0]["action"].assert_called_with("1")

        tcb._execute_command("시작")
        dummy_command_list[0]["action"].assert_called_with("시작")

        tcb._execute_command("2")
        dummy_command_list[1]["action"].assert_called_with("2")

        tcb._execute_command("중지")
        dummy_command_list[1]["action"].assert_called_with("중지")

        dummy_in_progress = MagicMock()
        tcb.in_progress = dummy_in_progress
        tcb._execute_command("2. 중지")
        dummy_in_progress.assert_called_once_with("2. 중지")

    @patch("threading.Thread")
    def test__start_get_updates_loop_start_thread_correctly(self, mock_thread):
        dummy_thread = MagicMock()
        mock_thread.return_value = dummy_thread
        tcb = TelegramController()
        tcb._handle_message = MagicMock()
        tcb.terminating = True  # for Test
        tcb._start_get_updates_loop()

        dummy_thread.start.assert_called()
        self.assertEqual(mock_thread.call_args[1]["name"], "get updates")
        self.assertEqual(mock_thread.call_args[1]["daemon"], True)

    def test__handle_message_call__execute_command_with_correct_commands(self):
        tcb = TelegramController()
        tcb.CHAT_ID = 1234567890
        tcb._execute_command = MagicMock()
        tcb._get_updates = MagicMock(
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
                            "chat": {"id": 1234567890, "first_name": "msaltnet", "type": "private"},
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
                            "chat": {"id": 1234567891, "first_name": "msaltnet", "type": "private"},
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
                            "chat": {"id": 1234567890, "first_name": "msaltnet", "type": "private"},
                            "date": 1627694420,
                            "text": "5",
                        },
                    },
                ],
            }
        )
        tcb._handle_message()

        self.assertEqual(tcb._execute_command.call_args_list[0][0][0], "3")
        self.assertEqual(tcb._execute_command.call_args_list[1][0][0], "5")
        self.assertEqual(tcb.last_update_id, 402107590)

    def test__send_image_message_shoul_call_sendMessage_api_correctly(self):
        tcb = TelegramController()
        tcb.post_worker = MagicMock()
        tcb.TOKEN = "banana"
        tcb.CHAT_ID = "to_banana"
        tcb._send_http = MagicMock()
        tcb._send_image_message("banana_file")
        tcb.post_worker.post_task.assert_called_once_with(ANY)
        task = tcb.post_worker.post_task.call_args[0][0]
        tcb.post_worker.post_task.call_args[0][0]["runnable"](task)

        tcb._send_http.assert_called_once_with(
            "https://api.telegram.org/banana/sendPhoto?chat_id=to_banana", True, "banana_file"
        )

    def test__send_text_message_shoul_call_sendMessage_api_correctly(self):
        tcb = TelegramController()
        tcb.post_worker = MagicMock()
        tcb.TOKEN = "banana"
        tcb.CHAT_ID = "to_banana"
        tcb._send_http = MagicMock()
        tcb._send_text_message("hello banana")
        tcb.post_worker.post_task.assert_called_once_with(ANY)
        task = tcb.post_worker.post_task.call_args[0][0]
        tcb.post_worker.post_task.call_args[0][0]["runnable"](task)

        tcb._send_http.assert_called_once_with(
            "https://api.telegram.org/banana/sendMessage?chat_id=to_banana&text=hello%20banana"
        )

    def test__send_text_message_shoul_call_sendMessage_api_correctly_with_keyboard(self):
        tcb = TelegramController()
        tcb.post_worker = MagicMock()
        tcb.TOKEN = "banana"
        tcb.CHAT_ID = "to_banana"
        tcb._send_http = MagicMock()
        tcb._send_text_message("hello banana", "banana_keyboard_markup")
        tcb.post_worker.post_task.assert_called_once_with(ANY)
        task = tcb.post_worker.post_task.call_args[0][0]
        tcb.post_worker.post_task.call_args[0][0]["runnable"](task)

        tcb._send_http.assert_called_once_with(
            "https://api.telegram.org/banana/sendMessage?chat_id=to_banana&text=hello%20banana&reply_markup=banana_keyboard_markup"
        )

    def test__get_updates_call_getUpdates_api_correctly(self):
        tcb = TelegramController()
        tcb.TOKEN = "banana"
        expected_response = "banana_result"
        tcb._send_http = MagicMock(return_value=expected_response)
        updates = tcb._get_updates()
        self.assertEqual(updates, expected_response)
        tcb._send_http.assert_called_once_with(
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
        updates = tcb._send_http("test_url", True, "mango")
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
        updates = tcb._send_http("test_url", True)
        self.assertEqual(updates, expected_response)
        self.assertEqual(mock_post.call_args[0][0].find("test_url"), 0)

    @patch("requests.get")
    def test__send_http_should_call_requests_get_when_is_post_False(self, mock_get):
        tcb = TelegramController()
        expected_response = {"dummy"}
        dummy_response = MagicMock()
        dummy_response.json.return_value = expected_response
        mock_get.return_value = dummy_response
        updates = tcb._send_http("test_url")
        self.assertEqual(updates, expected_response)
        self.assertEqual(mock_get.call_args[0][0].find("test_url"), 0)

    @patch("requests.get")
    def test__send_http_should_return_None_when_receive_invalid_data(self, mock_get):
        tcb = TelegramController()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        updates = tcb._send_http("test_url")
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

        updates = tcb._send_http("test_url")
        self.assertEqual(updates, None)

    @patch("requests.get")
    def test__send_http_should_return_None_when_connection_fail(self, mock_get):
        tcb = TelegramController()
        dummy_response = MagicMock()
        dummy_response.json.return_value = "dummy_result"
        dummy_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "RequestException dummy exception"
        )
        mock_get.return_value = dummy_response

        updates = tcb._send_http("test_url")
        self.assertEqual(updates, None)

    def test__query_state_should_call__send_text_message_with_correct_message(self):
        tcb = TelegramController()
        tcb._send_text_message = MagicMock()
        tcb._query_state("state")
        tcb._send_text_message.assert_called_with("자동 거래 시작 전입니다")

        tcb.operator = "mango"
        tcb._query_state("state")
        tcb._send_text_message.assert_called_with("자동 거래 운영 중입니다")

    def test__convert_keyboard_markup_should_conver_correctly(self):
        setup_list = [
            {"guide": "운영 예산을 정해주세요", "keyboard": ["50000", "100000", "500000"]},
            {"guide": "거래소를 선택해 주세요", "keyboard": ["1. Upbit", "2. Bithumb"]},
        ]
        TelegramController._convert_keyboard_markup(setup_list)

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
        tcb.strategy = "mango_strategy"
        tcb.data_provider = "mango_data_provider"
        tcb.trader = "mango_trader"
        tcb.budget = "mango_budget"
        tcb.operator.stop = MagicMock(
            return_value={
                "summary": (100, 200, 0.5, 0.9, "test.jpg", 0, 0, 0, ("12-01", "12-05", "12-08"))
            }
        )
        tcb._send_text_message = MagicMock()

        tcb._stop_trading("2")
        tcb._send_text_message.assert_called_once_with(
            "자동 거래가 중지되었습니다\n12-05 - 12-08\n자산 100 -> 200\n수익률 0.5\n비교 수익률 0.9\n", tcb.main_keyboard
        )
        self.assertEqual(tcb.operator, None)
        self.assertEqual(tcb.strategy, None)
        self.assertEqual(tcb.data_provider, None)
        self.assertEqual(tcb.trader, None)
        self.assertEqual(tcb.budget, None)

    def test__start_trading_should_call_next_setup_message_correctly_when_step_0(self):
        tcb = TelegramController()
        tcb.in_progress_step = 0
        tcb._send_text_message = MagicMock()
        tcb._start_trading("1")

        tcb._send_text_message.assert_called_once_with(
            tcb.setup_list[0]["guide"], tcb.setup_list[0]["keyboard"]
        )
        self.assertEqual(tcb.in_progress, tcb._start_trading)
        self.assertEqual(tcb.in_progress_step, 1)

    def test__start_trading_should_call_next_setup_message_correctly_when_step_1(self):
        tcb = TelegramController()
        tcb.in_progress_step = 1
        tcb._send_text_message = MagicMock()
        tcb._start_trading("5000")

        tcb._send_text_message.assert_called_once_with(
            tcb.setup_list[1]["guide"], tcb.setup_list[1]["keyboard"]
        )
        self.assertEqual(tcb.in_progress, tcb._start_trading)
        self.assertEqual(tcb.in_progress_step, 2)

    def test__start_trading_should_reset_with_wrong_input_when_step_1(self):
        tcb = TelegramController()
        tcb.in_progress_step = 1
        tcb._send_text_message = MagicMock()
        tcb._start_trading("5000.5")
        wrong_message = "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요"
        tcb._send_text_message.assert_called_once_with(wrong_message, tcb.main_keyboard)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    def test__start_trading_should_call_next_setup_message_correctly_when_step_2(self):
        tcb = TelegramController()
        tcb.in_progress_step = 2
        tcb._send_text_message = MagicMock()
        tcb._start_trading("BTC")

        tcb._send_text_message.assert_called_once_with(
            tcb.setup_list[2]["guide"], tcb.setup_list[2]["keyboard"]
        )
        self.assertEqual(tcb.currency, "BTC")
        self.assertEqual(tcb.in_progress, tcb._start_trading)
        self.assertEqual(tcb.in_progress_step, 3)

        tcb = TelegramController()
        tcb.in_progress_step = 2
        tcb._send_text_message = MagicMock()
        tcb._start_trading("ETH")

        tcb._send_text_message.assert_called_once_with(
            tcb.setup_list[2]["guide"], tcb.setup_list[2]["keyboard"]
        )
        self.assertEqual(tcb.currency, "ETH")
        self.assertEqual(tcb.in_progress, tcb._start_trading)
        self.assertEqual(tcb.in_progress_step, 3)

    def test__start_trading_should_reset_with_wrong_input_when_step_2(self):
        tcb = TelegramController()
        tcb.in_progress_step = 2
        tcb._send_text_message = MagicMock()
        tcb._start_trading("upbit")
        wrong_message = "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요"
        tcb._send_text_message.assert_called_once_with(wrong_message, tcb.main_keyboard)
        self.assertEqual(tcb.currency, None)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    def test__start_trading_should_call_next_setup_message_correctly_when_step_3(self):
        tcb = TelegramController()
        tcb.in_progress_step = 3
        tcb._send_text_message = MagicMock()
        tcb.currency = "BTC"
        tcb._start_trading("upbit")

        tcb._send_text_message.assert_called_once_with(
            tcb.setup_list[3]["guide"], tcb.setup_list[3]["keyboard"]
        )
        self.assertIsNotNone(tcb.trader)
        self.assertIsNotNone(tcb.data_provider)
        self.assertEqual(tcb.in_progress, tcb._start_trading)
        self.assertEqual(tcb.in_progress_step, 4)

    def test__start_trading_should_reset_with_wrong_input_when_step_3(self):
        tcb = TelegramController()
        tcb.in_progress_step = 3
        tcb._send_text_message = MagicMock()
        tcb._start_trading("NH bank")
        wrong_message = "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요"
        tcb._send_text_message.assert_called_once_with(wrong_message, tcb.main_keyboard)
        self.assertIsNone(tcb.trader)
        self.assertIsNone(tcb.data_provider)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    def test__start_trading_should_call_next_setup_message_correctly_when_step_4(self):
        tcb = TelegramController()
        tcb.in_progress_step = 4
        tcb._send_text_message = MagicMock()
        tcb.trader = MagicMock()
        tcb.currency = "mango"
        tcb.trader.NAME = "mango trader"
        tcb.strategy = MagicMock()
        tcb.strategy.NAME = "mango strategy"
        tcb.budget = 500
        tcb._start_trading("SMA")

        tcb._send_text_message.assert_called_once_with(
            f"화폐: mango\n전략: {StrategySma0.NAME}\n거래소: mango trader\n예산: 500\n자동 거래를 시작할까요?",
            tcb.setup_list[4]["keyboard"],
        )
        self.assertIsNotNone(tcb.strategy)
        self.assertEqual(tcb.in_progress, tcb._start_trading)
        self.assertEqual(tcb.in_progress_step, 5)

    def test__start_trading_should_reset_with_wrong_input_when_step_4(self):
        tcb = TelegramController()
        tcb.in_progress_step = 4
        tcb._send_text_message = MagicMock()
        tcb._start_trading("smtm")
        wrong_message = "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요"
        tcb._send_text_message.assert_called_once_with(wrong_message, tcb.main_keyboard)
        self.assertIsNone(tcb.strategy)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    @patch("smtm.Operator.start")
    @patch("smtm.Operator.initialize")
    def test__start_trading_should_call_next_setup_message_correctly_when_step_5(
        self, mock_start, mock_initialize
    ):
        tcb = TelegramController()
        tcb.in_progress_step = 5
        tcb._send_text_message = MagicMock()
        tcb.strategy = MagicMock()
        tcb.trader = MagicMock()
        tcb._start_trading("y")

        tcb._send_text_message.assert_called_once_with(ANY, tcb.main_keyboard)
        self.assertIsNotNone(tcb.operator)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    def test__start_trading_should_reset_with_wrong_input_when_step_5(self):
        tcb = TelegramController()
        tcb.in_progress_step = 5
        tcb._send_text_message = MagicMock()
        tcb._start_trading("n")
        wrong_message = "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요"
        tcb._send_text_message.assert_called_once_with(wrong_message, tcb.main_keyboard)
        self.assertIsNone(tcb.operator)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    def test__query_score_should_call_send_error_message_when_not_running(self):
        tcb = TelegramController()
        tcb._send_text_message = MagicMock()
        tcb._query_score("1")

        tcb._send_text_message.assert_called_once_with("자동 거래 운영중이 아닙니다", tcb.main_keyboard)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    def test__query_score_should_call_next_setup_message_correctly_when_step_0(self):
        tcb = TelegramController()
        tcb.in_progress_step = 0
        tcb.operator = MagicMock()
        tcb._send_text_message = MagicMock()
        tcb._query_score("1")

        tcb._send_text_message.assert_called_once_with(
            tcb.score_query_list[0]["guide"], tcb.score_query_list[0]["keyboard"]
        )
        self.assertEqual(tcb.in_progress, tcb._query_score)
        self.assertEqual(tcb.in_progress_step, 1)

    def test__query_score_should_call_next_setup_message_correctly_when_step_1(self):
        tcb = TelegramController()
        tcb.in_progress_step = 1
        tcb.operator = MagicMock()
        tcb._send_text_message = MagicMock()
        tcb._send_image_message = MagicMock()
        tcb._query_score("1")

        tcb.operator.get_score.assert_called_once()
        tcb._send_text_message.assert_called_once_with("조회중입니다", tcb.main_keyboard)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)
        self.assertEqual(tcb.operator.get_score.call_args[0][1], (60 * 6, -1))
        callback = tcb.operator.get_score.call_args[0][0]
        callback(None)
        tcb._send_text_message.assert_called_with("수익률 조회중 문제가 발생하였습니다.", tcb.main_keyboard)
        callback((100, 200, 0.5, 0.9, "test.jpg", 0, 0, 0, ("12-01", "12-05", "12-08")))
        tcb._send_text_message.assert_called_with(
            "12-05 - 12-08\n자산 100 -> 200\n구간 수익률 100.0\n12-01~\n누적 수익률 0.5\n비교 수익률 0.9\n",
            tcb.main_keyboard,
        )
        tcb._send_image_message.assert_called_with("test.jpg")

    def test__query_score_should_reset_with_wrong_input_when_step_1(self):
        tcb = TelegramController()
        tcb.in_progress_step = 1
        tcb.operator = MagicMock()
        tcb._send_text_message = MagicMock()
        tcb._query_score("7")
        wrong_message = "다시 시작해 주세요"
        tcb._send_text_message.assert_called_once_with(wrong_message, tcb.main_keyboard)
        self.assertEqual(tcb.in_progress, None)
        self.assertEqual(tcb.in_progress_step, 0)

    def test_on_exception_should_call__send_text_message(self):
        tcb = TelegramController()
        tcb._send_text_message = MagicMock()
        tcb.main_keyboard = "banana"
        tcb.on_exception("mango")
        tcb._send_text_message.assert_called_once_with(
            "트레이딩 중 문제가 발생하여 트레이딩이 중단되었습니다! mango", "banana"
        )
