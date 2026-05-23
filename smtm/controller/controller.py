import os
import signal
from ..config import Config
from ..log_manager import LogManager
from ..llm.llm_operator import LlmOperator
from ..llm.claude_llm_client import ClaudeLlmClient
from ..trader.trader_factory import TraderFactory
from ..data.data_provider_factory import DataProviderFactory


class Controller:
    """LLM 기반 CLI 컨트롤러"""

    MAIN_STATEMENT = "메시지를 입력하세요 (q: 종료): "

    def __init__(
        self,
        interval=60,
        budget=500000,
        currency="BTC",
        exchange="UPB",
        paper=False,
    ):
        self.logger = LogManager.get_logger("Controller")
        self.terminating = False
        self.interval = float(interval)
        self.budget = int(budget)
        self.currency = currency
        self.exchange = exchange
        self.paper = paper
        LogManager.set_stream_level(Config.operation_log_level)

    def main(self):
        api_key = os.environ.get("SMTM_LLM_API_KEY", "")
        if not api_key:
            print("SMTM_LLM_API_KEY 환경변수를 설정해주세요")
            return

        llm_client = ClaudeLlmClient(api_key=api_key)
        config = {
            "exchange": self.exchange,
            "currency": self.currency,
            "budget": self.budget,
            "interval": self.interval,
            "strategy_files": ["sma_crossover.md", "rsi_strategy.md", "buy_and_hold.md"],
        }
        operator = LlmOperator(llm_client, config)

        data_provider = DataProviderFactory.create(
            self.exchange, currency=self.currency, interval=Config.candle_interval
        )
        trader = TraderFactory.create(
            self.exchange,
            budget=self.budget,
            currency=self.currency,
            paper=self.paper,
        )
        if data_provider is None or trader is None:
            print(f"Invalid exchange code: {self.exchange}")
            return

        operator.setup_tools(data_provider=data_provider, trader=trader)

        print("##### smtm LLM trading system is initialized #####")
        print(f"exchange: {self.exchange}, currency: {self.currency}, budget: {self.budget}")
        if self.paper:
            print("!! PAPER TRADING MODE - no real orders will be placed")
        print("'start'를 입력하면 자동 매매가 시작됩니다")
        print("==============================")

        signal.signal(signal.SIGINT, lambda s, f: self._terminate(operator))
        signal.signal(signal.SIGTERM, lambda s, f: self._terminate(operator))

        while not self.terminating:
            try:
                message = input(self.MAIN_STATEMENT)
                if message.lower() in ("q", "quit", "exit", "terminate"):
                    self._terminate(operator)
                    break
                if message.lower() == "start":
                    operator.start_trading()
                    print("자동 매매가 시작되었습니다")
                    continue
                if message.lower() == "stop":
                    operator.stop_trading()
                    print("자동 매매가 중지되었습니다")
                    continue
                response = operator.chat(message)
                print(f"\n{response}\n")
            except EOFError:
                break

    def _terminate(self, operator):
        print("프로그램 종료 중.....")
        operator.stop_trading()
        self.terminating = True
        print("Good Bye~")
