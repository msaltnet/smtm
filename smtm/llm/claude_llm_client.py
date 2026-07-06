import anthropic
from .llm_client import LlmClient, LlmResponse, ToolCall
from ..log_manager import LogManager


class ClaudeLlmClient(LlmClient):
    """Anthropic Claude API 클라이언트"""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", max_tokens: int = 4096):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        kwargs = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system_prompt,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        response = self.client.messages.create(**kwargs)

        text_parts = []
        tool_calls = []
        for block in response.content:
            if block.type == "text":
                text_parts.append(block.text)
            elif block.type == "tool_use":
                tool_calls.append(
                    ToolCall(id=block.id, name=block.name, arguments=block.input)
                )

        return LlmResponse(
            text="".join(text_parts),
            tool_calls=tool_calls,
            stop_reason=response.stop_reason,
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
        )
