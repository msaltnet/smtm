"""
Refactored Telegram Controller
리팩터링된 텔레그램 컨트롤러

Combines separated classes using Command Pattern and Single Responsibility Principle.
Command Pattern과 단일 책임 원칙을 적용하여 분할된 클래스들을 조합합니다.
"""

import signal
import time
from typing import Optional, Any
from ...config import Config
from ...log_manager import LogManager
from ...analyzer import Analyzer
from ...operator import Operator
from .message_handler import TelegramMessageHandler
from .ui_manager import TelegramUIManager
from .setup_manager import TradingSetupManager
from .commands import (
    StartTradingCommand,
    StopTradingCommand,
    QueryStateCommand,
    QueryScoreCommand,
    QueryTradingRecordsCommand,
)


class TelegramController:
    """
    Refactored Telegram Trading Bot Controller
    리팩터링된 자동 거래 시스템 텔레그램 챗봇 컨트롤러

    Combines separated classes using Command Pattern and Single Responsibility Principle.
    Command Pattern과 단일 책임 원칙을 적용하여 분할된 클래스들을 조합합니다.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        chat_id: Optional[str] = None,
        demo: bool = False,
    ):
        """
        Initialize Telegram Controller
        텔레그램 컨트롤러 초기화

        Args:
            token: Telegram bot token / 텔레그램 봇 토큰
            chat_id: Telegram chat ID / 텔레그램 채팅 ID
            demo: Whether to run in demo mode / 데모 모드 실행 여부
        """
        self.logger = LogManager.get_logger("TelegramController")
        self.config = Config
        self.is_demo = demo

        # Initialize components
        # 컴포넌트 초기화
        self.message_handler = TelegramMessageHandler(token, chat_id)
        self.ui_manager = TelegramUIManager(Config.language)
        self.setup_manager = TradingSetupManager(demo)

        # Trading related
        # 거래 관련
        self.operator: Optional[Operator] = None

        # Initialize Command Pattern
        # Command Pattern 초기화
        self.commands = [
            StartTradingCommand(self),
            StopTradingCommand(self),
            QueryStateCommand(self),
            QueryScoreCommand(self),
            QueryTradingRecordsCommand(self),
        ]

        # Update UI with available options
        # UI 업데이트
        self._update_ui_with_options()

        # Set message handler callback
        # 메시지 핸들러 설정
        self.message_handler.set_message_callback(self._handle_message)

    def _update_ui_with_options(self) -> None:
        """
        Update UI with available options
        UI에 사용 가능한 옵션들을 업데이트합니다.
        """
        self.ui_manager.update_data_provider_keyboard(
            self.setup_manager.get_data_providers()
        )
        self.ui_manager.update_strategy_keyboard(self.setup_manager.get_strategies())

    def main(self, demo: bool = False) -> None:
        """
        Main execution function
        메인 실행 함수

        Args:
            demo: Whether to run in demo mode / 데모 모드 실행 여부
        """
        print("##### smtm telegram controller is started #####")
        self.is_demo = demo
        if self.is_demo:
            print("$$$ DEMO MODE $$$")

        signal.signal(signal.SIGINT, self._terminate)
        signal.signal(signal.SIGTERM, self._terminate)

        self.message_handler.start_polling()

        while not self.message_handler.terminating:
            time.sleep(0.5)

    def _handle_message(self, command: str) -> None:
        """
        Handle incoming message
        메시지를 처리합니다.

        Args:
            command: Command string from user / 사용자로부터 받은 명령어 문자열
        """
        self.logger.debug(f"_handle_message: {command}")

        # Use Command Pattern to handle commands
        # Command Pattern을 사용하여 명령어 처리
        for cmd in self.commands:
            if cmd.can_handle(command):
                cmd.execute(command)
                return

        # Send guide message for unrecognized commands
        # 처리할 수 없는 명령어인 경우 가이드 메시지 전송
        is_running = self.operator is not None
        message = self.ui_manager.get_guide_message(is_running)
        self.message_handler.send_text_message(message, self.ui_manager.main_keyboard)

    def _start_operator(self) -> bool:
        """
        Start trading operator
        Operator를 시작합니다.

        Returns:
            True if started successfully, False otherwise / 성공적으로 시작되면 True, 그렇지 않으면 False
        """

        def _alert_callback(msg: str) -> None:
            self.alert_callback(msg)

        try:
            setup_summary = self.setup_manager.get_setup_summary()
            self.operator = Operator(alert_callback=_alert_callback)
            self.operator.initialize(
                setup_summary["data_provider"],
                setup_summary["strategy"],
                setup_summary["trader"],
                Analyzer(),
                budget=setup_summary["budget"],
            )
            self.operator.set_interval(Config.candle_interval)
            return self.operator.start()
        except Exception as e:
            self.logger.error(f"Failed to start operator: {e}")
            return False

    def alert_callback(self, msg: str) -> None:
        """
        Handle exception situations
        예외 상황 처리

        Args:
            msg: Alert message / 알림 메시지
        """
        self.message_handler.send_text_message(
            f"Alert: {msg}", self.ui_manager.main_keyboard
        )

    def _terminate(
        self, signum: Optional[int] = None, frame: Optional[Any] = None
    ) -> None:
        """
        Handle termination
        종료 처리

        Args:
            signum: Signal number / 시그널 번호
            frame: Current stack frame / 현재 스택 프레임
        """
        self.message_handler.stop_polling()

        if signum is not None:
            print("Received a termination signal")
        print("##### smtm telegram controller is terminated #####")
        print("Good Bye~")
