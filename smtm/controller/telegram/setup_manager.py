"""
Trading Setup Manager
거래 설정 관리 담당 클래스

Handles state management and validation during trading setup process.
거래 설정 과정의 상태 관리와 검증을 담당합니다.
"""

from typing import Optional, Dict, Any, List, Tuple
from ...log_manager import LogManager
from ...config import Config
from ...data.data_provider_factory import DataProviderFactory
from ...strategy.strategy_factory import StrategyFactory
from ...trader.upbit_trader import UpbitTrader
from ...trader.bithumb_trader import BithumbTrader
from ...trader.demo_trader import DemoTrader


class TradingSetupManager:
    """
    Trading Setup Manager Class
    거래 설정 관리를 담당하는 클래스

    Manages trading setup state and validation.
    거래 설정 상태 관리와 검증을 담당합니다.
    """

    AVAILABLE_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    UPBIT_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    BITHUMB_CURRENCY = ["BTC", "ETH"]

    def __init__(self, is_demo: bool = False):
        """
        Initialize Trading Setup Manager
        거래 설정 매니저 초기화

        Args:
            is_demo: Whether to run in demo mode / 데모 모드 실행 여부
        """
        self.logger = LogManager.get_logger("TradingSetupManager")
        self.is_demo = is_demo

        # Setup state
        # 설정 상태
        self.budget: Optional[float] = None
        self.currency: Optional[str] = None
        self.data_provider: Optional[Any] = None
        self.trader: Optional[Any] = None
        self.strategy: Optional[Any] = None

        # Setup options
        # 설정 옵션들
        self.strategies: List[Dict[str, Any]] = []
        self.data_providers: List[Dict[str, Any]] = []
        self._update_strategies()
        self._update_data_providers()

    def _update_strategies(self) -> None:
        """
        Update available strategies list
        사용 가능한 전략 목록을 업데이트합니다.
        """
        self.strategies = []
        for idx, strategy in enumerate(StrategyFactory.get_all_strategy_info()):
            self.strategies.append(
                {
                    "name": f"{idx}. {strategy['name']}",
                    "selector": [
                        f"{idx}. {strategy['name']}".upper(),
                        f"{idx}",
                        f"{strategy['name']}".upper(),
                        f"{strategy['code']}",
                    ],
                    "builder": strategy["class"],
                }
            )

    def _update_data_providers(self) -> None:
        """
        Update available data providers list
        사용 가능한 데이터 프로바이더 목록을 업데이트합니다.
        """
        self.data_providers = []
        for idx, dp in enumerate(DataProviderFactory.get_all_strategy_info()):
            self.data_providers.append(
                {
                    "name": f"{idx}. {dp['name']}",
                    "selector": [
                        f"{idx}. {dp['name']}".upper(),
                        f"{idx}",
                        f"{dp['name']}".upper(),
                        f"{dp['code']}",
                    ],
                    "builder": dp["class"],
                }
            )

    def reset_setup(self) -> None:
        """
        Reset setup configuration
        설정을 초기화합니다.
        """
        self.budget = None
        self.currency = None
        self.data_provider = None
        self.trader = None
        self.strategy = None

    def validate_budget(self, command: str) -> Tuple[bool, Optional[float]]:
        """
        Validate budget setting
        예산 설정을 검증합니다.

        Args:
            command: Budget command string / 예산 명령어 문자열

        Returns:
            Tuple of (is_valid, budget_value) / (유효성, 예산값) 튜플
        """
        try:
            budget = int(command)
            if budget <= 0:
                return False, None
            return True, budget
        except ValueError:
            self.logger.info(f"invalid budget {command}")
            return False, None

    def validate_currency(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validate currency setting
        화폐 설정을 검증합니다.

        Args:
            command: Currency command string / 화폐 명령어 문자열

        Returns:
            Tuple of (is_valid, currency) / (유효성, 화폐) 튜플
        """
        currency = command.upper()
        if currency in self.AVAILABLE_CURRENCY:
            return True, currency
        return False, None

    def validate_data_provider(self, command: str) -> Tuple[bool, Optional[Any]]:
        """
        Validate data provider setting
        데이터 프로바이더 설정을 검증합니다.

        Args:
            command: Data provider command string / 데이터 프로바이더 명령어 문자열

        Returns:
            Tuple of (is_valid, data_provider) / (유효성, 데이터프로바이더) 튜플
        """
        for dp_item in self.data_providers:
            if command.upper() in dp_item["selector"]:
                try:
                    data_provider = dp_item["builder"](
                        self.currency, interval=Config.candle_interval
                    )
                    return True, data_provider
                except UserWarning as err:
                    self.logger.error(f"invalid data provider: {err}")
                    return False, None
        return False, None

    def validate_exchange(self, command: str) -> Tuple[bool, Optional[str]]:
        """
        Validate exchange setting
        거래소 설정을 검증합니다.

        Args:
            command: Exchange command string / 거래소 명령어 문자열

        Returns:
            Tuple of (is_valid, exchange) / (유효성, 거래소) 튜플
        """
        exchanges = {
            "1. UPBIT": "UPBIT",
            "1": "UPBIT",
            "UPBIT": "UPBIT",
            "2. BITHUMB": "BITHUMB",
            "2": "BITHUMB",
            "BITHUMB": "BITHUMB",
        }
        exchange = exchanges.get(command.upper())

        if exchange is None:
            return False, None

        if self.currency in getattr(self, f"{exchange.upper()}_CURRENCY"):
            return True, exchange

        return False, None

    def validate_strategy(self, command: str) -> Tuple[bool, Optional[Any]]:
        """
        Validate strategy setting
        전략 설정을 검증합니다.

        Args:
            command: Strategy command string / 전략 명령어 문자열

        Returns:
            Tuple of (is_valid, strategy) / (유효성, 전략) 튜플
        """
        for s_item in self.strategies:
            if command.upper() in s_item["selector"]:
                strategy = s_item["builder"]()
                return True, strategy
        return False, None

    def set_budget(self, budget: float) -> None:
        """
        Set budget
        예산을 설정합니다.

        Args:
            budget: Budget amount / 예산 금액
        """
        self.budget = budget

    def set_currency(self, currency: str) -> None:
        """
        Set currency
        화폐를 설정합니다.

        Args:
            currency: Currency code / 화폐 코드
        """
        self.currency = currency

    def set_data_provider(self, data_provider: Any) -> None:
        """
        Set data provider
        데이터 프로바이더를 설정합니다.

        Args:
            data_provider: Data provider instance / 데이터 프로바이더 인스턴스
        """
        self.data_provider = data_provider

    def set_trader(self, exchange: str) -> None:
        """
        Set trader (exchange)
        거래소를 설정합니다.

        Args:
            exchange: Exchange name / 거래소 이름
        """
        class_name = f"{exchange.title()}Trader"  # e.g., UpbitTrader, BithumbTrader
        trader_class = DemoTrader if self.is_demo else globals().get(class_name)
        if trader_class:
            self.trader = trader_class(budget=self.budget, currency=self.currency)

    def set_strategy(self, strategy: Any) -> None:
        """
        Set strategy
        전략을 설정합니다.

        Args:
            strategy: Strategy instance / 전략 인스턴스
        """
        self.strategy = strategy

    def is_setup_complete(self) -> bool:
        """
        Check if setup is complete
        설정이 완료되었는지 확인합니다.

        Returns:
            True if all setup is complete, False otherwise / 모든 설정이 완료되면 True, 그렇지 않으면 False
        """
        return all(
            [
                self.budget is not None,
                self.currency is not None,
                self.data_provider is not None,
                self.trader is not None,
                self.strategy is not None,
            ]
        )

    def get_setup_summary(self) -> Dict[str, Any]:
        """
        Get setup summary
        설정 요약을 반환합니다.

        Returns:
            Dictionary containing setup summary / 설정 요약을 담은 딕셔너리
        """
        return {
            "budget": self.budget,
            "currency": self.currency,
            "data_provider": self.data_provider,
            "trader": self.trader,
            "strategy": self.strategy,
        }

    def get_strategies(self) -> List[Dict[str, Any]]:
        """
        Get available strategies list
        사용 가능한 전략 목록을 반환합니다.

        Returns:
            List of available strategies / 사용 가능한 전략 목록
        """
        return self.strategies

    def get_data_providers(self) -> List[Dict[str, Any]]:
        """
        Get available data providers list
        사용 가능한 데이터 프로바이더 목록을 반환합니다.

        Returns:
            List of available data providers / 사용 가능한 데이터 프로바이더 목록
        """
        return self.data_providers
