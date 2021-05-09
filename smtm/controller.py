"""시스템 운영 인터페이스

Operator를 사용해서 시스템을 컨트롤하는 모듈
"""
import signal
from . import (
    LogManager,
    Analyzer,
    UpbitTrader,
    UpbitDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    Operator,
)


class Controller:
    """smtm 컨트롤러"""

    MAIN_STATEMENT = "명령어를 입력하세요. (h: 도움말): "

    def __init__(self, interval=10, strategy=0, budget=50000):
        self.logger = LogManager.get_logger("Controller")
        self.terminating = False
        self.interval = interval
        self.operator = Operator()
        self.budget = budget
        self.is_initialized = False
        self.command_list = []
        self.create_command()
        self.strategy = StrategySma0()
        LogManager.set_stream_level(30)

        if int(strategy) == 0:
            self.strategy = StrategyBuyAndHold()

    def create_command(self):
        self.command_list = [
            {
                "guide": "{0:15}도움말 출력".format("h, help"),
                "cmd": "help",
                "short": "h",
                "need_value": False,
                "action": self.print_help,
            },
            {
                "guide": "{0:15}자동 거래 시작".format("r, run"),
                "cmd": "run",
                "short": "r",
                "need_value": False,
                "action": self.start,
            },
            {
                "guide": "{0:15}자동 거래 중지".format("s, stop"),
                "cmd": "stop",
                "short": "s",
                "need_value": False,
                "action": self.stop,
            },
            {
                "guide": "{0:15}프로그램 종료".format("t, terminate"),
                "cmd": "terminate",
                "short": "t",
                "need_value": False,
                "action": self.terminate,
            },
            {
                "guide": "{0:15}정보 조회".format("q, query"),
                "cmd": "query",
                "short": "q",
                "need_value": True,
                "value_guide": "무엇을 조회할까요? (ex. state, score, result) :",
                "action": self._on_query_command,
            },
        ]

    def main(self):
        """main 함수"""

        self.operator.initialize(
            UpbitDataProvider(),
            self.strategy,
            UpbitTrader(),
            Analyzer(),
            budget=self.budget,
        )

        self.operator.set_interval(self.interval)
        strategy_name = "Buy and Hold" if isinstance(self.strategy, StrategyBuyAndHold) else "SMA0"
        print("##### smtm is intialized #####")
        print(f"interval: {self.interval}, strategy: {strategy_name}")
        print("==============================")

        self.logger.info(f"interval: {self.interval}")
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
        value = None
        for cmd in self.command_list:
            if cmd["cmd"] == key or cmd["short"] == key:
                if cmd["need_value"]:
                    value = input(cmd["value_guide"])
                    print(f"{cmd['cmd']} - {value} 명령어를 실행합니다.")
                    cmd["action"](value)
                else:
                    print(f"{cmd['cmd']} 명령어를 실행합니다.")
                    cmd["action"]()
                return
        print("잘못된 명령어가 입력되었습니다")

    def _on_query_command(self, value):
        """가이드 문구 출력"""
        if value == "state":
            print(f"현재 상태: {self.operator.state}")
        elif value == "score":
            self._get_score()
        elif value == "result":
            print(self.operator.get_trading_results())

    def _get_score(self):
        def print_score_and_main_statement(score):
            print("current score ==========")
            print(score)

        self.operator.get_score(print_score_and_main_statement)

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
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        self.stop()
        self.terminating = True
        print("Good Bye~")
