import os
import unittest
from unittest.mock import patch

from smtm.controller.telegram.telegram_controller import TelegramController
from smtm.llm.llm_client import LlmClient, LlmResponse


class StubDataProvider:
    """실 네트워크 호출 없이 고정 캔들을 반환하는 테스트용 DataProvider"""

    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-12T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


class StubLlmClient(LlmClient):
    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        return LlmResponse(text="ok")


class TelegramControllerSetupTests(unittest.TestCase):
    """main()이 조립하는 SystemOperator의 Tool 등록과 세션 기본값을 검증한다.

    main()은 signal 등록과 무한 폴링 루프를 돌기 때문에 그대로 실행할 수 없다.
    폴링을 즉시 끝내도록 message_handler를 스텁으로 바꾸고, operator만 꺼내 본다.
    """

    def setUp(self):
        self.patchers = [
            patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                  side_effect=lambda *a, **k: StubDataProvider()),
            patch("smtm.controller.telegram.telegram_controller.ClaudeLlmClient",
                  side_effect=lambda *a, **k: StubLlmClient()),
            patch("smtm.controller.telegram.telegram_controller.TelegramMessageHandler"),
            patch.dict(os.environ, {"SMTM_LLM_API_KEY": "test-key"}),
        ]
        for patcher in self.patchers:
            patcher.start()
        for patcher in self.patchers:
            self.addCleanup(patcher.stop)

    def _run_main(self):
        controller = TelegramController(token="t", chat_id="c")
        # start_polling 직후 terminating=True가 되어 while 루프를 즉시 빠져나온다
        controller.message_handler.terminating = True
        with patch("signal.signal"):
            controller.main()
        return controller.operator

    def test_profile_and_session_tools_are_registered(self):
        operator = self._run_main()

        tool_names = set(operator.tool_router.tools.keys())
        self.assertIn("create_profile", tool_names)
        self.assertIn("create_session", tool_names)
        self.assertIn("switch_profile", tool_names)

    def test_default_session_is_virtual(self):
        operator = self._run_main()

        session = operator.default_session()
        self.assertTrue(session.profile["virtual"])


if __name__ == "__main__":
    unittest.main()
