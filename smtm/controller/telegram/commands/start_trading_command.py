"""
Start Trading Command Implementation
거래 시작 명령어 구현

Handles the start trading command using multi-step setup process.
다단계 설정 프로세스를 사용하여 거래 시작 명령어를 처리합니다.
"""

from typing import Any
from .base_command import TelegramCommand


class StartTradingCommand(TelegramCommand):
    """
    Start Trading Command Class
    거래 시작 명령어를 처리하는 클래스

    Handles the start trading command with multi-step setup process.
    다단계 설정 프로세스로 거래 시작 명령어를 처리합니다.
    """

    def __init__(self, controller: Any):
        """
        Initialize Start Trading Command
        거래 시작 명령어 초기화

        Args:
            controller: Telegram controller instance / 텔레그램 컨트롤러 인스턴스
        """
        super().__init__(controller)
        self.in_progress_step = 0
        self.in_progress = None

    def execute(self, command: str) -> None:
        """
        Execute start trading command
        거래 시작 명령어를 실행합니다.

        Args:
            command: Command string / 명령어 문자열
        """
        if self.in_progress is not None:
            self.in_progress(command)
            return

        self._start_trading_process(command)

    def can_handle(self, command: str) -> bool:
        """
        Check if this is a start trading command or part of the setup process
        거래 시작 명령어이거나 설정 프로세스의 일부인지 확인합니다.

        Args:
            command: Command string to check / 확인할 명령어 문자열

        Returns:
            True if this is a start trading command or part of setup process, False otherwise
            거래 시작 명령어이거나 설정 프로세스의 일부이면 True, 그렇지 않으면 False
        """
        # If setup is in progress, handle any command as part of the setup process
        # 설정이 진행 중이면 모든 명령어를 설정 프로세스의 일부로 처리
        if self.in_progress is not None:
            return True
            
        # Check if this is an initial start command
        # 초기 시작 명령어인지 확인
        start_commands = [self.controller.ui_manager.msg["COMMAND_C_1"], "1"]
        return command in start_commands

    def _start_trading_process(self, command: str) -> None:
        """
        Start trading setup process
        거래 시작 프로세스를 시작합니다.

        Args:
            command: Command string from user / 사용자로부터 받은 명령어 문자열
        """
        not_ok = True
        message = ""

        if self.in_progress_step == 0:
            not_ok = False
        elif self.in_progress_step == 1:
            # Budget setting / 예산 설정
            is_valid, budget = self.controller.setup_manager.validate_budget(command)
            if is_valid:
                self.controller.setup_manager.set_budget(budget)
                not_ok = False
        elif self.in_progress_step == 2:
            # Currency setting / 화폐 설정
            is_valid, currency = self.controller.setup_manager.validate_currency(
                command
            )
            if is_valid:
                self.controller.setup_manager.set_currency(currency)
                not_ok = False
        elif self.in_progress_step == 3:
            # Data provider setting / 데이터 프로바이더 설정
            is_valid, data_provider = (
                self.controller.setup_manager.validate_data_provider(command)
            )
            if is_valid:
                self.controller.setup_manager.set_data_provider(data_provider)
                not_ok = False
        elif self.in_progress_step == 4:
            # Exchange setting / 거래소 설정
            is_valid, exchange = self.controller.setup_manager.validate_exchange(
                command
            )
            if is_valid:
                self.controller.setup_manager.set_trader(exchange)
                not_ok = False
        elif self.in_progress_step == 5:
            # Strategy setting / 전략 설정
            is_valid, strategy = self.controller.setup_manager.validate_strategy(
                command
            )
            if is_valid:
                self.controller.setup_manager.set_strategy(strategy)
                not_ok = False
                # Add setup summary message / 설정 요약 메시지 추가
                summary = self.controller.setup_manager.get_setup_summary()
                message = self.controller.ui_manager.format_trading_summary(
                    summary["currency"],
                    summary["strategy"].NAME,
                    summary["trader"].NAME,
                    summary["budget"],
                )
        elif (
            self.in_progress_step == 6
            and command.upper() in ["1. YES", "1", "Y", "YES"]
            and self.controller._start_operator()
        ):
            # Trading start confirmation and execution / 거래 시작 확인 및 실행
            summary = self.controller.setup_manager.get_setup_summary()
            start_message = self.controller.ui_manager.format_start_message(
                summary["currency"],
                summary["strategy"].NAME,
                summary["trader"].NAME,
                summary["budget"],
                self.controller.config.candle_interval,
            )
            self.controller.message_handler.send_text_message(
                start_message, self.controller.ui_manager.main_keyboard
            )
            self.controller.logger.info(
                f"## START! strategy: {summary['strategy'].NAME}, trader: {summary['trader'].NAME}"
            )
            self.in_progress = None
            self.in_progress_step = 0
            return

        if not_ok or self.in_progress_step >= len(
            self.controller.ui_manager.setup_list
        ):
            self._terminate_start_in_progress()
            return

        # Proceed to next step / 다음 단계로 진행
        setup_message, keyboard = self.controller.ui_manager.get_setup_message(
            self.in_progress_step
        )
        message += setup_message
        self.controller.message_handler.send_text_message(message, keyboard)
        self.in_progress = self._start_trading_process
        self.in_progress_step += 1

    def _terminate_start_in_progress(self) -> None:
        """
        Terminate start trading process
        거래 시작 프로세스를 종료합니다.
        """
        self.in_progress = None
        self.in_progress_step = 0
        self.controller.setup_manager.reset_setup()
        self.controller.operator = None
        self.controller.message_handler.send_text_message(
            self.controller.ui_manager.msg["ERROR_RESTART"],
            self.controller.ui_manager.main_keyboard,
        )
