"""
LLM-powered Telegram Controller
LLM 기반 텔레그램 컨트롤러
"""

import os
import signal
import time
from typing import Optional, Any
from ...config import Config
from ...log_manager import LogManager
from ...llm.system_operator import SystemOperator
from ...llm.claude_llm_client import ClaudeLlmClient
from ...account_store import AccountStore
from ...profile_store import ProfileStore
from .message_handler import TelegramMessageHandler


class TelegramController:
    """LLM 기반 자동 거래 시스템 텔레그램 챗봇 컨트롤러"""

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
    ):
        self.logger = LogManager.get_logger("TelegramController")
        self.message_handler = TelegramMessageHandler(token, chat_id)
        self.operator = None
        self.message_handler.set_message_callback(self._handle_message)

    def main(self, exchange="UPB", currency="BTC", budget=500000) -> None:
        print("##### smtm telegram LLM controller is started #####")

        api_key = os.environ.get("SMTM_LLM_API_KEY", "")
        if not api_key:
            print("SMTM_LLM_API_KEY 환경변수를 설정해주세요")
            return

        llm_client = ClaudeLlmClient(api_key=api_key)
        config = {
            "exchange": exchange,
            "currency": currency,
            "budget": budget,
            "interval": Config.candle_interval,
            "virtual": True,
            "strategy": "BNH",
            "strategy_files": ["sma_crossover.md", "rsi_strategy.md", "buy_and_hold.md"],
        }
        self.operator = SystemOperator(llm_client, config,
                                       profile_store=ProfileStore(),
                                       account_store=AccountStore())
        try:
            self.operator.setup()
        except Exception as err:
            print(str(err))
            return

        print("'start'를 입력하면 default 세션 매매가 시작됩니다")
        print("default 세션은 가상거래입니다 — 실제 주문은 전송되지 않습니다")
        print("실거래는 채팅으로 계좌를 등록한 뒤 세션을 만들어 시작하세요")

        signal.signal(signal.SIGINT, self._terminate)
        signal.signal(signal.SIGTERM, self._terminate)

        self.message_handler.start_polling()

        while not self.message_handler.terminating:
            time.sleep(0.5)

    def _handle_message(self, message: str) -> None:
        self.logger.debug(f"_handle_message: {message}")
        if self.operator is None:
            self.message_handler.send_text_message("시스템이 초기화되지 않았습니다")
            return

        try:
            response = self.operator.chat(message)
            self.message_handler.send_text_message(response)
        except Exception as e:
            self.logger.error(f"Chat error: {e}")
            self.message_handler.send_text_message(f"오류가 발생했습니다: {e}")

    def _terminate(
        self, signum: Optional[int] = None, frame: Optional[Any] = None
    ) -> None:
        if self.operator is not None:
            self.operator.shutdown()
        self.message_handler.stop_polling()
        print("##### smtm telegram controller is terminated #####")
        print("Good Bye~")
