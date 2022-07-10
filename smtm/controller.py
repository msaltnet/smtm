"""시스템 운영 인터페이스로서 Operator를 사용해서 자동 거래 시스템을 컨트롤하는 Controller 클래스"""

import signal
from . import (
    LogManager,
    Analyzer,
    UpbitTrader,
    UpbitDataProvider,
    BithumbTrader,
    BithumbDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    StrategyRsi,
    Operator,
)


class Controller:
    """자동 거래 시스템 기본 컨트롤러"""

    MAIN_STATEMENT = "명령어를 입력하세요. (h: 도움말): "

    def __init__(
        self,
        interval=10,
        strategy=0,
        budget=50000,
        currency="BTC",
        is_bithumb=False,
    ):
        self.logger = LogManager.get_logger("Controller")
        self.terminating = False
        self.interval = float(interval)
        self.operator = Operator()
        self.budget = int(budget)
        self.is_initialized = False
        self.command_list = []
        self.create_command()
        self.is_bithumb = is_bithumb
        self.strategy = None
        self.currency = currency
        LogManager.set_stream_level(30)

        strategy_num = int(strategy)
        if strategy_num == 0:
            self.strategy = StrategyBuyAndHold()
        elif strategy_num == 1:
            self.strategy = StrategySma0()
        elif strategy_num == 2:
            self.strategy = StrategyRsi()
        else:
            raise UserWarning(f"Invalid Strategy! {self.strategy}")

    def create_command(self):
        """명령어 정보를 생성한다"""
        self.command_list = [
            {
                "guide": "{0:15}도움말 출력".format("h, help"),
                "cmd": ["help", "h"],
                "action": self.print_help,
            },
            {
                "guide": "{0:15}자동 거래 시작".format("r, run"),
                "cmd": ["run", "r"],
                "action": self.start,
            },
            {
                "guide": "{0:15}자동 거래 중지".format("s, stop"),
                "cmd": ["stop", "s"],
                "action": self.stop,
            },
            {
                "guide": "{0:15}프로그램 종료".format("t, terminate"),
                "cmd": ["terminate", "t"],
                "action": self.terminate,
            },
            {
                "guide": "{0:15}정보 조회".format("q, query"),
                "cmd": ["query", "q"],
                "action": self._on_query_command,
            },
        ]

    def main(self):
        """시작점이 되는 main 함수"""

        if self.is_bithumb:
            data_provider = BithumbDataProvider(currency=self.currency)
            trader = BithumbTrader(currency=self.currency, budget=self.budget)
        else:
            data_provider = UpbitDataProvider(currency=self.currency)
            trader = UpbitTrader(currency=self.currency, budget=self.budget)

        self.operator.initialize(
            data_provider,
            self.strategy,
            trader,
            Analyzer(),
            budget=self.budget,
        )

        self.operator.set_interval(self.interval)
        print("##### smtm is intialized #####")
        print(f"interval: {self.interval}, strategy: {self.strategy.NAME} , trader: {trader.NAME}")
        print("==============================")

        self.logger.info(
            f"interval: {self.interval}, strategy: {self.strategy.NAME} , trader: {trader.NAME}"
        )
        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

        while not self.terminating:
            try:
                key = input(self.MAIN_STATEMENT)
                self.logger.debug(f"Execute command {key}")
                self._on_command(key)
            except EOFError:
                break

    def print_help(self):
        """가이드 문구 출력"""
        print("명령어 목록 =================")
        for item in self.command_list:
            print(item["guide"])

    def _on_command(self, key):
        """커맨드 처리를 담당"""
        for cmd in self.command_list:
            if key.lower() in cmd["cmd"]:
                print(f"{cmd['cmd'][0].upper()} 명령어를 실행합니다.")
                cmd["action"]()
                return
        print("잘못된 명령어가 입력되었습니다")

    def _on_query_command(self):
        """조회 커맨드 처리"""
        value = input("무엇을 조회할까요? (ex. 1.state, 2.score, 3.result) :")
        key = value.lower()
        if key in ["state", "1"]:
            print(f"현재 상태: {self.operator.state.upper()}")
        elif key in ["score", "2"]:
            self._get_score()
        elif key in ["result", "3"]:
            self._get_trading_record()

    def _get_score(self):
        def print_score_and_main_statement(score):
            print("current score ==========")
            print(score)

        self.operator.get_score(print_score_and_main_statement)

    def _get_trading_record(self):
        """현재까지 거래 기록 출력"""

        if self.operator is None:
            print("초기화가 필요합니다")
            return

        results = self.operator.get_trading_results()
        if results is None or len(results) == 0:
            print("거래 기록이 없습니다")
            return

        for result in results:
            print(f"@{result['date_time']}, {result['type']}")
            print(f"{result['price']} x {result['amount']}")

    def start(self):
        """프로그램 시작, 재시작"""
        if self.operator.start() is not True:
            print("프로그램 시작을 실패했습니다")
            return

    def stop(self):
        """프로그램 중지"""
        if self.operator is not None:
            self.operator.stop()

    def terminate(self, signum=None, frame=None):
        """프로그램 종료"""
        del frame
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        self.stop()
        self.terminating = True
        print("Good Bye~")
