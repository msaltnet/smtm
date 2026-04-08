import os
from IPython.display import display
from ..config import Config
from ..log_manager import LogManager
from ..llm.llm_operator import LlmOperator
from ..llm.claude_llm_client import ClaudeLlmClient
from ..trader.trader_factory import TraderFactory
from ..data.data_provider_factory import DataProviderFactory


class JptController:
    """Jupyter notebook용 LLM 기반 자동 거래 시스템 컨트롤러"""

    def __init__(self, interval=60, budget=500000, currency="BTC"):
        self.interval = interval
        self.budget = budget
        self.currency = currency
        self.operator = None
        self.logger = LogManager.get_logger("JptController")

    def initialize(self, interval=60, budget=500000, exchange="UPB"):
        self.interval = interval
        self.budget = budget

        api_key = os.environ.get("SMTM_LLM_API_KEY", "")
        if not api_key:
            print("SMTM_LLM_API_KEY 환경변수를 설정해주세요")
            return

        llm_client = ClaudeLlmClient(api_key=api_key)
        config = {
            "exchange": exchange,
            "currency": self.currency,
            "budget": self.budget,
            "interval": self.interval,
            "strategy_files": ["sma_crossover.md", "rsi_strategy.md", "buy_and_hold.md"],
        }
        self.operator = LlmOperator(llm_client, config)

        data_provider = DataProviderFactory.create(
            exchange, currency=self.currency, interval=Config.candle_interval
        )
        trader = TraderFactory.create(
            exchange, budget=self.budget, currency=self.currency
        )
        if data_provider is None or trader is None:
            raise UserWarning(f"Invalid exchange code! {exchange}")

        self.operator.setup_tools(data_provider=data_provider, trader=trader)
        print("##### smtm LLM trading is initialized #####")
        print(f"interval: {self.interval}, budget: {self.budget}")

    def start(self):
        if self.operator is None:
            print("초기화가 필요합니다")
            return
        self.operator.start_trading()
        print("자동 매매가 시작되었습니다")

    def stop(self):
        if self.operator is not None:
            self.operator.stop_trading()
            print("자동 매매가 중지되었습니다")

    def chat(self, message):
        if self.operator is None:
            print("초기화가 필요합니다")
            return
        response = self.operator.chat(message)
        print(response)
        return response

    @staticmethod
    def set_log_level(value):
        LogManager.set_stream_level(int(value))
        print(f"Log level set {value}")
