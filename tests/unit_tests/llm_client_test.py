import unittest
from unittest.mock import *
from smtm.llm.llm_client import LlmClient, LlmResponse, ToolCall


class LlmResponseTests(unittest.TestCase):
    def test_LlmResponse_should_store_attributes(self):
        tool_call = ToolCall(id="tc_1", name="get_market_data", arguments={"currency": "BTC"})
        response = LlmResponse(
            text="BTC 매수를 추천합니다",
            tool_calls=[tool_call],
            stop_reason="end_turn",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        self.assertEqual(response.text, "BTC 매수를 추천합니다")
        self.assertEqual(len(response.tool_calls), 1)
        self.assertEqual(response.tool_calls[0].name, "get_market_data")
        self.assertEqual(response.stop_reason, "end_turn")
        self.assertEqual(response.usage["input_tokens"], 100)

    def test_ToolCall_should_store_attributes(self):
        tc = ToolCall(id="tc_1", name="execute_trade", arguments={"action": "buy"})
        self.assertEqual(tc.id, "tc_1")
        self.assertEqual(tc.name, "execute_trade")
        self.assertEqual(tc.arguments["action"], "buy")

    def test_LlmResponse_has_tool_calls_returns_true_when_tool_calls_exist(self):
        tc = ToolCall(id="tc_1", name="test", arguments={})
        response = LlmResponse(text="", tool_calls=[tc], stop_reason="tool_use", usage={})
        self.assertTrue(response.has_tool_calls)

    def test_LlmResponse_has_tool_calls_returns_false_when_empty(self):
        response = LlmResponse(text="hello", tool_calls=[], stop_reason="end_turn", usage={})
        self.assertFalse(response.has_tool_calls)

    def test_LlmClient_cannot_be_instantiated(self):
        with self.assertRaises(TypeError):
            LlmClient()
