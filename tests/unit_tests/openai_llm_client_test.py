from unittest.mock import patch

from smtm.llm.llm_client import ToolCall
from smtm.llm.openai_llm_client import OpenAILlmClient


@patch("smtm.llm.openai_llm_client.OpenAI")
def test_constructor_uses_api_key_and_default_model(mock_openai):
    client = OpenAILlmClient(api_key="test-key")

    mock_openai.assert_called_once_with(api_key="test-key")
    assert client.model == "gpt-5.6-luna"
    assert client.max_tokens == 4096


def _text_response(text):
    message = type("Message", (), {"content": text, "tool_calls": []})()
    choice = type("Choice", (), {"message": message, "finish_reason": "stop"})()
    usage = type("Usage", (), {"prompt_tokens": 1, "completion_tokens": 1})()
    return type("Response", (), {"choices": [choice], "usage": usage})()


@patch("smtm.llm.openai_llm_client.OpenAI")
def test_create_message_converts_tool_schema_and_response(mock_openai):
    sdk_client = mock_openai.return_value
    function = type("Function", (), {
        "name": "get_market_data",
        "arguments": '{"session": "default"}',
    })()
    tool_call = type("SdkToolCall", (), {"id": "call_1", "function": function})()
    message = type("Message", (), {"content": "조회합니다", "tool_calls": [tool_call]})()
    usage = type("Usage", (), {"prompt_tokens": 12, "completion_tokens": 7})()
    choice = type("Choice", (), {"message": message, "finish_reason": "tool_calls"})()
    sdk_client.chat.completions.create.return_value = type("Response", (), {
        "choices": [choice], "usage": usage,
    })()

    response = OpenAILlmClient("test-key").create_message(
        "system prompt",
        [{"role": "user", "content": "상태 알려줘"}],
        [{"name": "get_market_data", "description": "시장 조회", "input_schema": {"type": "object"}}],
    )

    kwargs = sdk_client.chat.completions.create.call_args.kwargs
    assert kwargs["tools"] == [{"type": "function", "function": {
        "name": "get_market_data", "description": "시장 조회", "parameters": {"type": "object"},
    }}]
    assert response.tool_calls == [ToolCall("call_1", "get_market_data", {"session": "default"})]
    assert response.usage == {"input_tokens": 12, "output_tokens": 7}


@patch("smtm.llm.openai_llm_client.OpenAI")
def test_create_message_converts_forced_tool_choice(mock_openai):
    sdk_client = mock_openai.return_value
    sdk_client.chat.completions.create.return_value = _text_response("ok")

    OpenAILlmClient("test-key").create_message(
        "system", [{"role": "user", "content": "decide"}],
        [{"name": "submit_decision", "description": "", "input_schema": {"type": "object"}}],
        tool_choice={"type": "tool", "name": "submit_decision"},
    )

    assert sdk_client.chat.completions.create.call_args.kwargs["tool_choice"] == {
        "type": "function", "function": {"name": "submit_decision"}
    }
