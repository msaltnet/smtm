import unittest
from unittest.mock import *
from smtm.llm.llm_operator import LlmOperator, ContextConfig
from smtm.llm.llm_client import LlmResponse, ToolCall
from smtm.llm.tool import ToolResult


class LlmOperatorInitTests(unittest.TestCase):
    def test_init_sets_state_to_ready(self):
        llm_client = MagicMock()
        config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60}
        op = LlmOperator(llm_client, config)
        self.assertEqual(op.state, "ready")

    def test_init_creates_components(self):
        llm_client = MagicMock()
        config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60}
        op = LlmOperator(llm_client, config)
        self.assertIsNotNone(op.tool_router)
        self.assertIsNotNone(op.safety_guard)
        self.assertIsNotNone(op.system_monitor)


class LlmOperatorChatTests(unittest.TestCase):
    def setUp(self):
        self.llm_client = MagicMock()
        self.config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60}
        self.op = LlmOperator(self.llm_client, self.config)

    def test_chat_returns_llm_text_response(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="BTC 시장이 안정적입니다", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        response = self.op.chat("시장 상황 알려줘")
        self.assertEqual(response, "BTC 시장이 안정적입니다")

    def test_chat_handles_tool_use_loop(self):
        tool_response = LlmResponse(
            text="", tool_calls=[ToolCall(id="tc_1", name="get_portfolio", arguments={})],
            stop_reason="tool_use", usage={"input_tokens": 100, "output_tokens": 30},
        )
        final_response = LlmResponse(
            text="현재 잔고는 50만원입니다", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 150, "output_tokens": 40},
        )
        self.llm_client.create_message.side_effect = [tool_response, final_response]

        portfolio_tool = MagicMock()
        portfolio_tool.name = "get_portfolio"
        portfolio_tool.execute.return_value = ToolResult(success=True, data={"balance": 500000})
        self.op.tool_router.register(portfolio_tool)

        response = self.op.chat("잔고 알려줘")
        self.assertEqual(response, "현재 잔고는 50만원입니다")
        self.assertEqual(self.llm_client.create_message.call_count, 2)

    def test_chat_stores_conversation_history(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="안녕하세요", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.chat("안녕")
        self.assertEqual(len(self.op.conversation_history), 2)

    def test_chat_logs_interaction_to_system_monitor(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.chat("test")
        self.assertEqual(len(self.op.system_monitor.llm_interaction_log), 1)

    def test_chat_trims_conversation_history_when_exceeding_max(self):
        self.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.context_config = ContextConfig(max_conversation_turns=3)
        for i in range(5):
            self.op.chat(f"message {i}")
        self.assertLessEqual(len(self.op.conversation_history), 6)


class LlmOperatorTimerTests(unittest.TestCase):
    def setUp(self):
        self.patcher = patch("threading.Timer")
        self.timer_mock_cls = self.patcher.start()
        self.timer_instance = MagicMock()
        self.timer_mock_cls.return_value = self.timer_instance

        self.llm_client = MagicMock()
        self.config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 10}
        self.op = LlmOperator(self.llm_client, self.config)

    def tearDown(self):
        self.patcher.stop()

    def test_start_trading_changes_state_to_running(self):
        self.op.data_provider = MagicMock()
        self.llm_client.create_message.return_value = LlmResponse(
            text="매매를 시작합니다", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.start_trading()
        self.assertEqual(self.op.state, "running")

    def test_stop_trading_changes_state_to_stopped(self):
        self.op.data_provider = MagicMock()
        self.llm_client.create_message.return_value = LlmResponse(
            text="ok", tool_calls=[], stop_reason="end_turn",
            usage={"input_tokens": 10, "output_tokens": 5},
        )
        self.op.start_trading()
        self.op.stop_trading()
        self.assertEqual(self.op.state, "stopped")
