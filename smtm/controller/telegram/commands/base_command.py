"""
Base Command Interface for Command Pattern
Command Pattern의 기본 인터페이스

Defines the base interface for all Telegram commands.
모든 텔레그램 명령어의 기본 인터페이스를 정의합니다.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class TelegramCommand(ABC):
    """
    Base Telegram Command Interface
    텔레그램 명령어의 기본 인터페이스

    Abstract base class for all Telegram commands using Command Pattern.
    Command Pattern을 사용하는 모든 텔레그램 명령어의 추상 기본 클래스입니다.
    """

    def __init__(self, controller: Any):
        """
        Initialize command with controller
        컨트롤러로 명령어 초기화

        Args:
            controller: Telegram controller instance / 텔레그램 컨트롤러 인스턴스
        """
        self.controller = controller

    @abstractmethod
    def execute(self, command: str) -> None:
        """
        Execute the command
        명령어를 실행합니다.

        Args:
            command: Command string to execute / 실행할 명령어 문자열
        """
        pass

    @abstractmethod
    def can_handle(self, command: str) -> bool:
        """
        Check if this command can handle the given command
        이 명령어가 주어진 명령을 처리할 수 있는지 확인합니다.

        Args:
            command: Command string to check / 확인할 명령어 문자열

        Returns:
            True if this command can handle the given command, False otherwise
            이 명령어가 주어진 명령을 처리할 수 있으면 True, 그렇지 않으면 False
        """
        pass
