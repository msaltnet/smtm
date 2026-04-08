import unittest
from unittest.mock import *
from smtm.llm.llm_operator import LlmOperator
from smtm.llm.llm_client import LlmResponse, ToolCall


class LlmOperatorIntegrationTests(unittest.TestCase):
    """LlmOperator 전체 흐름 통합 테스트 (LLM API는 mock)"""

    def test_full_trading_cycle_with_tool_use(self):
        """시장 데이터 조회 → 판단 → 매수 실행 전체 흐름"""
        llm_client = MagicMock()
        config = {"exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60}
        op = LlmOperator(llm_client, config)

        dp = MagicMock()
        dp.get_info.return_value = [
            {"type": "primary_candle", "market": "BTC", "closing_price": 50000000,
             "opening_price": 49000000, "high_price": 51000000, "low_price": 48000000,
             "acc_price": 1000000, "acc_volume": 100, "date_time": "2026-04-07T12:00:00"}
        ]
        trader = MagicMock()
        trader.get_account_info.return_value = {"balance": 500000, "asset": {}, "quote": {}}
        def fake_send(req_list, cb):
            cb({"type": "buy", "price": 50000, "amount": 0.01, "state": "done",
                "request": req_list[0], "msg": "success", "balance": 449500,
                "date_time": "2026-04-07T12:00:02"})
        trader.send_request.side_effect = fake_send

        op.setup_tools(data_provider=dp, trader=trader)

        responses = [
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="get_portfolio", arguments={})],
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_2", name="execute_trade",
                    arguments={"action": "buy", "currency": "BTC", "price": 50000, "amount": 0.01})],
                usage={"input_tokens": 300, "output_tokens": 40},
            ),
            LlmResponse(
                text="BTC 0.01개를 50,000원에 매수했습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 400, "output_tokens": 50},
            ),
        ]
        llm_client.create_message.side_effect = responses

        result = op.chat("BTC 시장 분석 후 적절하면 매수해줘")
        self.assertIn("매수", result)
        self.assertEqual(len(op.system_monitor.trade_result_log), 1)
        self.assertEqual(llm_client.create_message.call_count, 3)

    def test_safety_guard_blocks_excessive_trade(self):
        """안전장치가 과도한 거래를 차단하는 흐름"""
        llm_client = MagicMock()
        config = {
            "exchange": "UPB", "currency": "BTC", "budget": 500000, "interval": 60,
            "safety": {"max_trade_amount": 10000},
        }
        op = LlmOperator(llm_client, config)
        trader = MagicMock()
        op.setup_tools(trader=trader)

        responses = [
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="execute_trade",
                    arguments={"action": "buy", "currency": "BTC", "price": 50000, "amount": 1.0})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="거래금액이 너무 커서 차단되었습니다. 소량으로 분할 매수하겠습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 150, "output_tokens": 30},
            ),
        ]
        llm_client.create_message.side_effect = responses

        result = op.chat("BTC 전량 매수해")
        trader.send_request.assert_not_called()
        self.assertEqual(len(op.system_monitor.safety_event_log), 1)
