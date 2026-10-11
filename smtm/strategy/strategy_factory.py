from .strategy_bnh import StrategyBuyAndHold
from .strategy_rsi import StrategyRsi
from .strategy_sma import StrategySma
from .strategy_llm import StrategyLlm


class StrategyFactory:
    """Strategy 정보 조회 및 생성을 담당하는 Factory 클래스"""

    STRATEGY_LIST = [
        StrategyBuyAndHold,
        StrategyRsi,
        StrategySma,
        StrategyLlm,
    ]

    @staticmethod
    def create(code, llm_client=None, usage_observer=None):
        """Create a strategy; only LLM receives the client and optional usage observer."""
        for strategy in StrategyFactory.STRATEGY_LIST:
            if strategy.CODE == code:
                if strategy is StrategyLlm:
                    return StrategyLlm(llm_client=llm_client, usage_observer=usage_observer)
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
