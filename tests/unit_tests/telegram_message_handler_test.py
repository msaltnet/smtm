import threading
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest

from smtm.controller.telegram.message_handler import TelegramMessageHandler


@pytest.mark.parametrize("text, expected", [
    ("- **세션:** `default`\n- **예산:** **500,000원**",
     "- <b>세션:</b> <code>default</code>\n- <b>예산:</b> <b>500,000원</b>"),
    ("가격 < 10 & 수익 > 0", "가격 &lt; 10 &amp; 수익 &gt; 0"),
    ("<b>raw</b> **A&B**", "&lt;b&gt;raw&lt;/b&gt; <b>A&amp;B</b>"),
    ("`**literal** <tag> & value`", "<code>**literal** &lt;tag&gt; &amp; value</code>"),
    ("```python\nprint('**value** < 10 & > 0')\n```",
     "<pre>print('**value** &lt; 10 &amp; &gt; 0')\n</pre>"),
    ("**unclosed `code < &", "**unclosed `code &lt; &amp;"),
    ("plain_text (0.00%) - BTC!", "plain_text (0.00%) - BTC!"),
])
@pytest.mark.parametrize("keyboard", [None, '{"keyboard":[["status & help"]]}'])
@patch("smtm.controller.telegram.message_handler.Worker")
def test_send_text_formats_markdown_as_safe_telegram_html(mock_worker, text, expected, keyboard):
    handler = TelegramMessageHandler(token="test-token", chat_id="1234")

    handler.send_text_message(text, keyboard=keyboard)

    task = mock_worker.return_value.post_task.call_args.args[0]
    query = parse_qs(urlsplit(task["url"]).query)
    assert query["text"] == [expected]
    assert query["parse_mode"] == ["HTML"]
    if keyboard is None:
        assert "reply_markup" not in query
    else:
        assert query["reply_markup"] == [keyboard]
    assert query["chat_id"] == ["1234"]
    with patch.object(handler, "_send_http", return_value={"ok": True}) as send_http:
        task["runnable"](task)
    send_http.assert_called_once_with(task["url"])


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
