# OpenAI LLM Support Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add OpenAI API support to the Telegram trading agent while retaining Claude as the default provider.

**Architecture:** Keep `SystemOperator` and the existing `LlmClient` contract unchanged. Add `OpenAILlmClient` to translate the application's message and tool history into OpenAI Chat Completions function-calling requests, then normalize responses back to `LlmResponse`. Select the adapter from environment variables in `TelegramController`.

**Tech Stack:** Python 3.9+, OpenAI Python SDK, Anthropic SDK, unittest/pytest, python-dotenv.

---

## File structure

| File | Responsibility |
|---|---|
| `requirements.txt` | Declare the OpenAI Python SDK. |
| `smtm/llm/openai_llm_client.py` | Convert requests, invoke Chat Completions, normalize output. |
| `smtm/llm/__init__.py`, `smtm/__init__.py` | Re-export `OpenAILlmClient`. |
| `smtm/controller/telegram/telegram_controller.py` | Select provider and report safe configuration errors. |
| `tests/unit_tests/openai_llm_client_test.py` | Mocked OpenAI request/response conversion tests. |
| `tests/unit_tests/telegram_controller_test.py` | Provider selection and key-validation tests. |
| `README*.md`, `docs/public/*.md` | User-facing provider configuration. |

### Task 1: Add the OpenAI client and SDK dependency

**Files:**

- Modify: `requirements.txt`
- Create: `smtm/llm/openai_llm_client.py`
- Create: `tests/unit_tests/openai_llm_client_test.py`

- [ ] **Step 1: Write the failing constructor test**

```python
import pytest
from unittest.mock import patch

from smtm.llm.llm_client import ToolCall
from smtm.llm.openai_llm_client import OpenAILlmClient


def _text_response(text):
    message = type("Message", (), {"content": text, "tool_calls": []})()
    choice = type("Choice", (), {"message": message, "finish_reason": "stop"})()
    usage = type("Usage", (), {"prompt_tokens": 1, "completion_tokens": 1})()
    return type("Response", (), {"choices": [choice], "usage": usage})()


@patch("smtm.llm.openai_llm_client.OpenAI")
def test_constructor_uses_api_key_and_default_model(mock_openai):
    client = OpenAILlmClient(api_key="test-key")

    mock_openai.assert_called_once_with(api_key="test-key")
    assert client.model == "gpt-5.6-luna"
    assert client.max_tokens == 4096
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit_tests/openai_llm_client_test.py -q`

Expected: collection fails because `openai_llm_client` does not exist.

- [ ] **Step 3: Add the minimal adapter**

Append `openai` to `requirements.txt`, then create:

```python
import json

from openai import OpenAI

from .llm_client import LlmClient, LlmResponse, ToolCall
from ..log_manager import LogManager


class OpenAILlmClient(LlmClient):
    """OpenAI Chat Completions API client."""

    def __init__(self, api_key: str, model: str = "gpt-5.6-luna", max_tokens: int = 4096):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.client = OpenAI(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        raise NotImplementedError
```

- [ ] **Step 4: Verify the constructor test passes**

Run: `python -m pytest tests/unit_tests/openai_llm_client_test.py::test_constructor_uses_api_key_and_default_model -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add requirements.txt smtm/llm/openai_llm_client.py tests/unit_tests/openai_llm_client_test.py
git commit -m "feat: add OpenAI LLM client shell"
```

### Task 2: Convert tools, calls, and usage into the existing contract

**Files:**

- Modify: `smtm/llm/openai_llm_client.py`
- Modify: `tests/unit_tests/openai_llm_client_test.py`

- [ ] **Step 1: Write failing tool-call and tool-choice tests**

```python
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
```

```python
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
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit_tests/openai_llm_client_test.py -q`

Expected: FAIL because `create_message` raises `NotImplementedError`.

- [ ] **Step 3: Implement conversions and response normalization**

```python
    @staticmethod
    def _convert_messages(messages):
        return [{"role": message["role"], "content": message["content"]} for message in messages]

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
                raise ValueError(f"Invalid OpenAI tool arguments for {call.function.name}") from err
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
```

- [ ] **Step 4: Verify the adapter tests pass**

Run: `python -m pytest tests/unit_tests/openai_llm_client_test.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add smtm/llm/openai_llm_client.py tests/unit_tests/openai_llm_client_test.py
git commit -m "feat: normalize OpenAI tool responses"
```

### Task 3: Convert the existing multi-turn tool history

**Files:**

- Modify: `smtm/llm/openai_llm_client.py`
- Modify: `tests/unit_tests/openai_llm_client_test.py`

- [ ] **Step 1: Write the failing conversation-history test**

```python
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
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/unit_tests/openai_llm_client_test.py::test_convert_messages_preserves_assistant_calls_and_tool_results -q`

Expected: FAIL because the initial converter only supports string message content.

- [ ] **Step 3: Add the message-history converter**

```python
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
                        "id": block["id"], "type": "function",
                        "function": {
                            "name": block["name"],
                            "arguments": json.dumps(block["input"], ensure_ascii=False),
                        },
                    })
                elif block["type"] == "tool_result":
                    tool_results.append({
                        "role": "tool", "tool_call_id": block["tool_use_id"],
                        "content": block["content"],
                    })
                else:
                    raise ValueError(f"Unsupported message block type: {block['type']}")
            if tool_calls:
                converted.append({
                    "role": "assistant", "content": "".join(text_parts) or None,
                    "tool_calls": tool_calls,
                })
            elif text_parts:
                converted.append({"role": message["role"], "content": "".join(text_parts)})
            converted.extend(tool_results)
        return converted
```

- [ ] **Step 4: Run all adapter tests**

Run: `python -m pytest tests/unit_tests/openai_llm_client_test.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add smtm/llm/openai_llm_client.py tests/unit_tests/openai_llm_client_test.py
git commit -m "feat: preserve OpenAI tool conversation history"
```

### Task 4: Select a provider safely at controller startup

**Files:**

- Modify: `smtm/controller/telegram/telegram_controller.py`
- Modify: `smtm/llm/__init__.py`
- Modify: `smtm/__init__.py`
- Modify: `tests/unit_tests/telegram_controller_test.py`

- [ ] **Step 1: Write failing provider-factory tests**

```python
import pytest

from smtm.controller.telegram.telegram_controller import create_llm_client_from_env


@patch("smtm.controller.telegram.telegram_controller.ClaudeLlmClient")
def test_provider_defaults_to_claude(mock_claude):
    with patch.dict(os.environ, {"SMTM_LLM_API_KEY": "claude-key"}, clear=True):
        create_llm_client_from_env()
    mock_claude.assert_called_once_with(api_key="claude-key")


@patch("smtm.controller.telegram.telegram_controller.OpenAILlmClient")
def test_openai_provider_uses_key_and_optional_model(mock_openai):
    with patch.dict(os.environ, {
        "SMTM_LLM_PROVIDER": "openai",
        "OPENAI_API_KEY": "openai-key",
        "SMTM_OPENAI_MODEL": "gpt-5.6-terra",
    }, clear=True):
        create_llm_client_from_env()
    mock_openai.assert_called_once_with(api_key="openai-key", model="gpt-5.6-terra")


def test_openai_provider_rejects_missing_key():
    with patch.dict(os.environ, {"SMTM_LLM_PROVIDER": "openai"}, clear=True):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            create_llm_client_from_env()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/unit_tests/telegram_controller_test.py -q`

Expected: FAIL because `create_llm_client_from_env` does not exist.

- [ ] **Step 3: Implement the provider factory**

```python
from ...llm.openai_llm_client import OpenAILlmClient


def create_llm_client_from_env():
    provider = os.environ.get("SMTM_LLM_PROVIDER", "claude").strip().lower()
    if provider == "claude":
        api_key = os.environ.get("SMTM_LLM_API_KEY", "")
        if not api_key:
            raise ValueError("SMTM_LLM_API_KEY 환경변수를 설정해주세요")
        return ClaudeLlmClient(api_key=api_key)
    if provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY", "")
        if not api_key:
            raise ValueError("OPENAI_API_KEY 환경변수를 설정해주세요")
        return OpenAILlmClient(
            api_key=api_key,
            model=os.environ.get("SMTM_OPENAI_MODEL", "gpt-5.6-luna"),
        )
    raise ValueError("SMTM_LLM_PROVIDER는 claude 또는 openai여야 합니다")
```

Replace the direct Claude construction in `TelegramController.main` with:

```python
        try:
            llm_client = create_llm_client_from_env()
        except ValueError as err:
            print(str(err))
            return
```

Add `from .openai_llm_client import OpenAILlmClient` to `smtm/llm/__init__.py` and `from .llm.openai_llm_client import OpenAILlmClient` to `smtm/__init__.py`.

- [ ] **Step 4: Verify controller and Claude regression tests**

Run: `python -m pytest tests/unit_tests/telegram_controller_test.py tests/unit_tests/claude_llm_client_test.py -q`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add smtm/controller/telegram/telegram_controller.py smtm/llm/__init__.py smtm/__init__.py tests/unit_tests/telegram_controller_test.py
git commit -m "feat: select Claude or OpenAI LLM provider"
```

### Task 5: Document both providers and verify no secrets are staged

**Files:**

- Modify: `README.md`
- Modify: `README-ko-kr.md`
- Modify: `docs/public/overview.md`
- Modify: `docs/public/user-guide.md`
- Modify: `docs/public/faq.md`
- Modify: `docs/public/architecture.md`

- [ ] **Step 1: Add the OpenAI environment-variable example**

```env
# OpenAI 사용
SMTM_LLM_PROVIDER=openai
OPENAI_API_KEY=sk-...
# 선택 사항. 기본값은 gpt-5.6-luna
SMTM_OPENAI_MODEL=gpt-5.6-luna
```

State that `SMTM_LLM_PROVIDER` defaults to `claude`, only the selected provider's key is required, and API keys must never be sent through Telegram.

- [ ] **Step 2: Correct provider claims in public docs**

Replace every claim that Claude is the only implemented provider with “Claude and OpenAI are supported through `LlmClient` adapters.” State that an OpenAI account must have access to the configured model.

- [ ] **Step 3: Check documentation consistency**

Run: `rg -n "Claude 하나|Claude only|currently implemented vendor" README.md README-ko-kr.md docs/public`

Expected: no inaccurate claim that Claude is the only supported provider.

- [ ] **Step 4: Run all offline regression tests**

Run: `python -m pytest tests/unit_tests/claude_llm_client_test.py tests/unit_tests/openai_llm_client_test.py tests/unit_tests/telegram_controller_test.py tests/e2e_tests/ -q`

Expected: PASS with all OpenAI SDK calls mocked.

- [ ] **Step 5: Verify import, CLI, and secret safety**

Run: `python -c "from smtm import OpenAILlmClient; print(OpenAILlmClient.__name__)"`

Expected: `OpenAILlmClient`.

Run: `python -m smtm --version`

Expected: `smtm version: 2.0.0`.

Run: `git status --short`

Expected: no `.env` file is staged or committed.

- [ ] **Step 6: Commit**

```bash
git add README.md README-ko-kr.md docs/public/overview.md docs/public/user-guide.md docs/public/faq.md docs/public/architecture.md
git commit -m "docs: explain OpenAI LLM configuration"
```
