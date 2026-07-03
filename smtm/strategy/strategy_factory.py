from .strategy_bnh import StrategyBuyAndHold
from .strategy_rsi import StrategyRsi
from .strategy_sma import StrategySma


class StrategyFactory:
    """Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

    STRATEGY_LIST = [
        StrategyBuyAndHold,
        StrategyRsi,
        StrategySma,
    ]

    @staticmethod
    def create(code, llm_client=None):
        """code에 해당하는 Strategy 객체를 생성하여 반환. llm_client는 LLM 전략에서만 사용"""
        del llm_client  # LLM 전략 등록 시(Task 9) 사용
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy()
        return None

    @staticmethod
    def get_name(code):
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                return strategy.NAME
        return None

    @staticmethod
    def get_all_strategy_info():
        return [
            {"name": s.NAME, "code": s.CODE, "class": s}
            for s in StrategyFactory.STRATEGY_LIST
        ]
