from abc import ABCMeta, abstractmethod
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class ToolResult:
    """Tool 실행 결과"""
    success: bool
    data: Any = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        if self.success:
            return self.data if isinstance(self.data, dict) else {"result": self.data}
        return {"error": self.error}


class Tool(metaclass=ABCMeta):
    """Tool 기본 추상 클래스"""

    name: str = ""
    description: str = ""
    input_schema: dict = {}

    @abstractmethod
    def execute(self, arguments: dict) -> ToolResult:
        """Tool 실행"""

    def get_schema(self) -> dict:
        """LLM에 전달할 Tool 스키마 반환"""
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }
