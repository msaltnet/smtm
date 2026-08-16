import json

from openai import OpenAI

from ..log_manager import LogManager
from .llm_client import LlmClient, LlmResponse, ToolCall


class OpenAILlmClient(LlmClient):
    """OpenAI Chat Completions API client."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-5.6-luna",
        max_tokens: int = 4096,
    ):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    @staticmethod
    def _convert_messages(messages):
        converted = []
        for message in messages:
            content = message["content"]
            if isinstance(content, str):
                converted.append({"role": message["role"], "content": content})
                continue

            text_parts, tool_calls, tool_results = [], [], []
            for block in content:
                if block["type"] == "text":
                    text_parts.append(block["text"])
                elif block["type"] == "tool_use":
                    tool_calls.append({
                        "id": block["id"],
                        "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block["input"], ensure_ascii=False),
                        },
                    })
                elif block["type"] == "tool_result":
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": block["tool_use_id"],
                        "content": block["content"],
                    })
                else:
                    raise ValueError(f"Unsupported message block type: {block['type']}")

            if tool_calls:
                converted.append({
                    "role": "assistant",
                    "content": "".join(text_parts) or None,
                    "tool_calls": tool_calls,
                })
            elif text_parts:
                converted.append({"role": message["role"], "content": "".join(text_parts)})
            converted.extend(tool_results)

        return converted

    @staticmethod
    def _convert_tools(tools):
        return [{"type": "function", "function": {
            "name": tool["name"],
            "description": tool.get("description", ""),
            "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
        }} for tool in tools]

    @staticmethod
    def _convert_tool_choice(tool_choice):
        if not tool_choice:
            return None
        if tool_choice.get("type") != "tool" or not tool_choice.get("name"):
            raise ValueError("Unsupported tool_choice format")
        return {"type": "function", "function": {"name": tool_choice["name"]}}

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        kwargs = {
            "model": self.model,
            "max_completion_tokens": self.max_tokens,
            "messages": [{"role": "system", "content": system_prompt}] + self._convert_messages(messages),
        }
        if tools:
            kwargs["tools"] = self._convert_tools(tools)
        converted_choice = self._convert_tool_choice(tool_choice)
        if converted_choice:
            kwargs["tool_choice"] = converted_choice

        response = self.client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        tool_calls = []
        for call in choice.message.tool_calls or []:
            try:
                arguments = json.loads(call.function.arguments)
            except json.JSONDecodeError as err:
                raise ValueError(
                    f"Invalid OpenAI tool arguments for {call.function.name}"
                ) from err
            tool_calls.append(ToolCall(call.id, call.function.name, arguments))

        usage = response.usage
        return LlmResponse(
            text=choice.message.content or "",
            tool_calls=tool_calls,
            stop_reason=choice.finish_reason or "end_turn",
            usage={
                "input_tokens": getattr(usage, "prompt_tokens", 0) or 0,
                "output_tokens": getattr(usage, "completion_tokens", 0) or 0,
            },
        )
