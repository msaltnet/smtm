import os
from ..log_manager import LogManager
from ..llm.system_operator import SystemOperator
from ..llm.claude_llm_client import ClaudeLlmClient


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
            "virtual": False,
            "strategy": "BNH",
            "strategy_files": ["sma_crossover.md", "rsi_strategy.md", "buy_and_hold.md"],
        }
        self.operator = SystemOperator(llm_client, config)
        self.operator.setup()
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
