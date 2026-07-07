import os
import signal
from ..config import Config
from ..log_manager import LogManager
from ..llm.system_operator import SystemOperator
from ..llm.claude_llm_client import ClaudeLlmClient
from ..profile_store import ProfileStore
from ..account_store import AccountStore


class Controller:
    """LLM 기반 CLI 컨트롤러 — SystemOperator를 통해 시스템을 제어"""

    MAIN_STATEMENT = "메시지를 입력하세요 (q: 종료): "

    def __init__(
        self,
        interval=60,
        budget=500000,
        currency="BTC",
        exchange="UPB",
        paper=False,
        strategy="BNH",
    ):
        self.logger = LogManager.get_logger("Controller")
        self.terminating = False
        self.interval = float(interval)
        self.budget = int(budget)
        self.currency = currency
        self.exchange = exchange
        self.paper = paper
        self.strategy = strategy
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
            "virtual": self.paper,
            "strategy": self.strategy,
            "strategy_files": ["sma_crossover.md", "rsi_strategy.md", "buy_and_hold.md"],
        }
        operator = SystemOperator(llm_client, config,
                                  profile_store=ProfileStore(),
                                  account_store=AccountStore())
        try:
            operator.setup()
        except Exception as err:
            print(str(err))
            return

        print("##### smtm LLM trading system is initialized #####")
        print(f"exchange: {self.exchange}, currency: {self.currency}, "
              f"budget: {self.budget}, strategy: {self.strategy}")
        if self.paper:
            print("!! 가상거래 모드 - 실제 주문은 전송되지 않습니다")
        print("'start'를 입력하면 자동 매매가 시작됩니다")
        print("멀티 세션 지원 — 채팅으로 계좌 등록·세션 생성/시작이 가능합니다")
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
                    result = operator.start_trading()
                    print("자동 매매가 시작되었습니다" if result.get("success")
                          else f"시작 실패: {result.get('error')}")
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
        operator.shutdown()
        self.terminating = True
        print("Good Bye~")
