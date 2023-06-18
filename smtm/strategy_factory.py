"""Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

from .strategy_bnh import StrategyBuyAndHold
from .strategy_sma_0 import StrategySma0
from .strategy_rsi import StrategyRsi
from .strategy_sma_ml import StrategySmaMl


class StrategyFactory:
    """Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

    STRATEGY_LIST = [StrategyBuyAndHold, StrategySma0, StrategyRsi, StrategySmaMl]

    @staticmethod
    def create(code):
        """code에 해당하는 Strategy 객체를 생성하여 반환"""
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy()
        return None

    @staticmethod
    def get_name(code):
        """code에 해당하는 Strategy 이름을 반환"""
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy.NAME
        return None

    @staticmethod
    def get_all_strategy_info():
        """전체 Strategy 정보를 반환"""
        all_strategy = []
        for strategy in StrategyFactory.STRATEGY_LIST:
            all_strategy.append({"name": strategy.NAME, "code": strategy.CODE, "class": strategy})
        return all_strategy
