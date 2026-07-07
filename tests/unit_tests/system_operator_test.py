import unittest
import tempfile
from unittest.mock import patch
from smtm import AccountStore
from smtm.llm.system_operator import SystemOperator
from smtm.llm.llm_client import LlmClient, LlmResponse, ToolCall


class StubDataProvider:
    """실 네트워크 호출 없이 고정 캔들을 반환하는 테스트용 DataProvider"""

    def get_info(self):
        return [{
            "type": "primary_candle", "market": "BTC",
            "date_time": "2026-07-03T12:00:00",
            "opening_price": 50000, "high_price": 51000, "low_price": 49000,
            "closing_price": 50000, "acc_price": 1000000000, "acc_volume": 200,
        }]


_data_provider_patcher = None
_account_dir = None


def setUpModule():
    # SessionManager._assemble은 DataProviderFactory를 지역 import하므로,
    # 실제 Factory의 create를 패치해 어떤 유닛 테스트도 실 거래소로
    # 네트워크 틱을 보내지 않도록 한다 (select_strategy/apply_profile 등은
    # replace_session으로 이 경로를 다시 탄다).
    global _data_provider_patcher, _account_dir
    _data_provider_patcher = patch(
        "smtm.data.data_provider_factory.DataProviderFactory.create",
        side_effect=lambda *a, **k: StubDataProvider(),
    )
    _data_provider_patcher.start()
    _account_dir = tempfile.TemporaryDirectory()


def tearDownModule():
    _data_provider_patcher.stop()
    _account_dir.cleanup()


class StubLlmClient(LlmClient):
    def __init__(self, responses=None):
        self.responses = list(responses or [])
        self.call_log = []

    def create_message(self, system_prompt, messages, tools, tool_choice=None):
        self.call_log.append({"system_prompt": system_prompt, "messages": messages,
                              "tools": tools})
        if not self.responses:
            return LlmResponse(text="ok")
        return self.responses.pop(0)


def make_operator(config_extra=None, responses=None):
    config = {
        "exchange": "UPB", "currency": "BTC", "budget": 500000,
        "interval": 60, "virtual": True, "strategy": "BNH",
        **(config_extra or {}),
    }
    operator = SystemOperator(
        StubLlmClient(responses), config,
        account_store=AccountStore(dir_path=_account_dir.name))
    operator.setup()
    return operator


class SystemOperatorSetupTests(unittest.TestCase):
    def test_setup_builds_default_session_with_default_strategy(self):
        operator = make_operator()
        session_operator = operator.session_manager.get_session("default").operator
        self.assertIsNotNone(session_operator)
        self.assertEqual(session_operator.state, "ready")
        self.assertEqual(operator.default_strategy(), "BNH")

    def test_setup_without_strategy_falls_back_to_bnh(self):
        operator = make_operator(config_extra={"strategy": None})
        self.assertEqual(operator.default_strategy(), "BNH")

    def test_no_trade_tool_registered(self):
        operator = make_operator()
        tool_names = set(operator.tool_router.tools.keys())
        self.assertNotIn("execute_trade", tool_names)
        self.assertIn("get_market_data", tool_names)
        self.assertIn("get_portfolio", tool_names)
        self.assertIn("get_trade_history", tool_names)
        self.assertIn("get_performance", tool_names)


class SystemOperatorOrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.operator = make_operator()

    def tearDown(self):
        self.operator.stop_trading()

    def test_start_and_stop_trading(self):
        result = self.operator.start_trading()
        self.assertTrue(result["success"])
        self.assertEqual(
            self.operator.session_manager.get_session("default").operator.state,
            "running")
        result = self.operator.stop_trading()
        self.assertTrue(result["success"])
        self.assertEqual(
            self.operator.session_manager.get_session("default").operator.state,
            "ready")

    def test_select_strategy_rebuilds_with_new_strategy(self):
        result = self.operator.select_strategy("RSI")
        self.assertTrue(result["success"])
        self.assertEqual(self.operator.default_strategy(), "RSI")
        self.assertEqual(
            self.operator.session_manager.get_session("default")
            .operator.strategy.CODE, "RSI")

    def test_select_strategy_rejected_while_running(self):
        self.operator.start_trading()
        result = self.operator.select_strategy("RSI")
        self.assertFalse(result["success"])
        self.assertEqual(self.operator.default_strategy(), "BNH")

    def test_select_unknown_strategy_fails(self):
        result = self.operator.select_strategy("NOPE")
        self.assertFalse(result["success"])

    def test_get_status_contains_key_fields(self):
        status = self.operator.get_status()
        self.assertEqual(status["sessions"][0]["name"], "default")
        self.assertEqual(status["sessions"][0]["state"], "ready")
        self.assertIn("llm_usage", status)

    def test_apply_profile_reconfigures(self):
        result = self.operator.apply_profile({
            "name": "aggressive", "strategy": "RSI", "budget": 300000,
            "virtual": True, "exchange": "UPB", "currency": "BTC",
        })
        self.assertTrue(result["success"])
        self.assertEqual(self.operator.default_strategy(), "RSI")
        self.assertEqual(self.operator.budget, 300000)

    def test_apply_profile_failure_keeps_current_config(self):
        result = self.operator.apply_profile({
            "name": "bad", "strategy": "NOPE", "budget": 999999,
        })
        self.assertFalse(result["success"])
        self.assertEqual(self.operator.default_strategy(), "BNH")
        self.assertEqual(self.operator.budget, 500000)
        self.assertEqual(self.operator.config.get("strategy"), "BNH")
        # 원복 후에도 매매 시작이 가능해야 한다 (일관 상태)
        self.assertTrue(self.operator.start_trading()["success"])

    def test_apply_profile_with_bad_safety_key_keeps_config(self):
        result = self.operator.apply_profile({
            "name": "bad-safety", "safety": {"max_trade": 5},
        })
        self.assertFalse(result["success"])
        # make_operator의 초기 config에는 "safety" 키가 없으므로 복원 후에도
        # 부재 상태가 유지되어야 한다 (반쯤 재구성된 상태가 아니라 이전
        # 스냅샷 그대로).
        self.assertIsNone(self.operator.config.get("safety"))
        # 복원 후에도 일관 상태
        self.assertTrue(self.operator.start_trading()["success"])

    def test_read_tools_reflect_new_session_after_strategy_change(self):
        # 읽기 Tool은 session_manager를 통해 execute 시점에 세션을 해석하므로
        # (Task 10) 세션 교체 후에도 재등록 없이 최신 세션 데이터를 반환해야 한다.
        portfolio_tool = self.operator.tool_router.tools["get_portfolio"]
        self.operator.select_strategy("RSI")
        session = self.operator.session_manager.get_session("default")
        result = portfolio_tool.execute({})
        self.assertTrue(result.success)
        self.assertEqual(result.data, session.trader.get_account_info())

    def test_select_strategy_preserves_daily_trade_count(self):
        self.operator.session_manager.get_session("default").session_guard.record_trade({})
        self.operator.session_manager.get_session("default").session_guard.record_trade({})
        self.operator.select_strategy("RSI")
        self.assertEqual(
            self.operator.session_manager.get_session("default")
            .session_guard.daily_trade_count, 2)

    def test_apply_partial_profile_inherits_current_virtual(self):
        # virtual 미지정 부분 프로파일 → 기존 가상 모드 유지 (실거래 전환 금지)
        result = self.operator.apply_profile({"name": "rsi-only", "strategy": "RSI"})
        self.assertTrue(result["success"])
        session = self.operator.session_manager.get_session("default")
        self.assertTrue(session.profile.get("virtual"))

    def test_apply_profile_recomputes_default_strategy_note(self):
        operator = make_operator(config_extra={"strategy": None})
        try:
            self.assertTrue(operator.default_strategy_used)
            operator.apply_profile({"name": "p", "strategy": "RSI", "virtual": True})
            result = operator.start_trading()
            self.assertTrue(result["success"])
            self.assertNotIn("note", result)
        finally:
            operator.shutdown()


class SystemOperatorMultiSessionTests(unittest.TestCase):
    def setUp(self):
        self.operator = make_operator()

    def tearDown(self):
        self.operator.shutdown()

    def test_setup_creates_default_session_not_started(self):
        session = self.operator.session_manager.get_session("default")
        self.assertEqual(session.state, "ready")

    def test_get_status_overview_lists_sessions(self):
        status = self.operator.get_status()
        names = [s["name"] for s in status["sessions"]]
        self.assertIn("default", names)
        self.assertIn("llm_usage", status)

    def test_get_status_with_session_returns_detail(self):
        status = self.operator.get_status(session="default")
        self.assertEqual(status["name"], "default")
        self.assertIn("safety", status)

    def test_shutdown_stops_all_running_sessions(self):
        self.operator.start_trading()
        self.operator.shutdown()
        self.assertEqual(
            self.operator.session_manager.get_session("default").state, "ready")


class SystemOperatorChatTests(unittest.TestCase):
    def test_chat_returns_text(self):
        operator = make_operator(responses=[LlmResponse(text="안녕하세요")])
        self.assertEqual(operator.chat("hi"), "안녕하세요")

    def test_chat_executes_tool_loop(self):
        # get_portfolio는 이 태스크에서 등록되는 읽기 전용 Tool
        # (오케스트레이션 Tool 등록은 Task 12)
        responses = [
            LlmResponse(text="", tool_calls=[
                ToolCall(id="t1", name="get_portfolio", arguments={})
            ], stop_reason="tool_use"),
            LlmResponse(text="포트폴리오입니다"),
        ]
        operator = make_operator(responses=responses)
        result = operator.chat("포트폴리오 알려줘")
        self.assertEqual(result, "포트폴리오입니다")

    def test_tool_loop_appends_anthropic_format_blocks(self):
        responses = [
            LlmResponse(text="확인해볼게요", tool_calls=[
                ToolCall(id="t1", name="get_portfolio", arguments={})
            ], stop_reason="tool_use"),
            LlmResponse(text="완료"),
        ]
        operator = make_operator(responses=responses)
        operator.chat("포트폴리오?")
        second_call_messages = operator.llm_client.call_log[1]["messages"]
        assistant_msg = second_call_messages[-2]
        self.assertEqual(assistant_msg["role"], "assistant")
        types = [block["type"] for block in assistant_msg["content"]]
        self.assertIn("text", types)
        self.assertIn("tool_use", types)
        tool_block = [b for b in assistant_msg["content"] if b["type"] == "tool_use"][0]
        self.assertEqual(tool_block["name"], "get_portfolio")
        self.assertEqual(tool_block["id"], "t1")

    def test_chat_trims_history(self):
        operator = make_operator(config_extra={
            "context": {"max_conversation_turns": 2}})
        for i in range(5):
            operator.llm_client.responses.append(LlmResponse(text=f"r{i}"))
            operator.chat(f"m{i}")
        self.assertLessEqual(len(operator.conversation_history), 4)
