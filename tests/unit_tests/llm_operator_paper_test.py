import unittest
from unittest.mock import MagicMock

from smtm.llm.llm_client import LlmResponse
from smtm.llm.llm_client import ToolCall
from smtm.llm.llm_operator import LlmOperator
from smtm.llm.tool import ToolResult


class LlmOperatorPaperQuoteSyncTest(unittest.TestCase):
    def setUp(self):
        self.llm = MagicMock()
        self.llm.create_message.return_value = LlmResponse(
            text="ok",
            tool_calls=[],
            stop_reason="end_turn",
            usage={"input_tokens": 1, "output_tokens": 1},
        )
        self.op = LlmOperator(
            self.llm,
            {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60},
        )
        self.trader = MagicMock()
        self.op.setup_tools(trader=self.trader)

    def test_sync_pushes_primary_candle_close_to_trader(self):
        self.op._sync_trader_quote([
            {"type": "primary_candle", "market": "BTC", "closing_price": 50500000}
        ])

        self.trader.update_quote.assert_called_once_with("BTC", 50500000)

    def test_sync_ignores_non_candle_data(self):
        self.op._sync_trader_quote([{"type": "news", "title": "no price"}])

        self.trader.update_quote.assert_not_called()

    def test_sync_is_noop_for_real_trader_without_update_quote(self):
        self.op.trader = object()

        self.op._sync_trader_quote([
            {"type": "primary_candle", "market": "BTC", "closing_price": 50500000}
        ])

    def test_chat_resyncs_last_market_data(self):
        self.op.last_market_data = [
            {"type": "primary_candle", "market": "BTC", "closing_price": 50500000}
        ]

        self.op.chat("매수해줘")

        self.trader.update_quote.assert_called_once_with("BTC", 50500000)

    def test_timer_caches_market_data_and_syncs_quote(self):
        self.op._start_timer = MagicMock()
        self.op.state = "running"
        self.op.data_provider = MagicMock()
        self.op.data_provider.get_info.return_value = [
            {"type": "primary_candle", "market": "BTC", "closing_price": 50500000}
        ]

        self.op._on_timer()

        self.assertEqual(
            self.op.last_market_data,
            [{"type": "primary_candle", "market": "BTC", "closing_price": 50500000}],
        )
        self.trader.update_quote.assert_called_with("BTC", 50500000)

    def test_market_data_tool_result_syncs_quote_during_chat(self):
        market_tool = MagicMock()
        market_tool.name = "get_market_data"
        market_tool.execute.return_value = ToolResult(
            success=True,
            data=[
                {
                    "type": "primary_candle",
                    "market": "BTC",
                    "closing_price": 50500000,
                }
            ],
        )
        self.op.tool_router.register(market_tool)
        self.llm.create_message.side_effect = [
            LlmResponse(
                text="",
                tool_calls=[
                    ToolCall(
                        id="tc_1",
                        name="get_market_data",
                        arguments={"currency": "BTC"},
                    )
                ],
                stop_reason="tool_use",
                usage={"input_tokens": 1, "output_tokens": 1},
            ),
            LlmResponse(
                text="시장 확인 완료",
                tool_calls=[],
                stop_reason="end_turn",
                usage={"input_tokens": 1, "output_tokens": 1},
            ),
        ]

        self.op.chat("BTC 분석해줘")

        self.trader.update_quote.assert_called_once_with("BTC", 50500000)


if __name__ == "__main__":
    unittest.main()
