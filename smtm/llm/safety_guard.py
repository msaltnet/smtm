from dataclasses import dataclass
from datetime import date
from typing import Optional
from ..log_manager import LogManager


@dataclass
class SafetyConfig:
    """안전장치 설정"""
    max_trade_amount: float = 100000
    max_daily_trades: int = 20
    max_loss_ratio: float = -0.20
    initial_budget: float = 500000


@dataclass
class SafetyResult:
    """안전장치 검증 결과"""
    allowed: bool
    reason: Optional[str] = None


class SafetyGuard:
    """규칙 기반 안전장치 — Tool 실행 전 검증, LLM 우회 불가"""

    TRADE_TOOLS = ("execute_trade",)

    def __init__(self, config: SafetyConfig):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.config = config
        self.daily_trade_count = 0
        self.daily_date = date.today()
        self.current_value = config.initial_budget

    def check(self, tool_call) -> SafetyResult:
        """Tool 호출 사전 검증. 거래 Tool만 검증, 나머지는 통과."""
        if tool_call.name not in self.TRADE_TOOLS:
            return SafetyResult(allowed=True)

        self._reset_daily_if_needed()

        # 1회 최대 거래금액 검증
        trade_amount = tool_call.arguments.get("price", 0) * tool_call.arguments.get("amount", 0)
        if trade_amount > self.config.max_trade_amount:
            reason = f"1회 최대 거래금액 초과 ({trade_amount:,.0f} > {self.config.max_trade_amount:,.0f})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        # 일일 거래횟수 제한
        if self.daily_trade_count >= self.config.max_daily_trades:
            reason = f"일일 거래횟수 초과 ({self.daily_trade_count}/{self.config.max_daily_trades})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        # 누적 손실 한도
        loss_ratio = (self.current_value - self.config.initial_budget) / self.config.initial_budget
        if loss_ratio < self.config.max_loss_ratio:
            reason = f"손실 한도 초과 ({loss_ratio:.1%} < {self.config.max_loss_ratio:.1%})"
            self.logger.warning(reason)
            return SafetyResult(allowed=False, reason=reason)

        return SafetyResult(allowed=True)

    def record_trade(self, result: dict):
        """거래 완료 후 카운터 업데이트"""
        self._reset_daily_if_needed()
        self.daily_trade_count += 1

    def update_portfolio_value(self, value: float):
        """포트폴리오 가치 업데이트"""
        self.current_value = value

    def get_status(self) -> dict:
        self._reset_daily_if_needed()
        loss_ratio = (self.current_value - self.config.initial_budget) / self.config.initial_budget
        return {
            "daily_trades": self.daily_trade_count,
            "daily_limit": self.config.max_daily_trades,
            "current_loss_ratio": round(loss_ratio, 4),
            "max_loss_ratio": self.config.max_loss_ratio,
            "trading_allowed": self.check(
                type("FakeCall", (), {"name": "execute_trade", "arguments": {"price": 1, "amount": 1}})()
            ).allowed,
        }

    def _reset_daily_if_needed(self):
        today = date.today()
        if self.daily_date != today:
            self.daily_trade_count = 0
            self.daily_date = today
