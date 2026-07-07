from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .log_manager import LogManager


@dataclass
class TradingSession:
    """프로파일의 실행 인스턴스 — 자기 완결적 트레이딩 단위"""
    name: str
    profile: dict
    operator: object
    trader: object
    session_guard: object
    account: Optional[str]
    created_at: str

    @property
    def state(self):
        return self.operator.state


class SessionManager:
    """병렬 트레이딩 세션 관리자.

    세션 생성 검증(예산 합계 ≤ 실잔고, (계좌,심볼) 충돌 방지)과
    계좌별 AccountGuard 공유를 담당한다. 검증 실패 시 무부작용.
    생성/교체/제거는 단일 제어 스레드(SystemOperator)에서만 호출하는 것을 전제한다.
    """

    DEFAULT_SESSION = "default"
    LEGACY_ACCOUNT = "legacy"

    def __init__(self, account_store=None, llm_client=None, system_monitor=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.account_store = account_store
        self.llm_client = llm_client
        self.system_monitor = system_monitor
        self.sessions = {}        # name -> TradingSession
        self.account_guards = {}  # alias -> AccountGuard

    # ------------------------------------------------------------------
    # 생성/교체
    # ------------------------------------------------------------------
    def create_session(self, profile: dict, name=None) -> dict:
        from .profile_store import ProfileStore
        from .trader.trader_factory import TraderFactory

        name = name or profile.get("name") or self.DEFAULT_SESSION
        if name in self.sessions:
            return {"success": False, "error": f"이미 존재하는 세션입니다: {name}"}
        if not ProfileStore.NAME_PATTERN.match(str(name)):
            return {"success": False,
                    "error": "세션 이름은 영문/숫자/-/_ 1~64자여야 합니다"}

        exchange = profile.get("exchange", "UPB")
        currency = profile.get("currency", "BTC")
        try:
            budget = float(profile.get("budget", 500000))
        except (TypeError, ValueError):
            return {"success": False, "error": "올바르지 않은 예산 값입니다"}
        virtual = bool(profile.get("virtual", False))

        # --- 실거래 검증 (가상은 건너뜀) ---
        account = None
        guard_alias = None
        if not virtual:
            account_alias = profile.get("account")
            if account_alias:
                if self.account_store is None:
                    return {"success": False, "error": "계좌 저장소가 설정되지 않았습니다"}
                try:
                    account = self.account_store.load(account_alias)
                except ValueError as err:
                    return {"success": False, "error": str(err)}
                if account.get("exchange") != exchange:
                    return {"success": False,
                            "error": (f"계좌({account.get('exchange')})와 프로파일"
                                      f"({exchange})의 거래소가 일치하지 않습니다")}
                missing = self.account_store.missing_env_vars(account)
                if missing:
                    return {"success": False,
                            "error": f"키 환경변수 미설정: {', '.join(missing)}"}
                guard_alias = account_alias
            elif name == self.DEFAULT_SESSION:
                guard_alias = self.LEGACY_ACCOUNT  # 레거시 기본 env 사용
            else:
                return {"success": False,
                        "error": "실거래 세션에는 account(계좌 별칭)가 필요합니다"}

            # (계좌, 심볼) 충돌
            for session in self.sessions.values():
                if (session.account == guard_alias
                        and not session.profile.get("virtual")
                        and session.profile.get("currency", "BTC") == currency):
                    return {"success": False,
                            "error": (f"계좌 '{guard_alias}'의 {currency}은(는) "
                                      f"세션 '{session.name}'이 이미 운영 중입니다")}

        # --- Trader 생성 (실잔고 조회에 필요) ---
        # TraderFactory/Trader 생성자가 던지는 예외(예: 미지원 currency)도
        # 무부작용 보장을 위해 흡수한다 — replace_session의 원복 경로를 지키기 위함
        try:
            trader = TraderFactory.create(
                exchange, budget=budget, currency=currency,
                paper=virtual, account=account)
        except Exception as err:
            return {"success": False, "error": f"트레이더 생성 실패: {err}"}
        if trader is None:
            return {"success": False, "error": f"올바르지 않은 거래소 코드입니다: {exchange}"}

        if not virtual:
            account_guard = self.get_account_guard(guard_alias)
            if account is not None:  # legacy default는 실잔고 검증 생략
                try:
                    balance = float(trader.get_account_info().get("balance", 0))
                except Exception as err:
                    self._discard_trader(trader)
                    return {"success": False, "error": f"계좌 잔고 조회 실패: {err}"}
                if account_guard.total_allocated() + budget > balance:
                    self._discard_trader(trader)
                    return {"success": False,
                            "error": (f"계좌 잔고 부족: 할당 합계 "
                                      f"{account_guard.total_allocated() + budget:,.0f}"
                                      f" > 잔고 {balance:,.0f}")}
            verdict = account_guard.can_allocate(budget)
            if not verdict.allowed:
                self._discard_trader(trader)
                return {"success": False, "error": verdict.reason}

        # --- 나머지 컴포넌트 조립 ---
        # ValueError 외의 예외(예: 잘못된 safety 키로 인한 TypeError)도
        # 무부작용 보장을 위해 모두 흡수한다
        try:
            operator, session_guard = self._assemble(
                profile, name, trader,
                self.get_account_guard(guard_alias) if not virtual else None)
        except Exception as err:
            self._discard_trader(trader)
            return {"success": False, "error": f"세션 조립 실패: {err}"}

        if not virtual:
            self.get_account_guard(guard_alias).allocate(name, budget)

        self.sessions[name] = TradingSession(
            name=name,
            profile=dict(profile),
            operator=operator,
            trader=trader,
            session_guard=session_guard,
            account=guard_alias,
            created_at=datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self.logger.info(f"session created: {name}")
        return {"success": True, "session": name,
                "virtual": virtual, "strategy": profile.get("strategy")}

    def _assemble(self, profile, name, trader, account_guard):
        """DataProvider/Strategy/Analyzer/Guard/TradingOperator 조립.
        실패 시 ValueError (호출부가 trader 정리)"""
        from .data.data_provider_factory import DataProviderFactory
        from .strategy.strategy_factory import StrategyFactory
        from .trading_operator import TradingOperator
        from .analyzer import Analyzer
        from .config import Config
        from .llm.safety_guard import SafetyGuard, SafetyConfig
        from .llm.account_guard import CompositeSafetyGuard

        exchange = profile.get("exchange", "UPB")
        currency = profile.get("currency", "BTC")
        budget = float(profile.get("budget", 500000))
        strategy_code = profile.get("strategy") or "BNH"

        data_provider = DataProviderFactory.create(
            exchange, currency=currency, interval=Config.candle_interval)
        if data_provider is None:
            raise ValueError(f"올바르지 않은 거래소 코드입니다: {exchange}")

        strategy = StrategyFactory.create(strategy_code, llm_client=self.llm_client)
        if strategy is None:
            raise ValueError(f"올바르지 않은 전략 코드입니다: {strategy_code}")

        analyzer = Analyzer(self.system_monitor, session_name=name)
        session_guard = SafetyGuard(SafetyConfig(
            initial_budget=budget, **profile.get("safety", {})))
        guard = session_guard
        if account_guard is not None:
            guard = CompositeSafetyGuard(session_guard, account_guard)

        operator = TradingOperator(
            interval=profile.get("term", 60), currency=currency)
        operator.initialize(
            data_provider, strategy, trader, analyzer, guard, budget=budget)
        return operator, session_guard

    def replace_session(self, name, profile) -> dict:
        """stopped 세션을 새 프로파일로 교체. 세션 가드 일일 카운터 승계.
        실패 시 기존 세션 유지."""
        old = self.sessions.get(name)
        if old is not None and old.state == "running":
            return {"success": False,
                    "error": "매매 중에는 세션을 교체할 수 없습니다. 먼저 중지하세요."}
        if old is not None:
            del self.sessions[name]
            if old.account:
                self.get_account_guard(old.account).release(name)

        try:
            result = self.create_session(profile, name=name)
        except Exception as err:
            # create_session은 원칙적으로 내부에서 모든 예외를 흡수하지만,
            # 방어적으로 한 겹 더 감싸 원복 경로가 반드시 실행되게 한다
            result = {"success": False, "error": f"세션 생성 실패: {err}"}
        if not result.get("success"):
            if old is not None:  # 원복
                self.sessions[name] = old
                if old.account:
                    self.get_account_guard(old.account).allocate(
                        name, float(old.profile.get("budget", 500000)))
            return result

        if old is not None:
            new_guard = self.sessions[name].session_guard
            new_guard.daily_trade_count = old.session_guard.daily_trade_count
            new_guard.daily_date = old.session_guard.daily_date
            self._discard_trader(old.trader)
        return result

    # ------------------------------------------------------------------
    # 수명 주기
    # ------------------------------------------------------------------
    def start_session(self, name) -> dict:
        try:
            session = self.get_session(name)
        except ValueError as err:
            return {"success": False, "error": str(err)}
        if session.state == "running":
            return {"success": False, "error": f"세션 '{name}'은 이미 매매 중입니다"}
        if not session.operator.start():
            return {"success": False, "error": f"세션 '{name}'을 시작할 수 없습니다"}
        return {"success": True, "session": name}

    def stop_session(self, name) -> dict:
        try:
            session = self.get_session(name)
        except ValueError as err:
            return {"success": False, "error": str(err)}
        if session.state != "running":
            return {"success": True, "note": f"세션 '{name}'은 매매 중이 아닙니다"}
        session.operator.stop()
        return {"success": True, "session": name}

    def remove_session(self, name) -> dict:
        try:
            session = self.get_session(name)
        except ValueError as err:
            return {"success": False, "error": str(err)}
        if session.state == "running":
            session.operator.stop()
        if session.account:
            self.get_account_guard(session.account).release(name)
        self._discard_trader(session.trader)
        del self.sessions[name]
        return {"success": True, "removed": name}

    def stop_all(self):
        for session in list(self.sessions.values()):
            if session.state == "running":
                try:
                    session.operator.stop()
                except Exception as err:
                    self.logger.error(f"session stop failed: {session.name}: {err}")

    # ------------------------------------------------------------------
    # 조회
    # ------------------------------------------------------------------
    def get_session(self, name) -> TradingSession:
        if name not in self.sessions:
            raise ValueError(f"세션을 찾을 수 없습니다: {name}")
        return self.sessions[name]

    def list_sessions(self) -> list:
        return [{
            "name": s.name,
            "state": s.state,
            "strategy": s.profile.get("strategy"),
            "account": s.account,
            "exchange": s.profile.get("exchange"),
            "currency": s.profile.get("currency"),
            "budget": s.profile.get("budget"),
            "virtual": bool(s.profile.get("virtual", False)),
        } for s in self.sessions.values()]

    def get_session_status(self, name) -> dict:
        session = self.get_session(name)
        return {
            "name": session.name,
            "state": session.state,
            "profile": dict(session.profile),
            "account": session.account,
            "created_at": session.created_at,
            "safety": session.operator.safety_guard.get_status(),
            "performance": session.operator.get_score(),
        }

    def get_performance(self, name) -> dict:
        session = self.get_session(name)
        report = {"session": name, **session.operator.get_score()}
        if self.system_monitor is not None:
            report["total_trades"] = len(
                self.system_monitor.get_trade_log(session=name))
        return report

    def compare_performance(self) -> list:
        result = []
        for s in self.sessions.values():
            row = {
                "session": s.name,
                "state": s.state,
                "strategy": s.profile.get("strategy"),
                "virtual": bool(s.profile.get("virtual", False)),
                **s.operator.get_score(),
            }
            if self.system_monitor is not None:
                row["total_trades"] = len(
                    self.system_monitor.get_trade_log(session=s.name))
            result.append(row)
        return result

    def get_account_guard(self, alias):
        from .llm.account_guard import AccountGuard
        if alias not in self.account_guards:
            self.account_guards[alias] = AccountGuard()
        return self.account_guards[alias]

    @staticmethod
    def _discard_trader(trader):
        """검증 실패로 버려지는 trader의 워커 정리 (무부작용 보장)"""
        worker = getattr(trader, "worker", None)
        if worker is not None:
            worker.stop()
