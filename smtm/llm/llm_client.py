from abc import ABCMeta, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class ToolCall:
    """Tool 호출 정보"""
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class LlmResponse:
    """LLM 응답 정규화 객체"""
    text: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    stop_reason: str = "end_turn"
    usage: Dict[str, int] = field(default_factory=dict)

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LlmClient(metaclass=ABCMeta):
    """LLM 벤더 추상화 클라이언트"""

    @abstractmethod
    def create_message(
        self,
        system_prompt: str,
        messages: list,
        tools: list,
    ) -> LlmResponse:
        """LLM에 메시지를 전송하고 응답을 받는다"""
