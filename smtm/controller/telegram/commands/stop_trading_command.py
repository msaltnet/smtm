"""
Stop Trading Command Implementation
거래 중지 명령어 구현

Handles the stop trading command.
거래 중지 명령어를 처리합니다.
"""

from typing import Any
from .base_command import TelegramCommand


class StopTradingCommand(TelegramCommand):
    """
    Stop Trading Command Class
    거래 중지 명령어를 처리하는 클래스

    Handles the stop trading command.
    거래 중지 명령어를 처리합니다.
    """

    def execute(self, command: str) -> None:
        """
        Execute stop trading command
        거래 중지 명령어를 실행합니다.

        Args:
            command: Command string / 명령어 문자열
        """
        last_report = None
        if self.controller.operator is not None:
            last_report = self.controller.operator.stop()

        # Reset state / 상태 초기화
        self.controller.operator = None
        self.controller.setup_manager.reset_setup()

        # Send stop message / 중지 메시지 전송
        stop_message = self.controller.ui_manager.format_stop_message(last_report)
        self.controller.message_handler.send_text_message(
            stop_message, self.controller.ui_manager.main_keyboard
        )

    def can_handle(self, command: str) -> bool:
        """
        Check if this is a stop trading command
        거래 중지 명령어인지 확인합니다.

        Args:
            command: Command string to check / 확인할 명령어 문자열

        Returns:
            True if this is a stop trading command, False otherwise
            거래 중지 명령어이면 True, 그렇지 않으면 False
        """
        stop_commands = [self.controller.ui_manager.msg["COMMAND_C_2"], "2"]
        return command in stop_commands
