"""
Query State Command Implementation
상태 조회 명령어 구현

Handles the query state command.
상태 조회 명령어를 처리합니다.
"""

from typing import Any
from .base_command import TelegramCommand


class QueryStateCommand(TelegramCommand):
    """
    Query State Command Class
    상태 조회 명령어를 처리하는 클래스

    Handles the query state command.
    상태 조회 명령어를 처리합니다.
    """

    def execute(self, command: str) -> None:
        """
        Execute query state command
        상태 조회 명령어를 실행합니다.

        Args:
            command: Command string / 명령어 문자열
        """
        if self.controller.operator is None:
            message = self.controller.ui_manager.msg["INFO_STATUS_READY"]
        else:
            message = self.controller.ui_manager.msg["INFO_STATUS_RUNNING"]

        self.controller.message_handler.send_text_message(message)

    def can_handle(self, command: str) -> bool:
        """
        Check if this is a query state command
        상태 조회 명령어인지 확인합니다.

        Args:
            command: Command string to check / 확인할 명령어 문자열

        Returns:
            True if this is a query state command, False otherwise
            상태 조회 명령어이면 True, 그렇지 않으면 False
        """
        state_commands = [self.controller.ui_manager.msg["COMMAND_C_3"], "3"]
        return command in state_commands
