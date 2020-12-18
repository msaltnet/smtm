"""
Description for Package
"""
from .log_manager import LogManager
from .trading_request import TradingRequest
from .trading_result import TradingResult
from .trader import Trader
from .data_provider import DataProvider
from .operator import Operator
from .live_data_provider import LiveDataProvider
from .simulator_data_provider import SimulatorDataProvider
from .simulator_operator import SimulatorOperator
from .strategy_bnh import StrategyBuyAndHold

__all__ = [
    'LogManager',
    'TradingRequest',
    'TradingResult',
    'Trader',
    'SimulatorDataProvider',
    'Operator',
    'StrategyBuyAndHold',
    'SimulatorOperator']
__version__ = '0.1.0'