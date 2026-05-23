"""
E2E 테스트: 채팅 기반 거래 흐름

외부 시스템(LLM API, 거래소 API)만 Fake로 대체하고,
LlmOperator, ToolRouter, SafetyGuard, SystemMonitor, 각 Tool 등
내부 컴포넌트는 전부 실제 동작한다.

테스트 시나리오:
1. 사용자 채팅 → 시장 조회 → 매수 실행 → 결과 반환
2. 사용자 채팅 → 포트폴리오 조회 → 매도 → 수익률 확인
3. 과도한 거래 → SafetyGuard 차단
4. 여러 턴의 대화 흐름 (컨텍스트 유지)
5. 일일 거래 횟수 제한
"""

import unittest
from smtm.llm.llm_operator import LlmOperator
from smtm.llm.llm_client import LlmResponse, ToolCall
from smtm.trader.simulation_trader import SimulationTrader
from .fake_llm_client import FakeLlmClient, FakeDataProvider


class ChatTradingE2ETest(unittest.TestCase):
    """채팅 → 도구 호출 → 거래 실행 전체 E2E 흐름"""

    def _make_operator(self, budget=500000, safety=None):
        self.llm = FakeLlmClient()
        self.trader = SimulationTrader(budget=budget, currency="BTC")
        self.trader.update_quote("BTC", 50000)
        self.dp = FakeDataProvider()
        config = {
            "exchange": "UPB",
            "currency": "BTC",
            "budget": budget,
            "interval": 60,
        }
        if safety:
            config["safety"] = safety
        op = LlmOperator(self.llm, config)
        op.setup_tools(data_provider=self.dp, trader=self.trader)
        return op

    def test_chat_to_market_data_to_buy(self):
        """사용자 메시지 → 시장 데이터 조회 → 매수 실행 → 결과 텍스트 반환"""
        op = self._make_operator()

        self.llm.add_responses([
            # 1) LLM이 시장 데이터 조회 도구 호출
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="get_market_data",
                                    arguments={"currency": "BTC"})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            # 2) 시장 데이터를 보고 매수 결정
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_2", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 50000, "amount": 0.01})],
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
            # 3) 최종 응답
            LlmResponse(
                text="BTC 0.01개를 50,000원에 매수했습니다. 현재 시장이 안정적이어서 소량 진입했습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 300, "output_tokens": 50},
            ),
        ])

        result = op.chat("BTC 시장 분석해서 괜찮으면 매수해줘")

        # 응답 텍스트에 매수 결과가 포함
        self.assertIn("매수", result)

        # SimulationTrader 상태 변경 확인
        self.assertEqual(self.trader.balance, 499500)  # 500000 - (50000 * 0.01)
        self.assertIn("BTC", self.trader.assets)
        self.assertEqual(self.trader.assets["BTC"], (50000, 0.01))

        # SystemMonitor에 기록 확인
        self.assertEqual(len(op.system_monitor.trade_result_log), 1)
        self.assertEqual(len(op.system_monitor.tool_call_log), 2)  # market_data + trade
        self.assertEqual(len(op.system_monitor.llm_interaction_log), 3)

        # LLM에 시스템 프롬프트와 도구 스키마가 전달되었는지 확인
        self.assertTrue(len(self.llm.call_log) == 3)
        first_call = self.llm.call_log[0]
        self.assertIn("암호화폐", first_call["system_prompt"])
        self.assertTrue(len(first_call["tools"]) >= 5)  # 5개 도구 등록됨

    def test_buy_then_sell_with_profit(self):
        """매수 → 가격 상승 → 매도 → 수익 확인"""
        op = self._make_operator()

        # 1단계: 매수
        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 50000, "amount": 0.01})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="BTC 0.01개 매수 완료",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
        ])
        op.chat("BTC 매수해줘")
        self.assertEqual(self.trader.balance, 499500)

        # 2단계: 가격 상승 후 매도
        self.trader.update_quote("BTC", 60000)  # 가격 상승
        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_3", name="execute_trade",
                                    arguments={"action": "sell", "currency": "BTC",
                                               "price": 60000, "amount": 0.01})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_4", name="get_performance", arguments={})],
                usage={"input_tokens": 200, "output_tokens": 20},
            ),
            LlmResponse(
                text="BTC 0.01개를 60,000원에 매도했습니다. 수익률 +0.02%",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 300, "output_tokens": 40},
            ),
        ])
        result = op.chat("BTC 전량 매도하고 수익률 알려줘")

        # 잔고 확인: 499500 + 600 = 500100
        self.assertEqual(self.trader.balance, 500100)
        self.assertNotIn("BTC", self.trader.assets)

        # 거래 기록 2건 (매수 + 매도)
        self.assertEqual(len(op.system_monitor.trade_result_log), 2)

    def test_portfolio_inquiry_no_trade(self):
        """포트폴리오 조회만 하고 거래하지 않는 흐름"""
        op = self._make_operator()

        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="get_portfolio", arguments={})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="현재 잔고 500,000원이며 보유 자산은 없습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
        ])

        result = op.chat("내 포트폴리오 상태 알려줘")
        self.assertIn("500,000", result)

        # 거래 없음
        self.assertEqual(len(op.system_monitor.trade_result_log), 0)
        self.assertEqual(self.trader.balance, 500000)

    def test_trade_history_query(self):
        """거래 후 거래 내역 조회"""
        op = self._make_operator()

        # 매수 실행
        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 50000, "amount": 0.01})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="매수 완료",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 10},
            ),
        ])
        op.chat("BTC 매수")

        # 거래 내역 조회
        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_2", name="get_trade_history",
                                    arguments={"count": 5})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="최근 거래: BTC 0.01개 매수 @ 50,000원",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
        ])
        result = op.chat("최근 거래 내역 보여줘")
        self.assertIn("거래", result)

    def test_multi_turn_conversation_context(self):
        """여러 턴의 대화에서 컨텍스트가 유지되는지 확인"""
        op = self._make_operator()

        # 1턴
        self.llm.add_responses([
            LlmResponse(
                text="현재 시장 상황을 분석하겠습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
        ])
        op.chat("시장 상황이 어때?")

        # 2턴
        self.llm.add_responses([
            LlmResponse(
                text="네, 소량 매수하겠습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 20},
            ),
        ])
        op.chat("그러면 매수할까?")

        # 대화 히스토리에 4개 메시지 (user, assistant, user, assistant)
        self.assertEqual(len(op.conversation_history), 4)
        self.assertEqual(op.conversation_history[0]["role"], "user")
        self.assertEqual(op.conversation_history[1]["role"], "assistant")
        self.assertEqual(op.conversation_history[2]["role"], "user")
        self.assertEqual(op.conversation_history[3]["role"], "assistant")

        # 2번째 LLM 호출 시 이전 대화가 포함되어야 함
        second_call = self.llm.call_log[1]
        self.assertTrue(len(second_call["messages"]) >= 3)


class SafetyGuardE2ETest(unittest.TestCase):
    """SafetyGuard 전체 E2E 흐름 — 실제 ToolRouter, SafetyGuard 동작"""

    def _make_operator(self, budget=500000, safety=None):
        self.llm = FakeLlmClient()
        self.trader = SimulationTrader(budget=budget, currency="BTC")
        self.trader.update_quote("BTC", 50000)
        self.dp = FakeDataProvider()
        config = {
            "exchange": "UPB",
            "currency": "BTC",
            "budget": budget,
            "interval": 60,
        }
        if safety:
            config["safety"] = safety
        op = LlmOperator(self.llm, config)
        op.setup_tools(data_provider=self.dp, trader=self.trader)
        return op

    def test_max_trade_amount_blocks_large_order(self):
        """최대 거래 금액 초과 시 차단"""
        op = self._make_operator(safety={"max_trade_amount": 10000})

        self.llm.add_responses([
            # LLM이 큰 금액 매수 시도
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 50000, "amount": 1.0})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            # SafetyGuard 차단 후 LLM이 응답
            LlmResponse(
                text="거래 금액이 제한을 초과하여 차단되었습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
        ])

        result = op.chat("BTC 전량 매수")

        # 거래 실행되지 않음
        self.assertEqual(self.trader.balance, 500000)
        self.assertEqual(len(self.trader.order_history), 0)

        # SafetyGuard 이벤트 기록
        self.assertEqual(len(op.system_monitor.safety_event_log), 1)
        event = op.system_monitor.safety_event_log[0]["event"]
        self.assertEqual(event["type"], "blocked")
        self.assertIn("초과", event["reason"])

    def test_small_order_passes_safety_guard(self):
        """제한 이내의 거래는 정상 통과"""
        op = self._make_operator(safety={"max_trade_amount": 10000})

        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 5000, "amount": 0.001})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="소량 매수 완료",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 20},
            ),
        ])

        op.chat("소량 매수해줘")

        self.assertEqual(self.trader.balance, 500000 - 50)
        self.assertEqual(len(op.system_monitor.safety_event_log), 0)
        self.assertEqual(len(op.system_monitor.trade_result_log), 1)

    def test_daily_trade_limit(self):
        """일일 거래 횟수 제한"""
        op = self._make_operator(safety={"max_daily_trades": 2, "max_trade_amount": 100000})

        # 거래 1, 2 성공
        for i in range(2):
            self.llm.add_responses([
                LlmResponse(
                    text="", stop_reason="tool_use",
                    tool_calls=[ToolCall(id=f"tc_{i}", name="execute_trade",
                                        arguments={"action": "buy", "currency": "BTC",
                                                   "price": 1000, "amount": 0.001})],
                    usage={"input_tokens": 100, "output_tokens": 20},
                ),
                LlmResponse(
                    text=f"매수 {i+1} 완료",
                    tool_calls=[], stop_reason="end_turn",
                    usage={"input_tokens": 200, "output_tokens": 20},
                ),
            ])
            op.chat(f"매수 {i+1}")

        self.assertEqual(len(op.system_monitor.trade_result_log), 2)

        # 3번째 거래 차단
        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_blocked", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 1000, "amount": 0.001})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="일일 거래 횟수 제한으로 차단되었습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
        ])
        op.chat("매수 3")

        # 거래 결과는 2건만, safety 이벤트 1건
        self.assertEqual(len(op.system_monitor.trade_result_log), 2)
        self.assertEqual(len(op.system_monitor.safety_event_log), 1)

    def test_non_trade_tools_bypass_safety(self):
        """거래가 아닌 도구(시장 데이터, 포트폴리오)는 SafetyGuard를 우회"""
        op = self._make_operator(safety={"max_trade_amount": 0})  # 모든 거래 차단

        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="get_market_data",
                                    arguments={"currency": "BTC"})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_2", name="get_portfolio", arguments={})],
                usage={"input_tokens": 200, "output_tokens": 20},
            ),
            LlmResponse(
                text="시장 데이터와 포트폴리오를 조회했습니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 300, "output_tokens": 30},
            ),
        ])

        result = op.chat("시장 데이터랑 포트폴리오 조회해줘")

        # 조회 도구는 차단 없이 실행
        self.assertEqual(len(op.system_monitor.tool_call_log), 2)
        self.assertEqual(len(op.system_monitor.safety_event_log), 0)


class MonitoringE2ETest(unittest.TestCase):
    """SystemMonitor 기록 E2E 검증"""

    def _make_operator(self, budget=500000):
        self.llm = FakeLlmClient()
        self.trader = SimulationTrader(budget=budget, currency="BTC")
        self.trader.update_quote("BTC", 50000)
        self.dp = FakeDataProvider()
        config = {
            "exchange": "UPB",
            "currency": "BTC",
            "budget": budget,
            "interval": 60,
        }
        op = LlmOperator(self.llm, config)
        op.setup_tools(data_provider=self.dp, trader=self.trader)
        return op

    def test_all_interactions_logged(self):
        """모든 LLM 호출, 도구 호출, 거래가 SystemMonitor에 기록"""
        op = self._make_operator()

        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="get_market_data",
                                    arguments={"currency": "BTC"})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_2", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 50000, "amount": 0.01})],
                usage={"input_tokens": 200, "output_tokens": 30},
            ),
            LlmResponse(
                text="매수 완료",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 300, "output_tokens": 20},
            ),
        ])

        op.chat("BTC 분석 후 매수")

        monitor = op.system_monitor

        # LLM 호출 3회
        self.assertEqual(len(monitor.llm_interaction_log), 3)

        # 도구 호출 2회 (market_data + trade)
        self.assertEqual(len(monitor.tool_call_log), 2)
        self.assertEqual(monitor.tool_call_log[0]["tool_name"], "get_market_data")
        self.assertEqual(monitor.tool_call_log[1]["tool_name"], "execute_trade")

        # 거래 요청/결과 각 1회
        self.assertEqual(len(monitor.trade_request_log), 1)
        self.assertEqual(len(monitor.trade_result_log), 1)

        # LLM 사용량 집계
        usage = monitor.get_llm_usage()
        self.assertEqual(usage["call_count"], 3)
        self.assertEqual(usage["total_input_tokens"], 600)
        self.assertEqual(usage["total_output_tokens"], 70)

    def test_failed_trade_logged(self):
        """잔고 부족으로 실패한 거래도 SystemMonitor에 기록"""
        op = self._make_operator(budget=100)

        self.llm.add_responses([
            LlmResponse(
                text="", stop_reason="tool_use",
                tool_calls=[ToolCall(id="tc_1", name="execute_trade",
                                    arguments={"action": "buy", "currency": "BTC",
                                               "price": 50000, "amount": 1.0})],
                usage={"input_tokens": 100, "output_tokens": 20},
            ),
            LlmResponse(
                text="잔고가 부족합니다.",
                tool_calls=[], stop_reason="end_turn",
                usage={"input_tokens": 200, "output_tokens": 20},
            ),
        ])

        op.chat("BTC 매수")

        # 거래 요청은 기록, 결과도 기록 (실패 포함)
        self.assertEqual(len(op.system_monitor.trade_request_log), 1)
        self.assertEqual(len(op.system_monitor.trade_result_log), 1)
        self.assertEqual(op.system_monitor.trade_result_log[0]["result"]["state"], "failed")


if __name__ == "__main__":
    unittest.main()
