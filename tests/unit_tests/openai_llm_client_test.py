from unittest.mock import patch

import pytest

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
    assert kwargs["reasoning_effort"] == "none"
    assert response.tool_calls == [ToolCall("call_1", "get_market_data", {"session": "default"})]
    assert response.usage == {"input_tokens": 12, "output_tokens": 7}


@pytest.mark.parametrize("model", ["gpt-5.6-luna", "gpt-5.6-terra"])
@patch("smtm.llm.openai_llm_client.OpenAI")
def test_create_message_converts_forced_tool_choice(mock_openai, model):
    sdk_client = mock_openai.return_value
    sdk_client.chat.completions.create.return_value = _text_response("ok")

    OpenAILlmClient("test-key", model=model).create_message(
        "system", [{"role": "user", "content": "decide"}],
        [{"name": "submit_decision", "description": "", "input_schema": {"type": "object"}}],
        tool_choice={"type": "tool", "name": "submit_decision"},
    )

    assert sdk_client.chat.completions.create.call_args.kwargs["tool_choice"] == {
        "type": "function", "function": {"name": "submit_decision"}
    }
    assert sdk_client.chat.completions.create.call_args.kwargs["reasoning_effort"] == "none"


@pytest.mark.parametrize("model, tools, expected_effort", [
    ("gpt-5.6-luna", [{"name": "get_status"}], "none"),
    ("gpt-5.6-luna-2026-09-01", [{"name": "get_status"}], "none"),
    ("gpt-5.6-luna", [], None),
    ("gpt-5.6-terra", [{"name": "get_status"}], "none"),
    ("gpt-5.6-terra-2026-09-01", [{"name": "get_status"}], "none"),
    ("gpt-5.6-terra", [], None),
    ("gpt-5.6-terrain", [{"name": "get_status"}], None),
    ("gpt-4o", [{"name": "get_status"}], None),
    ("gpt-5.6-sol", [{"name": "get_status"}], None),
    ("gpt-5.6-lunatic", [{"name": "get_status"}], None),
])
@patch("smtm.llm.openai_llm_client.OpenAI")
def test_reasoning_effort_is_scoped_to_luna_and_terra_tool_requests(
    mock_openai, model, tools, expected_effort
):
    sdk_client = mock_openai.return_value
    sdk_client.chat.completions.create.return_value = _text_response("ok")

    OpenAILlmClient("test-key", model=model).create_message(
        "system", [{"role": "user", "content": "status"}], tools,
    )

    kwargs = sdk_client.chat.completions.create.call_args.kwargs
    if expected_effort is None:
        assert "reasoning_effort" not in kwargs
    else:
        assert kwargs["reasoning_effort"] == expected_effort


def test_convert_messages_preserves_assistant_calls_and_tool_results():
    messages = [
        {"role": "assistant", "content": [
            {"type": "text", "text": "확인하겠습니다"},
            {"type": "tool_use", "id": "call_1", "name": "get_status", "input": {}},
        ]},
        {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "call_1", "content": "{'ok': True}"},
        ]},
    ]

    assert OpenAILlmClient._convert_messages(messages) == [
        {"role": "assistant", "content": "확인하겠습니다", "tool_calls": [{
            "id": "call_1", "type": "function",
            "function": {"name": "get_status", "arguments": "{}"},
        }]},
        {"role": "tool", "tool_call_id": "call_1", "content": "{'ok': True}"},
    ]
