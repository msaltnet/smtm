from .upbit_trader import UpbitTrader
from .bithumb_trader import BithumbTrader
from .simulation_trader import SimulationTrader


class TraderFactory:
    """
    Trader 정보 조회 및 생성을 담당하는 Factory 클래스
    Factory class responsible for retrieving and creating Trader information
    """

    TRADER_LIST = [
        UpbitTrader,
        BithumbTrader,
    ]

    @staticmethod
    def create(code, budget=50000, currency="BTC", commission_ratio=0.0005,
               paper=False, account=None):
        if paper:
            return SimulationTrader(
                budget=budget,
                currency=currency,
                commission_ratio=commission_ratio,
            )

        for trader in TraderFactory.TRADER_LIST:
            if trader.CODE == code:
                kwargs = {
                    "budget": budget,
                    "currency": currency,
                    "commission_ratio": commission_ratio,
                }
                if account:
                    kwargs["access_key_env"] = account.get("access_key_env")
                    kwargs["secret_key_env"] = account.get("secret_key_env")
                return trader(**kwargs)
        return None

    @staticmethod
    def get_name(code):
        for trader in TraderFactory.TRADER_LIST:
            if trader.CODE == code:
                return trader.NAME
        return None

    @staticmethod
    def get_all_trader_info():
        all_trader = []
        for trader in TraderFactory.TRADER_LIST:
            all_trader.append(
                {
                    "name": trader.NAME,
                    "code": trader.CODE,
                    "class": trader,
                }
            )
        return all_trader
