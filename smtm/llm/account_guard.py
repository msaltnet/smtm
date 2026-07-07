import threading
from dataclasses import dataclass
from datetime import date
from ..log_manager import LogManager
from .safety_guard import SafetyResult


@dataclass
class AccountGuardConfig:
    """계좌 수준 안전장치 설정"""
    max_daily_trades: int = 60
    max_total_allocation: float = 10_000_000


class AccountGuard:
    """계좌 수준 안전장치 — 같은 계좌의 모든 실거래 세션이 공유한다.

    세션 재생성/전환으로 카운터가 리셋되지 않는다 (LLM 우회 방지).
    여러 세션의 워커 스레드가 동시 접근하므로 Lock으로 보호한다.
    """

    def __init__(self, config=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.config = config or AccountGuardConfig()
        self._lock = threading.Lock()
        self.daily_trade_count = 0
        self.daily_date = date.today()
        self.allocations = {}  # session_name -> soft budget

    def check_request(self, request: dict) -> SafetyResult:
        if request.get("type") == "cancel":
            return SafetyResult(allowed=True)
        with self._lock:
            self._reset_daily_if_needed()
            if self.daily_trade_count >= self.config.max_daily_trades:
                reason = (f"계좌 일일 거래횟수 초과 "
                          f"({self.daily_trade_count}/{self.config.max_daily_trades})")
                self.logger.warning(reason)
                return SafetyResult(allowed=False, reason=reason)
        return SafetyResult(allowed=True)

    def record_trade(self, result):
        del result
        with self._lock:
            self._reset_daily_if_needed()
            self.daily_trade_count += 1

    def update_portfolio_value(self, value):
        """계좌 가드는 세션별 포트폴리오 가치를 추적하지 않는다 (후속: 통합 손실률)"""
        del value

    def can_allocate(self, amount: float) -> SafetyResult:
        with self._lock:
            total = sum(self.allocations.values()) + float(amount)
            if total > self.config.max_total_allocation:
                reason = (f"계좌 할당 총액 초과 "
                          f"({total:,.0f} > {self.config.max_total_allocation:,.0f})")
                self.logger.warning(reason)
                return SafetyResult(allowed=False, reason=reason)
        return SafetyResult(allowed=True)

    def allocate(self, session_name: str, amount: float):
        with self._lock:
            self.allocations[session_name] = float(amount)

    def release(self, session_name: str):
        with self._lock:
            self.allocations.pop(session_name, None)

    def total_allocated(self) -> float:
        with self._lock:
            return sum(self.allocations.values())

    def get_status(self) -> dict:
        with self._lock:
            self._reset_daily_if_needed()
            return {
                "daily_trades": self.daily_trade_count,
                "daily_limit": self.config.max_daily_trades,
                "total_allocated": sum(self.allocations.values()),
                "max_total_allocation": self.config.max_total_allocation,
                "allocations": dict(self.allocations),
            }

    def _reset_daily_if_needed(self):
        today = date.today()
        if self.daily_date != today:
            self.daily_trade_count = 0
            self.daily_date = today


class CompositeSafetyGuard:
    """세션 가드 + 계좌 가드 합성 — TradingOperator는 단일 가드 인터페이스만 본다"""

    def __init__(self, session_guard, account_guard):
        self.session_guard = session_guard
        self.account_guard = account_guard

    def check_request(self, request: dict) -> SafetyResult:
        for guard in (self.session_guard, self.account_guard):
            verdict = guard.check_request(request)
            if not verdict.allowed:
                return verdict
        return SafetyResult(allowed=True)

    def record_trade(self, result):
        self.session_guard.record_trade(result)
        self.account_guard.record_trade(result)

    def update_portfolio_value(self, value):
        self.session_guard.update_portfolio_value(value)

    def get_status(self) -> dict:
        return {
            "session": self.session_guard.get_status(),
            "account": self.account_guard.get_status(),
        }
