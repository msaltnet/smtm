"""
E2E 테스트 — 2계층 아키텍처

시나리오: 채팅(에이전트 Tool use) → 전략 선택 → 매매 시작 → 틱 수행 → 결과 검증
외부 API 없이 FakeLlmClient / FakeDataProvider로 전 구간 검증.
"""
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from smtm import ProfileStore, AccountStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmResponse, ToolCall

from .fake_llm_client import FakeLlmClient, FakeDataProvider


_data_provider_patcher = None
_account_dir = None


def setUpModule():
    # SessionManager._assemble은 DataProviderFactory를 지역 import하므로,
    # 실제 Factory의 create를 패치해 모듈 전체가 실 거래소로 네트워크 틱을
    # 보내지 않도록 한다 (unit 테스트들과 동일 패턴).
    global _data_provider_patcher, _account_dir
    _data_provider_patcher = patch(
        "smtm.data.data_provider_factory.DataProviderFactory.create",
        side_effect=lambda *a, **k: FakeDataProvider())
    _data_provider_patcher.start()
    _account_dir = tempfile.TemporaryDirectory()


def tearDownModule():
    _data_provider_patcher.stop()
    _account_dir.cleanup()


def make_operator(strategy="BNH", profile_store=None, responses=None,
                  budget=500000, safety=None):
    llm = FakeLlmClient(responses)
    operator = SystemOperator(llm, {
        "exchange": "UPB", "currency": "BTC", "budget": budget,
        "interval": 60, "virtual": True, "strategy": strategy,
        "safety": safety or {},
    }, profile_store=profile_store,
       account_store=AccountStore(dir_path=_account_dir.name))
    operator.setup()
    return operator, llm


def tick(operator):
    """타이머를 기다리지 않고 틱 1회 직접 수행 (default 세션)"""
    operator.session_manager.get_session("default").operator._execute_trading(None)


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
        default_session = operator.session_manager.get_session("default")
        self.assertEqual(default_session.operator.state, "running")

        # start()가 worker에 첫 틱을 즉시 post하므로 수동 tick() 대신
        # 첫 틱의 체결을 폴링으로 기다린다 (interval=60이라 두 번째 틱은 없음)
        trader = default_session.trader
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
        operator.session_manager.get_session("default").operator.state = "running"
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
        operator.session_manager.get_session("default").operator.state = "running"
        tick(operator)
        trader = operator.session_manager.get_session("default").trader
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
        session = operator.session_manager.get_session("default")
        session.operator.state = "running"
        tick(operator)
        self.assertEqual(len(session.trader.order_history), 0)
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
        self.assertEqual(operator.default_strategy(), "RSI")
        self.assertEqual(operator.budget, 200000)


class MonitoringE2ETest(unittest.TestCase):
    def test_tick_activity_is_logged(self):
        operator, _ = make_operator(strategy="BNH")
        self.addCleanup(operator.stop_trading)
        operator.session_manager.get_session("default").operator.state = "running"
        tick(operator)
        monitor = operator.system_monitor
        self.assertGreaterEqual(len(monitor.market_data_log), 1)
        self.assertGreaterEqual(len(monitor.trade_request_log), 1)
        self.assertGreaterEqual(len(monitor.trade_result_log), 1)


class MultiSessionE2ETest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.profile_store = ProfileStore(dir_path=self.tmp.name + "/p")
        self.account_store = AccountStore(dir_path=self.tmp.name + "/a")

    def tearDown(self):
        self.tmp.cleanup()

    def _operator(self, responses=None):
        llm = FakeLlmClient(responses)
        operator = SystemOperator(llm, {
            "exchange": "UPB", "currency": "BTC", "budget": 500000,
            "interval": 60, "virtual": True, "strategy": "BNH",
        }, profile_store=self.profile_store, account_store=self.account_store)
        operator.setup()
        # 모든 세션의 data_provider를 Fake로 교체하는 대신 factory 스텁 사용
        return operator, llm

    def test_chat_two_virtual_sessions_and_compare(self):
        """채팅: 프로파일 생성 → 세션 2개 기동 → 각자 틱 → 성과 비교"""
        responses = [
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="create_profile", arguments={
                    "name": "bnh-v", "strategy": "BNH", "virtual": True,
                    "budget": 300000})]),
            LlmResponse(text="프로파일 생성"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t2", name="create_session",
                         arguments={"profile": "bnh-v"})]),
            LlmResponse(text="세션 생성"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t3", name="start_session",
                         arguments={"session": "bnh-v"})]),
            LlmResponse(text="세션 시작"),
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t4", name="compare_performance", arguments={})]),
            LlmResponse(text="성과 비교 결과입니다"),
        ]
        with patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: FakeDataProvider()):
            operator, llm = self._operator(responses)
            self.addCleanup(operator.shutdown)
            operator.chat("BNH 가상 프로파일 만들어줘")
            operator.chat("그걸로 세션 만들어줘")
            operator.chat("세션 시작해줘")
            manager = operator.session_manager
            self.assertEqual(manager.get_session("bnh-v").state, "running")
            # default 세션과 신규 세션이 공존
            self.assertEqual(len(manager.list_sessions()), 2)
            # start가 워커에 첫 틱을 post하므로 폴링으로 첫 체결 대기
            # (interval=60 → 두 번째 틱 없음, 수동 틱 호출 금지: 이중 주문 경합)
            trader = manager.get_session("bnh-v").trader
            deadline = time.time() + 5
            while time.time() < deadline and len(trader.order_history) == 0:
                time.sleep(0.05)
            self.assertEqual(len(trader.order_history), 1)
            self.assertEqual(
                len(manager.get_session("default").trader.order_history), 0)
            reply = operator.chat("성과 비교해줘")
            self.assertIn("성과", reply)

    def test_legacy_default_flow_still_works(self):
        """기존 start_trading/stop_trading 경로가 default 세션으로 동작"""
        with patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: FakeDataProvider()):
            operator, _ = self._operator()
            self.addCleanup(operator.shutdown)
            self.assertTrue(operator.start_trading()["success"])
            self.assertEqual(
                operator.session_manager.get_session("default").state, "running")
            self.assertTrue(operator.stop_trading()["success"])

    def test_account_registration_never_leaks_key_values(self):
        """계좌 등록 대화 전 구간에 키 값이 등장하지 않는다"""
        responses = [
            LlmResponse(text="", stop_reason="tool_use", tool_calls=[
                ToolCall(id="t1", name="register_account", arguments={
                    "name": "main", "exchange": "UPB",
                    "access_key_env": "SMTM_E2E_K",
                    "secret_key_env": "SMTM_E2E_S"})]),
            LlmResponse(text="계좌가 등록되었습니다"),
        ]
        with patch("smtm.data.data_provider_factory.DataProviderFactory.create",
                   side_effect=lambda *a, **k: FakeDataProvider()), \
             patch.dict(os.environ, {"SMTM_E2E_K": "TOP-SECRET-KEY",
                                     "SMTM_E2E_S": "TOP-SECRET-2"}):
            operator, llm = self._operator(responses)
            self.addCleanup(operator.shutdown)
            operator.chat("main 계좌 등록해줘")
            # Tool 결과/대화 이력 어디에도 키 값 없음
            self.assertNotIn("TOP-SECRET", str(operator.conversation_history))
            self.assertNotIn("TOP-SECRET",
                             str(operator.system_monitor.tool_call_log))
