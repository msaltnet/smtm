"""
Query Score Command Implementation
수익률 조회 명령어 구현

Handles the query score command with multi-step process.
다단계 프로세스로 수익률 조회 명령어를 처리합니다.
"""

from typing import Any
from .base_command import TelegramCommand


class QueryScoreCommand(TelegramCommand):
    """
    Query Score Command Class
    수익률 조회 명령어를 처리하는 클래스

    Handles the query score command with multi-step process.
    다단계 프로세스로 수익률 조회 명령어를 처리합니다.
    """

    def __init__(self, controller: Any):
        """
        Initialize Query Score Command
        수익률 조회 명령어 초기화

        Args:
            controller: Telegram controller instance / 텔레그램 컨트롤러 인스턴스
        """
        super().__init__(controller)
        self.in_progress_step = 0
        self.in_progress = None

        # Set score query tick / 수익률 조회 틱 설정
        # candle_interval은 초 단위이므로, 1시간(3600초)을 candle_interval로 나누어 tick 수를 계산
        an_hour_tick = int(3600 / self.controller.config.candle_interval)
        self.score_query_tick = {
            self.controller.ui_manager.msg["PERIOD_1"]: (an_hour_tick * 6, -1),
            self.controller.ui_manager.msg["PERIOD_2"]: (an_hour_tick * 12, -1),
            self.controller.ui_manager.msg["PERIOD_3"]: (an_hour_tick * 24, -1),
            self.controller.ui_manager.msg["PERIOD_4"]: (an_hour_tick * 12, -2),
            self.controller.ui_manager.msg["PERIOD_5"]: (an_hour_tick * 24, -2),
            "1": (an_hour_tick * 6, -1),
            "2": (an_hour_tick * 12, -1),
            "3": (an_hour_tick * 24, -1),
            "4": (an_hour_tick * 12, -2),
            "5": (an_hour_tick * 24, -2),
        }

    def execute(self, command: str) -> None:
        """
        Execute query score command
        수익률 조회 명령어를 실행합니다.

        Args:
            command: Command string / 명령어 문자열
        """
        if self.in_progress is not None:
            self.in_progress(command)
            return

        # Start score query process / 수익률 조회 프로세스 시작
        self._query_score_process(command)

    def can_handle(self, command: str) -> bool:
        """
        Check if this is a query score command or part of the query process
        수익률 조회 명령어이거나 조회 프로세스의 일부인지 확인합니다.

        Args:
            command: Command string to check / 확인할 명령어 문자열

        Returns:
            True if this is a query score command or part of query process, False otherwise
            수익률 조회 명령어이거나 조회 프로세스의 일부이면 True, 그렇지 않으면 False
        """
        # If query is in progress, handle any command as part of the query process
        # 조회가 진행 중이면 모든 명령어를 조회 프로세스의 일부로 처리
        if self.in_progress is not None:
            return True
            
        # Check if this is an initial query score command
        # 초기 수익률 조회 명령어인지 확인
        score_commands = [self.controller.ui_manager.msg["COMMAND_C_4"], "4"]
        return command in score_commands

    def _query_score_process(self, command: str) -> None:
        """
        Execute score query process
        수익률 조회 프로세스를 실행합니다.
        """
        not_ok = True

        if self.controller.operator is None:
            self.controller.message_handler.send_text_message(
                self.controller.ui_manager.msg["INFO_STATUS_READY"],
                self.controller.ui_manager.main_keyboard,
            )
            return

        if self.in_progress_step == 1:
            if command in self.score_query_tick.keys():

                def print_score_and_main_statement(score):
                    if score is None:
                        self.controller.message_handler.send_text_message(
                            self.controller.ui_manager.msg["ERROR_QUERY"],
                            self.controller.ui_manager.main_keyboard,
                        )
                        return

                    score_message = self.controller.ui_manager.format_score_message(
                        score
                    )
                    self.controller.message_handler.send_text_message(
                        score_message, self.controller.ui_manager.main_keyboard
                    )

                    if len(score) > 4 and score[4] is not None:
                        self.controller.message_handler.send_image_message(score[4])

                self.controller.operator.get_score(
                    print_score_and_main_statement, self.score_query_tick[command]
                )
                not_ok = False

        if self.in_progress_step >= len(self.controller.ui_manager.score_query_list):
            self.in_progress = None
            self.in_progress_step = 0
            if not_ok:
                self.controller.message_handler.send_text_message(
                    self.controller.ui_manager.msg["INFO_RESTART_QUERY"],
                    self.controller.ui_manager.main_keyboard,
                )
            else:
                self.controller.message_handler.send_text_message(
                    self.controller.ui_manager.msg["INFO_QUERY_RUNNING"],
                    self.controller.ui_manager.main_keyboard,
                )
            return

        # Proceed to next step / 다음 단계로 진행
        message, keyboard = self.controller.ui_manager.get_score_query_message(
            self.in_progress_step
        )
        self.controller.message_handler.send_text_message(message, keyboard)
        self.in_progress = self._query_score_process
        self.in_progress_step += 1
