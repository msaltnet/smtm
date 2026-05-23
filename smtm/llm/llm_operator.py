import os
import threading
from dataclasses import dataclass
from ..log_manager import LogManager
from ..worker import Worker
from .llm_client import LlmClient, LlmResponse
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


class LlmOperator:
    """LLM 기반 자율 트레이딩 오퍼레이터"""

    def __init__(self, llm_client: LlmClient, config: dict):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.llm_client = llm_client
        self.config = config
        self.state = "ready"
        self.interval = config.get("interval", 60)
        self.budget = config.get("budget", 500000)

        # 컴포넌트 초기화
        safety_config = SafetyConfig(
            initial_budget=self.budget,
            **config.get("safety", {}),
        )
        self.safety_guard = SafetyGuard(safety_config)
        self.system_monitor = SystemMonitor(
            storage_path=config.get("monitor_storage_path", "output/monitor/"),
        )
        self.tool_router = ToolRouter(self.safety_guard, self.system_monitor)
        self.context_config = ContextConfig(**config.get("context", {}))

        # 대화 관리
        self.conversation_history = []
        self.strategy_knowledge = self._load_strategy_knowledge(
            config.get("strategy_files", [])
        )

        # 타이머
        self.timer = None
        self.is_timer_running = False
        self.worker = Worker("LlmOperator-Worker")

        # DataProvider (setup_tools에서 설정)
        self.data_provider = None
        self.trader = None
        self.last_market_data = None

    def setup_tools(self, data_provider=None, trader=None):
        """Tool 등록을 위한 설정. Controller가 호출."""
        from .tools.market_data_tool import MarketDataTool
        from .tools.trade_tool import TradeTool
        from .tools.portfolio_tool import PortfolioTool
        from .tools.trade_history_tool import TradeHistoryTool
        from .tools.performance_tool import PerformanceTool

        if data_provider:
            self.data_provider = data_provider
            self.tool_router.register(MarketDataTool(data_provider))

        if trader:
            self.trader = trader
            self.tool_router.register(TradeTool(trader, self.system_monitor))
            self.tool_router.register(PortfolioTool(trader))
            self.tool_router.register(PerformanceTool(
                self.system_monitor, trader, self.budget,
            ))

        self.tool_router.register(TradeHistoryTool(self.system_monitor))

    def chat(self, message: str) -> str:
        """단일 인터페이스 — 사용자 요청 및 주기적 판단 모두 처리"""
        if self.last_market_data:
            self._sync_trader_quote(self.last_market_data)

        self.conversation_history.append({"role": "user", "content": message})

        response_text = self._execute_llm_loop()

        self.conversation_history.append({"role": "assistant", "content": response_text})
        self._trim_conversation_history()
        return response_text

    def start_trading(self):
        """매매 시작"""
        if self.state == "running":
            return
        self.state = "running"
        self.worker.start()
        self._start_timer()
        self.logger.info("===== LlmOperator Start =====")

    def stop_trading(self):
        """매매 중지"""
        if self.timer is not None:
            self.timer.cancel()
        self.is_timer_running = False
        self.state = "stopped"
        self.worker.stop()
        self.logger.info("===== LlmOperator Stop =====")

    def _execute_llm_loop(self) -> str:
        """LLM Tool Use 루프"""
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

            # Tool Use 처리
            tool_results_content = []
            for tool_call in response.tool_calls:
                result = self.tool_router.execute(tool_call)
                if tool_call.name == "get_market_data" and result.success:
                    self.last_market_data = result.data
                    self._sync_trader_quote(result.data)
                tool_results_content.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": str(result.to_dict()),
                })

            # 대화에 tool_use와 tool_result 추가
            messages.append({"role": "assistant", "content": response.tool_calls})
            messages.append({"role": "user", "content": tool_results_content})

    def _on_timer(self):
        """주기적 판단 요청"""
        self.is_timer_running = False
        if self.state != "running":
            return

        try:
            market_data = None
            if self.data_provider:
                market_data = self.data_provider.get_info()
                self.system_monitor.log_market_data(market_data)
                self.last_market_data = market_data
                self._sync_trader_quote(market_data)

            prompt = self._build_periodic_prompt(market_data)
            self.chat(prompt)
        except Exception as e:
            self.logger.error(f"Periodic trading error: {e}")

        self._start_timer()

    def _start_timer(self):
        if self.is_timer_running or self.state != "running":
            return
        self.timer = threading.Timer(self.interval, self._on_timer)
        self.timer.start()
        self.is_timer_running = True

    def _sync_trader_quote(self, market_data) -> None:
        """Push the latest candle close to paper traders that support quote injection."""
        if not self.trader or not hasattr(self.trader, "update_quote") or not market_data:
            return

        candles = market_data if isinstance(market_data, list) else [market_data]
        for item in candles:
            if not isinstance(item, dict) or item.get("type") != "primary_candle":
                continue

            currency = item.get("market", self.config.get("currency", "BTC"))
            price = item.get("closing_price")
            if currency and price is not None:
                self.trader.update_quote(currency, price)
            return

    def _build_system_prompt(self) -> str:
        parts = [
            "당신은 암호화폐 자동 매매 에이전트입니다.",
            "제공되는 Tool을 사용하여 시장을 분석하고, 매매 판단을 내리세요.",
            "리스크 관리를 최우선으로 고려하고, 확신이 없으면 거래하지 마세요.",
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
        return "\n".join(parts)

    def _build_periodic_prompt(self, market_data) -> str:
        parts = ["[주기적 시장 판단 요청]"]
        if market_data:
            parts.append(f"현재 시장 데이터: {market_data}")
        parts.append("시장 상황을 분석하고, 필요시 매매를 실행하세요.")
        parts.append("거래가 불필요하다고 판단하면 '관망'으로 응답하세요.")
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
