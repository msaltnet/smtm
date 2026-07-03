"""
E2E 테스트 — 2계층 아키텍처

시나리오: 채팅(에이전트 Tool use) → 전략 선택 → 매매 시작 → 틱 수행 → 결과 검증
외부 API 없이 FakeLlmClient / FakeDataProvider로 전 구간 검증.
"""
import tempfile
import time
import unittest

from smtm import ProfileStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmResponse, ToolCall

from .fake_llm_client import FakeLlmClient, FakeDataProvider


def make_operator(strategy="BNH", profile_store=None, responses=None,
                  budget=500000, safety=None):
    llm = FakeLlmClient(responses)
    operator = SystemOperator(llm, {
        "exchange": "UPB", "currency": "BTC", "budget": budget,
        "interval": 60, "virtual": True, "strategy": strategy,
        "safety": safety or {},
    }, profile_store=profile_store)
    operator.setup()
    # 실제 네트워크 대신 Fake 데이터 주입
    operator.data_provider = FakeDataProvider()
    operator.trading_operator.data_provider = operator.data_provider
    return operator, llm


def tick(operator):
    """타이머를 기다리지 않고 틱 1회 직접 수행"""
    operator.trading_operator._execute_trading(None)


class StrategyTradingE2ETest(unittest.TestCase):
    def test_chat_select_strategy_start_tick_buy(self):
        """채팅으로 전략 선택+시작 → 틱 → BnH 매수 체결"""
        responses = [
            # turn 1: 에이전트가 select_strategy 호출
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="select_strategy",
                         arguments={"code": "BNH"})]),
            LlmResponse(text="BNH 전략을 선택했습니다"),
            # turn 2: 에이전트가 start_trading 호출
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t2", name="start_trading", arguments={})]),
            LlmResponse(text="자동 매매를 시작했습니다"),
        ]
        operator, _ = make_operator(strategy=None, responses=responses)
        self.addCleanup(operator.stop_trading)

        reply = operator.chat("BNH 전략으로 설정해줘")
        self.assertIn("BNH", reply)
        reply = operator.chat("매매 시작해줘")
        self.assertEqual(operator.trading_operator.state, "running")

        # start()가 worker에 첫 틱을 즉시 post하므로 수동 tick() 대신
        # 첫 틱의 체결을 폴링으로 기다린다 (interval=60이라 두 번째 틱은 없음)
        trader = operator.trader
        deadline = time.time() + 5
        while time.time() < deadline and len(trader.order_history) == 0:
            time.sleep(0.05)
        # BnH: 예산 1/5 매수 (FakeDataProvider 종가 50000 주입 체결)
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["type"], "buy")
        self.assertEqual(trader.order_history[0]["price"], 50000)
        self.assertLess(trader.balance, 500000)

    def test_algorithmic_tick_makes_zero_llm_calls(self):
        """알고리즘 전략 틱은 LLM을 호출하지 않는다"""
        operator, llm = make_operator(strategy="BNH")
        self.addCleanup(operator.stop_trading)
        operator.trading_operator.state = "running"
        calls_before = len(llm.call_log)
        tick(operator)
        self.assertEqual(len(llm.call_log), calls_before)

    def test_llm_strategy_tick_uses_forced_decision(self):
        """LLM 전략 틱: 강제 submit_decision 1회 호출로 매수"""
        operator, llm = make_operator(strategy="LLM")
        self.addCleanup(operator.stop_trading)
        llm.add_response(LlmResponse(text="", stop_reason="tool_use", tool_calls=[
            ToolCall(id="d1", name="submit_decision", arguments={
                "action": "buy", "price": 50000, "amount": 0.5,
                "confidence": 0.8, "reason": "테스트 매수"})]))
        operator.trading_operator.state = "running"
        tick(operator)
        trader = operator.trader
        self.assertEqual(len(trader.order_history), 1)
        self.assertEqual(trader.order_history[0]["type"], "buy")
        # 강제 tool use 확인
        self.assertEqual(llm.call_log[-1]["tool_choice"],
                         {"type": "tool", "name": "submit_decision"})

    def test_safety_guard_blocks_oversized_trade(self):
        """SafetyGuard가 한도 초과 주문을 차단하고 이벤트를 기록"""
        operator, _ = make_operator(strategy="BNH",
                                    safety={"max_trade_amount": 1000})
        self.addCleanup(operator.stop_trading)
        operator.trading_operator.state = "running"
        tick(operator)
        self.assertEqual(len(operator.trader.order_history), 0)
        self.assertEqual(len(operator.system_monitor.safety_event_log), 1)


class ProfileE2ETest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ProfileStore(dir_path=self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_chat_create_and_switch_profile(self):
        responses = [
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="create_profile", arguments={
                    "name": "rsi-virtual", "strategy": "RSI",
                    "budget": 200000, "virtual": True})]),
            LlmResponse(text="프로파일을 생성했습니다"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t2", name="switch_profile",
                         arguments={"name": "rsi-virtual"})]),
            LlmResponse(text="프로파일로 전환했습니다"),
        ]
        operator, _ = make_operator(profile_store=self.store,
                                    responses=responses)
        self.addCleanup(operator.stop_trading)

        operator.chat("RSI 전략으로 가상매매 프로파일 만들어줘")
        self.assertEqual(len(self.store.list_profiles()), 1)

        operator.chat("그 프로파일로 전환해줘")
        self.assertEqual(operator.strategy_code, "RSI")
        self.assertEqual(operator.budget, 200000)


class MonitoringE2ETest(unittest.TestCase):
    def test_tick_activity_is_logged(self):
        operator, _ = make_operator(strategy="BNH")
        self.addCleanup(operator.stop_trading)
        operator.trading_operator.state = "running"
        tick(operator)
        monitor = operator.system_monitor
        self.assertGreaterEqual(len(monitor.market_data_log), 1)
        self.assertGreaterEqual(len(monitor.trade_request_log), 1)
        self.assertGreaterEqual(len(monitor.trade_result_log), 1)
