"""
Query Trading Records Command Implementation
거래내역 조회 명령어 구현

Handles the query trading records command.
거래내역 조회 명령어를 처리합니다.
"""

from typing import Any
from .base_command import TelegramCommand


class QueryTradingRecordsCommand(TelegramCommand):
    """
    Query Trading Records Command Class
    거래내역 조회 명령어를 처리하는 클래스

    Handles the query trading records command.
    거래내역 조회 명령어를 처리합니다.
    """

    def execute(self, command: str) -> None:
        """
        Execute query trading records command
        거래내역 조회 명령어를 실행합니다.

        Args:
            command: Command string / 명령어 문자열
        """
        if self.controller.operator is None:
            self.controller.message_handler.send_text_message(
                self.controller.ui_manager.msg["INFO_STATUS_READY"],
                self.controller.ui_manager.main_keyboard,
            )
            return

        results = self.controller.operator.get_trading_results()
        message = self.controller.ui_manager.format_trading_records(results)
        self.controller.message_handler.send_text_message(
            message, self.controller.ui_manager.main_keyboard
        )

    def can_handle(self, command: str) -> bool:
        """
        Check if this is a query trading records command
        거래내역 조회 명령어인지 확인합니다.

        Args:
            command: Command string to check / 확인할 명령어 문자열

        Returns:
            True if this is a query trading records command, False otherwise
            거래내역 조회 명령어이면 True, 그렇지 않으면 False
        """
        records_commands = [self.controller.ui_manager.msg["COMMAND_C_5"], "5"]
        return command in records_commands
