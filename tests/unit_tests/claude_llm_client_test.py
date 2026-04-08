import unittest
from unittest.mock import *
from smtm.llm.claude_llm_client import ClaudeLlmClient
from smtm.llm.llm_client import LlmResponse, ToolCall


class ClaudeLlmClientTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("smtm.llm.claude_llm_client.anthropic")
        self.mock_anthropic = self.patcher.start()
        self.mock_client = MagicMock()
        self.mock_anthropic.Anthropic.return_value = self.mock_client

    def tearDown(self):
        self.patcher.stop()

    def test_create_message_returns_LlmResponse_with_text(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="분석 결과입니다")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 100
        mock_response.usage.output_tokens = 50
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        response = client.create_message(
            system_prompt="You are a trader",
            messages=[{"role": "user", "content": "분석해줘"}],
            tools=[],
        )

        self.assertIsInstance(response, LlmResponse)
        self.assertEqual(response.text, "분석 결과입니다")
        self.assertEqual(response.stop_reason, "end_turn")
        self.assertFalse(response.has_tool_calls)

    def test_create_message_returns_LlmResponse_with_tool_calls(self):
        mock_tool_use = MagicMock()
        mock_tool_use.type = "tool_use"
        mock_tool_use.id = "toolu_123"
        mock_tool_use.name = "execute_trade"
        mock_tool_use.input = {"action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01}

        mock_response = MagicMock()
        mock_response.content = [mock_tool_use]
        mock_response.stop_reason = "tool_use"
        mock_response.usage.input_tokens = 200
        mock_response.usage.output_tokens = 30
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        response = client.create_message(
            system_prompt="You are a trader",
            messages=[{"role": "user", "content": "BTC 매수해"}],
            tools=[{"name": "execute_trade", "description": "trade", "input_schema": {}}],
        )

        self.assertTrue(response.has_tool_calls)
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "execute_trade")
        self.assertEqual(response.tool_calls[0].arguments["action"], "buy")

    def test_create_message_passes_correct_params_to_api(self):
        mock_response = MagicMock()
        mock_response.content = [MagicMock(type="text", text="ok")]
        mock_response.stop_reason = "end_turn"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 5
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        tools = [{"name": "t1", "description": "d1", "input_schema": {"type": "object"}}]
        client.create_message(
            system_prompt="system",
            messages=[{"role": "user", "content": "hi"}],
            tools=tools,
        )

        self.mock_client.messages.create.assert_called_once()
        call_kwargs = self.mock_client.messages.create.call_args[1]
        self.assertEqual(call_kwargs["model"], "claude-sonnet-4-20250514")
        self.assertEqual(call_kwargs["system"], "system")
        self.assertEqual(call_kwargs["messages"], [{"role": "user", "content": "hi"}])

    def test_create_message_handles_mixed_content(self):
        mock_text = MagicMock(type="text", text="먼저 시장을 확인하겠습니다")
        mock_tool = MagicMock()
        mock_tool.type = "tool_use"
        mock_tool.id = "toolu_456"
        mock_tool.name = "get_market_data"
        mock_tool.input = {"currency": "BTC"}

        mock_response = MagicMock()
        mock_response.content = [mock_text, mock_tool]
        mock_response.stop_reason = "tool_use"
        mock_response.usage.input_tokens = 150
        mock_response.usage.output_tokens = 40
        self.mock_client.messages.create.return_value = mock_response

        client = ClaudeLlmClient(api_key="test-key", model="claude-sonnet-4-20250514")
        response = client.create_message("sys", [{"role": "user", "content": "hi"}], [])

        self.assertEqual(response.text, "먼저 시장을 확인하겠습니다")
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "get_market_data")
