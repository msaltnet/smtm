import os
import tempfile
import unittest
from unittest.mock import patch

from smtm.account_store import AccountStore
from smtm.controller.telegram.telegram_controller import (
    BOOT_MESSAGES,
    TelegramController,
)
from smtm.llm.llm_client import LlmClient, LlmResponse
from smtm.profile_store import ProfileStore


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
        # 실제 config/ 디렉토리를 건드리지 않도록 임시 디렉토리를 먼저 만든다
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

        self.patchers = [
            patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                  side_effect=lambda *a, **k: StubDataProvider()),
            patch("smtm.controller.telegram.telegram_controller.ClaudeLlmClient",
                  side_effect=lambda *a, **k: StubLlmClient()),
            patch("smtm.controller.telegram.telegram_controller.TelegramMessageHandler"),
            patch("smtm.controller.telegram.telegram_controller.ProfileStore",
                  side_effect=lambda *a, **k: ProfileStore(
                      dir_path=os.path.join(self.tmp.name, "profiles"))),
            patch("smtm.controller.telegram.telegram_controller.AccountStore",
                  side_effect=lambda *a, **k: AccountStore(
                      dir_path=os.path.join(self.tmp.name, "accounts"))),
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
        self.addCleanup(controller.operator.shutdown)
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


class BootMessageEncodingTests(unittest.TestCase):
    """부팅 콘솔 메시지가 cp949 콘솔에서 깨지지 않는지 검증한다.

    텔레그램이 유일한 시작 경로이므로, 부팅 안내를 콘솔에 출력하다
    UnicodeEncodeError가 나면 제품 전체가 시작에 실패한다.
    pytest는 stdout을 가로채 실제 콘솔 코덱으로 인코딩하지 않으므로
    이 부류의 버그를 놓친다. 그래서 여기서 직접 cp949 인코딩을 확인한다.
    """

    def test_boot_messages_are_cp949_encodable(self):
        for msg in BOOT_MESSAGES:
            # cp949에서 인코딩 불가능한 문자(em-dash 등)가 있으면 여기서 raise
            msg.encode("cp949")

    def test_em_dash_is_not_cp949_encodable(self):
        # 이 가드가 실제로 의미가 있음을 증명한다:
        # em-dash 같은 비-ASCII 문장부호는 cp949로 인코딩되지 않는다.
        with self.assertRaises(UnicodeEncodeError):
            "실제 주문은 전송되지 않습니다 — 주의".encode("cp949")


if __name__ == "__main__":
    unittest.main()
