import os
from dataclasses import dataclass
from ..log_manager import LogManager
from .tool_router import ToolRouter
from .system_monitor import SystemMonitor


@dataclass
class ContextConfig:
    """LLM에 전달할 컨텍스트 범위 설정"""
    candle_count: int = 20
    include_portfolio: bool = True
    include_trade_history: bool = True
    trade_history_count: int = 10
    max_conversation_turns: int = 50


class SystemOperator:
    """시스템 운영 LLM 에이전트 — 멀티 세션 오케스트레이션 전용.

    직접 매매하지 않는다. 매매는 각 세션(TradingSession)의
    Strategy → Trader 단일 경로. 세션 수명 주기는 SessionManager가 담당한다.
    """

    DEFAULT_STRATEGY = "BNH"

    def __init__(self, llm_client, config: dict, profile_store=None,
                 account_store=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.llm_client = llm_client
        self.config = config
        self.budget = config.get("budget", 500000)
        self.profile_store = profile_store
        self.account_store = account_store

        self.system_monitor = SystemMonitor(
            storage_path=config.get("monitor_storage_path", "output/monitor/"),
        )
        self.tool_router = ToolRouter(self.system_monitor)
        self.context_config = ContextConfig(**config.get("context", {}))
        self.conversation_history = []
        self.strategy_knowledge = self._load_strategy_knowledge(
            config.get("strategy_files", [])
        )
        self.session_manager = None
        self.default_strategy_used = False

    # ------------------------------------------------------------------
    # 구성
    # ------------------------------------------------------------------
    def setup(self):
        """SessionManager 구성 + default 세션 생성 + Tool 등록. Controller가 호출."""
        from ..session_manager import SessionManager

        self.session_manager = SessionManager(
            account_store=self.account_store,
            llm_client=self.llm_client,
            system_monitor=self.system_monitor,
        )
        self.default_strategy_used = not self.config.get("strategy")
        result = self.session_manager.create_session(
            self._config_to_profile(), name=SessionManager.DEFAULT_SESSION)
        if not result.get("success"):
            raise ValueError(result.get("error"))
        self._register_tools()

    def _config_to_profile(self) -> dict:
        cfg = self.config
        profile = {"name": "default"}
        mapping = {
            "exchange": "exchange", "currency": "currency", "budget": "budget",
            "virtual": "virtual", "interval": "term", "strategy": "strategy",
            "strategy_params": "strategy_params", "safety": "safety",
            "account": "account",
        }
        for config_key, profile_key in mapping.items():
            if cfg.get(config_key) is not None:
                profile[profile_key] = cfg[config_key]
        profile.setdefault("strategy", self.DEFAULT_STRATEGY)
        return profile

    def _register_tools(self):
        from .tools.market_data_tool import MarketDataTool
        from .tools.portfolio_tool import PortfolioTool
        from .tools.trade_history_tool import TradeHistoryTool
        from .tools.performance_tool import PerformanceTool

        self.tool_router.register(MarketDataTool(self.session_manager))
        self.tool_router.register(PortfolioTool(self.session_manager))
        self.tool_router.register(TradeHistoryTool(self.system_monitor))
        self.tool_router.register(PerformanceTool(self.session_manager))

        from .tools.orchestration_tools import (
            ListStrategiesTool, DescribeStrategyTool, SelectStrategyTool,
            StartTradingTool, StopTradingTool, GetStatusTool,
        )
        self.tool_router.register(ListStrategiesTool())
        self.tool_router.register(DescribeStrategyTool())
        self.tool_router.register(SelectStrategyTool(self))
        self.tool_router.register(StartTradingTool(self))
        self.tool_router.register(StopTradingTool(self))
        self.tool_router.register(GetStatusTool(self))

        if self.profile_store is not None:
            from .tools.profile_tools import (
                ListProfilesTool, DescribeProfileTool, CreateProfileTool,
                UpdateProfileTool, DeleteProfileTool, SwitchProfileTool,
            )
            self.tool_router.register(ListProfilesTool(self.profile_store))
            self.tool_router.register(DescribeProfileTool(self.profile_store))
            self.tool_router.register(CreateProfileTool(self.profile_store))
            self.tool_router.register(UpdateProfileTool(self.profile_store))
            self.tool_router.register(DeleteProfileTool(self.profile_store))
            self.tool_router.register(SwitchProfileTool(self.profile_store, self))

        if self.account_store is not None:
            from .tools.account_tools import (
                RegisterAccountTool, ListAccountsTool, DeleteAccountTool,
            )
            self.tool_router.register(RegisterAccountTool(self.account_store))
            self.tool_router.register(ListAccountsTool(self.account_store))
            self.tool_router.register(DeleteAccountTool(
                self.account_store, self.session_manager))

        from .tools.session_tools import (
            CreateSessionTool, StartSessionTool, StopSessionTool,
            RemoveSessionTool, ListSessionsTool, ComparePerformanceTool,
        )
        self.tool_router.register(StartSessionTool(self.session_manager))
        self.tool_router.register(StopSessionTool(self.session_manager))
        self.tool_router.register(RemoveSessionTool(self.session_manager))
        self.tool_router.register(ListSessionsTool(self.session_manager))
        self.tool_router.register(ComparePerformanceTool(self.session_manager))
        if self.profile_store is not None:
            self.tool_router.register(CreateSessionTool(
                self.profile_store, self.session_manager))

    # ------------------------------------------------------------------
    # 레거시 위임 (default 세션)
    # ------------------------------------------------------------------
    def default_session(self):
        return self.session_manager.get_session("default")

    def default_strategy(self):
        try:
            return self.default_session().profile.get("strategy")
        except ValueError:
            return None

    def select_strategy(self, code: str) -> dict:
        previous = self.config.get("strategy")
        self.config["strategy"] = code
        result = self.session_manager.replace_session(
            "default", self._config_to_profile())
        if not result.get("success"):
            self.config["strategy"] = previous
            return result
        self.default_strategy_used = False
        return {"success": True, "strategy": code}

    def start_trading(self) -> dict:
        result = self.session_manager.start_session("default")
        if result.get("success") and self.default_strategy_used:
            result["strategy"] = self.default_strategy()
            result["note"] = "전략이 지정되지 않아 기본 전략(BNH)으로 시작했습니다"
        return result

    def stop_trading(self) -> dict:
        return self.session_manager.stop_session("default")

    def apply_profile(self, profile: dict) -> dict:
        # 현재 config를 기반으로 요청 프로파일을 오버레이 — 미지정 키는
        # 기존 설정을 상속한다 (가상→실거래 무언 전환 방지)
        effective = self._config_to_profile()
        for key in ("exchange", "currency", "budget", "virtual", "term",
                    "strategy", "strategy_params", "safety", "account"):
            if key in profile:
                effective[key] = profile[key]
        effective["name"] = "default"
        result = self.session_manager.replace_session("default", effective)
        if result.get("success"):
            # config를 유효 프로파일에 맞춰 동기화 (레거시 get_status 일관성)
            for key in ("exchange", "currency", "budget", "virtual",
                        "strategy", "strategy_params", "safety", "account"):
                if key in effective:
                    self.config[key] = effective[key]
            if "term" in effective:
                self.config["interval"] = effective["term"]
            self.budget = self.config.get("budget", self.budget)
            self.default_strategy_used = not self.config.get("strategy")
            result["note"] = ("프로파일이 default 세션에 적용되었습니다. "
                              "매매를 재개하려면 start_trading을 호출하세요.")
        return result

    def get_status(self, session=None) -> dict:
        if session:
            try:
                return self.session_manager.get_session_status(session)
            except ValueError as err:
                return {"error": str(err)}
        return {
            "sessions": self.session_manager.list_sessions(),
            "accounts": {
                alias: guard.get_status()
                for alias, guard in self.session_manager.account_guards.items()
            },
            "llm_usage": self.system_monitor.get_llm_usage(),
        }

    def shutdown(self):
        if self.session_manager is not None:
            self.session_manager.stop_all()

    # ------------------------------------------------------------------
    # 대화 (LlmOperator에서 이관)
    # ------------------------------------------------------------------
    def chat(self, message: str) -> str:
        self.conversation_history.append({"role": "user", "content": message})
        response_text = self._execute_llm_loop()
        self.conversation_history.append(
            {"role": "assistant", "content": response_text})
        self._trim_conversation_history()
        return response_text

    def _execute_llm_loop(self) -> str:
        system_prompt = self._build_system_prompt()
        tools = self.tool_router.get_tool_schemas()
        messages = list(self.conversation_history)

        while True:
            response = self.llm_client.create_message(system_prompt, messages, tools)
            self.system_monitor.log_llm_interaction(
                request={"messages": messages[-1:]},
                response_text=response.text,
                usage=response.usage,
            )
            if not response.has_tool_calls:
                return response.text

            tool_results_content = []
            for tool_call in response.tool_calls:
                result = self.tool_router.execute(tool_call)
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": str(result.to_dict()),
                })
            assistant_content = []
            if response.text:
                assistant_content.append({"type": "text", "text": response.text})
            assistant_content.extend(
                {"type": "tool_use", "id": tc.id, "name": tc.name, "input": tc.arguments}
                for tc in response.tool_calls
            )
            messages.append({"role": "assistant", "content": assistant_content})
            messages.append({"role": "user", "content": tool_results_content})

    def _build_system_prompt(self) -> str:
        parts = [
            "당신은 암호화폐 자동매매 시스템의 운영 에이전트입니다.",
            "직접 매매하지 않습니다. 매매는 각 세션의 전략이 고정 주기로 수행합니다.",
            "여러 세션(전략×계좌×심볼)을 병렬로 운영할 수 있습니다.",
            "제공된 Tool로 계좌를 등록하고, 프로파일로 세션을 생성·시작·중지하고,",
            "세션별 상태와 성과를 확인·비교하세요.",
            "위험한 변경(실거래 세션 시작/교체/제거)은 실행 전에 사용자에게 확인하세요.",
            "API 키 값은 절대 묻지도 저장하지도 마세요 — 환경변수 이름만 다룹니다.",
            "",
        ]
        if self.strategy_knowledge:
            parts.append("## 참고 전략 지식")
            parts.append(self.strategy_knowledge)
            parts.append("")
        parts.append("## 세션 현황")
        for s in self.session_manager.list_sessions():
            mode = "가상" if s["virtual"] else f"실거래({s['account']})"
            parts.append(
                f"- {s['name']}: {s['strategy']} / {s['exchange']} {s['currency']}"
                f" / 예산 {(s['budget'] or 0):,.0f} / {mode} / 상태 {s['state']}")
        return "\n".join(parts)

    def _trim_conversation_history(self):
        max_messages = self.context_config.max_conversation_turns * 2
        if len(self.conversation_history) > max_messages:
            self.conversation_history = self.conversation_history[-max_messages:]

    def _load_strategy_knowledge(self, strategy_files: list) -> str:
        parts = []
        base_dir = os.path.join(os.path.dirname(__file__), "..", "strategies")
        for filename in strategy_files:
            filepath = os.path.join(base_dir, filename)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    parts.append(f.read())
            except FileNotFoundError:
                self.logger.warning(f"Strategy file not found: {filepath}")
        return "\n\n---\n\n".join(parts)
