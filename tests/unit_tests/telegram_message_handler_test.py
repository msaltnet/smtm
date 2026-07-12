import threading
import unittest
from unittest.mock import patch

from smtm.controller.telegram.message_handler import TelegramMessageHandler


class TelegramMessageHandlerTokenTests(unittest.TestCase):
    def test_missing_token_raises_value_error(self):
        # 토큰이 없으면 placeholder로 부팅하지 않고 즉시 에러를 낸다
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                TelegramMessageHandler()

    def test_placeholder_token_raises_value_error(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                TelegramMessageHandler(token="telegram_token", chat_id="1234")

    def test_explicit_token_is_accepted(self):
        with patch.dict("os.environ", {}, clear=True):
            handler = TelegramMessageHandler(token="real-token-123", chat_id="1234")

        self.assertEqual(handler.TOKEN, "real-token-123")
        self.assertEqual(handler.CHAT_ID, 1234)
        handler.post_worker.stop()

    def test_token_from_environment_is_accepted(self):
        env = {
            "TELEGRAM_BOT_TOKEN": "env-token-456",
            "TELEGRAM_CHAT_ID": "9876",
        }
        with patch.dict("os.environ", env, clear=True):
            handler = TelegramMessageHandler()

        self.assertEqual(handler.TOKEN, "env-token-456")
        self.assertEqual(handler.CHAT_ID, 9876)
        handler.post_worker.stop()

    def test_no_worker_thread_is_leaked_when_token_is_missing(self):
        before = threading.active_count()

        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                TelegramMessageHandler()

        self.assertEqual(threading.active_count(), before)


if __name__ == "__main__":
    unittest.main()
