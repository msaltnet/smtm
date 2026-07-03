import os
from dataclasses import dataclass
from ..log_manager import LogManager
from .tool_router import ToolRouter
from .safety_guard import SafetyGuard, SafetyConfig
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
    """시스템 운영 LLM 에이전트 — 오케스트레이션 전용.

    직접 매매하지 않는다. 매매는 TradingOperator의 Strategy → Trader 단일 경로.
    """

    DEFAULT_STRATEGY = "BNH"

    def __init__(self, llm_client, config: dict, profile_store=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.llm_client = llm_client
        self.config = config
        self.state = "ready"
        self.budget = config.get("budget", 500000)
        self.profile_store = profile_store

        self.system_monitor = SystemMonitor(
            storage_path=config.get("monitor_storage_path", "output/monitor/"),
        )
        self.tool_router = ToolRouter(self.system_monitor)
        self.context_config = ContextConfig(**config.get("context", {}))
        self.conversation_history = []
        self.strategy_knowledge = self._load_strategy_knowledge(
            config.get("strategy_files", [])
        )

        self.trading_operator = None
        self.data_provider = None
        self.trader = None
        self.safety_guard = None
        self.strategy_code = None
        self.default_strategy_used = False

    # ------------------------------------------------------------------
    # 구성
    # ------------------------------------------------------------------
    def setup(self):
        """트레이딩 컴포넌트 구성 + Tool 등록. Controller가 호출."""
        self._build_trading_components(rebuild_infra=True)

    def _build_trading_components(self, rebuild_infra=True):
        # 순환 import 방지를 위한 지역 import
        from ..data.data_provider_factory import DataProviderFactory
        from ..trader.trader_factory import TraderFactory
        from ..strategy.strategy_factory import StrategyFactory
        from ..trading_operator import TradingOperator
        from ..analyzer import Analyzer
        from ..config import Config

        cfg = self.config
        exchange = cfg.get("exchange", "UPB")
        currency = cfg.get("currency", "BTC")
        strategy_code = cfg.get("strategy") or self.DEFAULT_STRATEGY
        self.default_strategy_used = not cfg.get("strategy")

        if rebuild_infra or self.trader is None:
            self.data_provider = DataProviderFactory.create(
                exchange, currency=currency, interval=Config.candle_interval)
            self.trader = TraderFactory.create(
                exchange, budget=self.budget, currency=currency,
                paper=bool(cfg.get("virtual", False)))
            if self.data_provider is None or self.trader is None:
                raise ValueError(f"올바르지 않은 거래소 코드입니다: {exchange}")

        strategy = StrategyFactory.create(strategy_code, llm_client=self.llm_client)
        if strategy is None:
            raise ValueError(f"올바르지 않은 전략 코드입니다: {strategy_code}")

        analyzer = Analyzer(self.system_monitor)
        self.safety_guard = SafetyGuard(SafetyConfig(
            initial_budget=self.budget, **cfg.get("safety", {})))

        operator = TradingOperator(
            interval=cfg.get("interval", 60), currency=currency)
        operator.initialize(
            self.data_provider, strategy, self.trader, analyzer,
            self.safety_guard, budget=self.budget)
        self.trading_operator = operator
        self.strategy_code = strategy_code
        self._register_tools()

    def _register_tools(self):
        from .tools.market_data_tool import MarketDataTool
        from .tools.portfolio_tool import PortfolioTool
        from .tools.trade_history_tool import TradeHistoryTool
        from .tools.performance_tool import PerformanceTool

        self.tool_router.register(MarketDataTool(self.data_provider))
        self.tool_router.register(PortfolioTool(self.trader))
        self.tool_router.register(TradeHistoryTool(self.system_monitor))
        self.tool_router.register(PerformanceTool(
            self.system_monitor, self.trader, self.budget))

    # ------------------------------------------------------------------
    # 오케스트레이션 API (Tool과 Controller에서 호출)
    # ------------------------------------------------------------------
    def select_strategy(self, code: str) -> dict:
        if self._is_trading_running():
            return {"success": False,
                    "error": "매매 중에는 전략을 변경할 수 없습니다. 먼저 매매를 중지하세요."}
        previous = self.config.get("strategy")
        self.config["strategy"] = code
        try:
            self._build_trading_components(rebuild_infra=False)
        except ValueError as err:
            self.config["strategy"] = previous
            return {"success": False, "error": str(err)}
        return {"success": True, "strategy": code}

    def start_trading(self) -> dict:
        if self.trading_operator is None:
            return {"success": False, "error": "트레이딩 컴포넌트가 구성되지 않았습니다"}
        if self._is_trading_running():
            return {"success": False, "error": "이미 매매가 진행 중입니다"}
        started = self.trading_operator.start()
        if not started:
            return {"success": False, "error": "매매를 시작할 수 없습니다"}
        result = {"success": True, "strategy": self.strategy_code}
        if self.default_strategy_used:
            result["note"] = "전략이 지정되지 않아 기본 전략(BNH)으로 시작했습니다"
        return result

    def stop_trading(self) -> dict:
        if self.trading_operator is None or not self._is_trading_running():
            return {"success": True, "note": "매매가 진행 중이 아닙니다"}
        self.trading_operator.stop()
        return {"success": True}

    def get_status(self) -> dict:
        return {
            "trading_state": self.trading_operator.state if self.trading_operator else None,
            "strategy": self.strategy_code,
            "exchange": self.config.get("exchange"),
            "currency": self.config.get("currency"),
            "budget": self.budget,
            "virtual": bool(self.config.get("virtual", False)),
            "interval": self.config.get("interval", 60),
            "safety": self.safety_guard.get_status() if self.safety_guard else None,
            "llm_usage": self.system_monitor.get_llm_usage(),
        }

    def apply_profile(self, profile: dict) -> dict:
        was_running = self._is_trading_running()
        if was_running:
            self.trading_operator.stop()
        old_config = dict(self.config)
        old_budget = self.budget
        for key in ("exchange", "currency", "budget", "virtual", "term",
                    "strategy", "strategy_params", "safety"):
            if key in profile:
                config_key = "interval" if key == "term" else key
                self.config[config_key] = profile[key]
        self.budget = self.config.get("budget", self.budget)
        try:
            self._build_trading_components(rebuild_infra=True)
        except ValueError as err:
            # 현재 구성 유지: 스냅샷 복원 후 이전 구성으로 재구성
            self.config.clear()
            self.config.update(old_config)
            self.budget = old_budget
            self._build_trading_components(rebuild_infra=True)
            return {"success": False, "error": str(err)}
        return {"success": True, "profile": profile.get("name"),
                "was_running": was_running,
                "note": "프로파일이 적용되었습니다. 매매를 재개하려면 start_trading을 호출하세요."}

    def _is_trading_running(self) -> bool:
        return (self.trading_operator is not None
                and self.trading_operator.state == "running")

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
            "직접 매매하지 않습니다. 매매는 선택된 전략(Strategy)이 고정 주기로 수행합니다.",
            "제공된 Tool로 전략을 조회·선택하고, 매매를 시작/중지하고, 상태와 성과를 확인하고,",
            "프로파일(실행 프리셋)을 관리하세요.",
            "사용자의 요청을 정확히 파악하고, 위험한 변경(전략 전환, 프로파일 전환)은",
            "실행 전에 사용자에게 확인하세요.",
            "",
        ]
        if self.strategy_knowledge:
            parts.append("## 참고 전략 지식")
            parts.append(self.strategy_knowledge)
            parts.append("")
        parts.append("## 현재 설정")
        parts.append(f"- 거래소: {self.config.get('exchange', 'N/A')}")
        parts.append(f"- 통화: {self.config.get('currency', 'N/A')}")
        parts.append(f"- 초기 예산: {self.budget:,.0f}")
        parts.append(f"- 현재 전략: {self.strategy_code or 'N/A'}")
        parts.append(f"- 가상매매: {'예' if self.config.get('virtual') else '아니오'}")
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
