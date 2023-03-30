"""Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

from . import StrategyBuyAndHold, StrategySma0, StrategyRsi


class StrategyFactory:
    """Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

    STRATEGY_LIST = [StrategyBuyAndHold, StrategySma0, StrategyRsi]

    @staticmethod
    def create(code):
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy()

    @staticmethod
    def get_name(code):
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy.NAME

    @staticmethod
    def get_all_strategy_info():
        all = []
        for strategy in StrategyFactory.STRATEGY_LIST:
            all.append({"name": strategy.NAME, "code": strategy.CODE, "class": strategy})
        return all