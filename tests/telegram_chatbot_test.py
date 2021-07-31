import requests
import unittest
from smtm import TelegramChatbot
from unittest.mock import *


class TelegramChatbotTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_main_should_call__start_get_updates_loop(self):
        tcb = TelegramChatbot()
        tcb.terminating = True  # for Test
        tcb._start_get_updates_loop = MagicMock()
        tcb.main()

        tcb._start_get_updates_loop.assert_called_once()

    @patch("threading.Thread")
    def test__start_get_updates_loop_start_thread_correctly(self, mock_thread):
        dummy_thread = MagicMock()
        mock_thread.return_value = dummy_thread
        tcb = TelegramChatbot()
        tcb._handle_message = MagicMock()
        tcb.terminating = True  # for Test
        tcb._start_get_updates_loop()

        dummy_thread.start.assert_called_once()
        self.assertEqual(mock_thread.call_args[1]["name"], "get updates")
        self.assertEqual(mock_thread.call_args[1]["daemon"], True)

    def test__handle_message_call__execute_command_with_correct_commands(self):
        tcb = TelegramChatbot()
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
                                "id": 1819645704,
                                "is_bot": False,
                                "first_name": "msaltnet",
                                "language_code": "ko",
                            },
                            "chat": {"id": 1819645704, "first_name": "msaltnet", "type": "private"},
                            "date": 1627694419,
                            "text": "3",
                        },
                    },
                    {
                        "update_id": 402107589,
                        "message": {
                            "message_id": 12,
                            "from": {
                                "id": 1819645704,
                                "is_bot": False,
                                "first_name": "msaltnet",
                                "language_code": "ko",
                            },
                            "chat": {"id": 1819645704, "first_name": "msaltnet", "type": "private"},
                            "date": 1627694420,
                            "text": "4",
                        },
                    },
                    {
                        "update_id": 402107590,
                        "message": {
                            "message_id": 13,
                            "from": {
                                "id": 1819645704,
                                "is_bot": False,
                                "first_name": "msaltnet",
                                "language_code": "ko",
                            },
                            "chat": {"id": 1819645704, "first_name": "msaltnet", "type": "private"},
                            "date": 1627694420,
                            "text": "5",
                        },
                    },
                ],
            }
        )
        tcb._handle_message()

        tcb._execute_command.assert_called_once_with(["3", "4", "5"])

    @patch("requests.get")
    def test__get_updates_call_getUpdates_api_correctly(self, mock_get):
        tcb = TelegramChatbot()
        expected_response = {
            "ok": True,
            "result": [
                {
                    "update_id": 402107581,
                    "message": {
                        "message_id": 3,
                        "from": {
                            "id": 1819645704,
                            "is_bot": False,
                            "first_name": "msaltnet",
                            "language_code": "ko",
                        },
                        "chat": {"id": 1819645704, "first_name": "msaltnet", "type": "private"},
                        "date": 1627616560,
                        "text": "hello~",
                    },
                }
            ],
        }
        dummy_response = MagicMock()
        dummy_response.json.return_value = expected_response
        mock_get.return_value = dummy_response
        updates = tcb._get_updates()
        self.assertEqual(updates, expected_response)
        self.assertEqual(mock_get.call_args[0][0].find("https://api.telegram.org/"), 0)

    @patch("requests.get")
    def test__get_updates_return_None_when_receive_invalid_data(self, mock_get):
        tcb = TelegramChatbot()
        dummy_response = MagicMock()
        dummy_response.json.side_effect = ValueError()
        mock_get.return_value = dummy_response

        updates = tcb._get_updates()
        self.assertEqual(updates, None)

    @patch("requests.get")
    def test__get_updates_return_None_when_receive_response_error(self, mock_get):
        tcb = TelegramChatbot()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            "HTTPError dummy exception"
        )
        mock_get.return_value = dummy_response

        updates = tcb._get_updates()
        self.assertEqual(updates, None)

    @patch("requests.get")
    def test__get_updates_return_None_when_connection_fail(self, mock_get):
        tcb = TelegramChatbot()
        dummy_response = MagicMock()
        dummy_response.json.return_value = [{"market": "apple"}, {"market": "banana"}]
        dummy_response.raise_for_status.side_effect = requests.exceptions.RequestException(
            "RequestException dummy exception"
        )
        mock_get.return_value = dummy_response

        updates = tcb._get_updates()
        self.assertEqual(updates, None)
