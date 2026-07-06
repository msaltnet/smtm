import unittest
from smtm import StrategyLlm, StrategyFactory
from smtm.llm.llm_client import LlmResponse, ToolCall


class ScriptedLlmClient:
    """지정된 판단을 반환하는 테스트용 클라이언트"""

    def __init__(self, decision=None, raise_error=False):
        self.decision = decision
        self.raise_error = raise_error
        self.call_log = []

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        self.call_log.append({"system_prompt": system_prompt, "messages": messages,
                              "tools": tools, "tool_choice": tool_choice})
        if self.raise_error:
            raise RuntimeError("api error")
        if self.decision is None:
            return LlmResponse(text="no tool call", tool_calls=[])
        return LlmResponse(text="", tool_calls=[
            ToolCall(id="t1", name="submit_decision", arguments=self.decision)
        ])


CANDLE = {
    "type": "primary_candle", "market": "BTC", "date_time": "2026-07-03T12:00:00",
    "opening_price": 50000, "high_price": 51000, "low_price": 49000,
    "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
}


def make_strategy(decision=None, raise_error=False, budget=500000):
    client = ScriptedLlmClient(decision=decision, raise_error=raise_error)
    strategy = StrategyLlm(llm_client=client)
    strategy.initialize(budget)
    strategy.update_trading_info([CANDLE])
    return strategy, client


class StrategyLlmTests(unittest.TestCase):
    def test_buy_decision_produces_buy_request(self):
        strategy, client = make_strategy(
            {"action": "buy", "price": 50000, "amount": 0.5,
             "confidence": 0.8, "reason": "상승 추세"})
        requests = strategy.get_request()
        self.assertEqual(requests[-1]["type"], "buy")
        self.assertEqual(requests[-1]["price"], 50000)
        self.assertEqual(requests[-1]["amount"], 0.5)
        # 강제 tool use 확인
        self.assertEqual(client.call_log[0]["tool_choice"],
                         {"type": "tool", "name": "submit_decision"})

    def test_hold_decision_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "hold", "confidence": 0.5, "reason": "관망"})
        self.assertIsNone(strategy.get_request())

    def test_sell_without_position_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "sell", "price": 50000, "amount": 1.0,
             "confidence": 0.9, "reason": "하락"})
        self.assertIsNone(strategy.get_request())  # 보유 수량 0

    def test_buy_exceeding_balance_returns_none(self):
        strategy, _ = make_strategy(
            {"action": "buy", "price": 50000, "amount": 100.0,
             "confidence": 0.9, "reason": "무리한 매수"})
        self.assertIsNone(strategy.get_request())  # 500만 > 잔고 50만

    def test_llm_error_falls_back_to_hold(self):
        strategy, _ = make_strategy(raise_error=True)
        self.assertIsNone(strategy.get_request())

    def test_no_tool_call_falls_back_to_hold(self):
        strategy, _ = make_strategy(decision=None)
        self.assertIsNone(strategy.get_request())

    def test_invalid_action_falls_back_to_hold(self):
        strategy, _ = make_strategy(
            {"action": "yolo", "reason": "?"})
        self.assertIsNone(strategy.get_request())

    def test_update_result_tracks_balance_and_asset(self):
        strategy, _ = make_strategy(
            {"action": "buy", "price": 50000, "amount": 0.5,
             "confidence": 0.8, "reason": "매수"})
        strategy.update_result({
            "request": {"id": "1"}, "type": "buy", "price": 50000, "amount": 0.5,
            "msg": "success", "state": "done", "balance": 475000,
            "date_time": "2026-07-03T12:00:01",
        })
        self.assertLess(strategy.balance, 500000)
        self.assertEqual(strategy.asset_amount, 0.5)

    def test_not_initialized_returns_none(self):
        strategy = StrategyLlm(llm_client=ScriptedLlmClient())
        self.assertIsNone(strategy.get_request())

    def test_factory_creates_llm_strategy_with_client(self):
        client = ScriptedLlmClient()
        strategy = StrategyFactory.create("LLM", llm_client=client)
        self.assertIsInstance(strategy, StrategyLlm)
        self.assertIs(strategy.llm_client, client)
