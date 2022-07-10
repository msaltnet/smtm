"""SimulationOperator를 사용해서 시뮬레이션을 컨트롤하는 Simulator 클래스"""
import signal
import time
from . import (
    LogManager,
    Analyzer,
    SimulationTrader,
    SimulationDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    StrategyRsi,
    SimulationOperator,
    DateConverter,
)


class Simulator:
    """자동 거래 시뮬레이터 클래스

    command_list:
        {
            guide: 화면에 출력될 명령어와 안내문
            cmd: 입력 받은 명령어와 매칭되는 문자열
            action: 명령어가 입력되었을때 실행되는 객체
        }

    config_list:
        {
            guide: 화면에 출력될 설정값과 안내문
            value: 출력될 현재값
            action: 입력 받은 설정값을 처리해주는 객체
        }
    """

    MAIN_STATEMENT = "input command (h:help): "

    def __init__(
        self,
        budget=50000,
        interval=2,
        strategy=0,
        from_dash_to="201220.170000-201220.180000",
        currency="BTC",
    ):
        self.logger = LogManager.get_logger("Simulator")
        self.__terminating = False
        self.start_str = "200430.170000"
        self.end_str = "200430.180000"
        self.interval = interval
        self.operator = None
        self.strategy = int(strategy)
        self.budget = int(budget)
        self.need_init = True
        self.currency = currency

        self.interval = float(self.interval)

        start_end = from_dash_to.split("-")
        self.start_str = start_end[0]
        self.end_str = start_end[1]

        self.command_list = [
            {
                "guide": "h, help          print command info",
                "cmd": ["help", "h"],
                "action": self.print_help,
            },
            {
                "guide": "r, run           start running simulation",
                "cmd": ["run", "r"],
                "action": self.start,
            },
            {
                "guide": "s, stop          stop running simulation",
                "cmd": ["stop", "s"],
                "action": self._stop,
            },
            {
                "guide": "t, terminate     terminate simulator",
                "cmd": ["terminate", "t"],
                "action": self.terminate,
            },
            {
                "guide": "i, initialize    initialize simulation",
                "cmd": ["initialize", "i"],
                "action": self.initialize_with_command,
            },
            {
                "guide": "1, state         query operating state",
                "cmd": ["1"],
                "action": self._print_state,
            },
            {
                "guide": "2, score         query current score",
                "cmd": ["2"],
                "action": self._print_score,
            },
            {
                "guide": "3, result        query trading result",
                "cmd": ["3"],
                "action": self._print_trading_result,
            },
        ]

        self.config_list = [
            {
                "guide": "년월일.시분초 형식으로 시작 시점 입력. 예. 201220.162300",
                "value": self.start_str,
                "action": self._set_start_str,
            },
            {
                "guide": "년월일.시분초 형식으로 종료 시점 입력. 예. 201220.162300",
                "value": self.end_str,
                "action": self._set_end_str,
            },
            {
                "guide": "거래 간격 입력. 예. 1",
                "value": self.interval,
                "action": self._set_interval,
            },
            {
                "guide": "예산 입력. 예. 50000",
                "value": self.budget,
                "action": self._set_budget,
            },
            {
                "guide": "전략 번호 입력. 0: Buy and Hold, 1: SMA-0, 2: RSI",
                "value": self.strategy,
                "action": self._set_strategy,
            },
            {
                "guide": "화폐 코드 입력. BTC, ETH",
                "value": self.currency,
                "action": self._set_currency,
            },
        ]

    def initialize(self):
        """시뮬레이션 초기화"""

        dt = DateConverter.to_end_min(self.start_str + "-" + self.end_str)
        end = dt[0][1]
        count = dt[0][2]

        if self.strategy == 0:
            strategy = StrategyBuyAndHold()
        elif self.strategy == 1:
            strategy = StrategySma0()
        elif self.strategy == 2:
            strategy = StrategyRsi()
        else:
            raise UserWarning(f"Invalid Strategy! {self.strategy}")

        strategy.is_simulation = True
        self.operator = SimulationOperator()
        self._print_configuration(strategy.NAME)

        data_provider = SimulationDataProvider(currency=self.currency)
        data_provider.initialize_simulation(end=end, count=count)
        trader = SimulationTrader(currency=self.currency)
        trader.initialize_simulation(end=end, count=count, budget=self.budget)
        analyzer = Analyzer()
        analyzer.is_simulation = True
        self.operator.initialize(
            data_provider,
            strategy,
            trader,
            analyzer,
            budget=self.budget,
        )
        self.operator.tag = self._make_tag(self.start_str, self.end_str, strategy.NAME)
        self.operator.set_interval(self.interval)
        self.need_init = False

    @staticmethod
    def _make_tag(start_str, end_str, strategy_name):
        return "SIM-" + strategy_name + "-" + start_str + "-" + end_str

    def start(self):
        """시뮬레이션 시작, 재시작"""
        if self.operator is None or self.need_init:
            self._print("초기화가 필요합니다")
            return

        self.logger.info("Simulation start! ============================")

        if self.operator.start() is not True:
            self._print("Fail operator start")
            return

    def stop(self, signum, frame):
        """시뮬레이션 중지"""
        self._stop()
        self.__terminating = True
        self._print(f"Receive Signal {signum} {frame}")
        self._print("Stop Singing")

    def _stop(self):
        if self.operator is not None:
            self.operator.stop()
            self.need_init = True
            self._print("프로그램을 재시작하려면 초기화하세요")

    def terminate(self):
        """시뮬레이터 종료"""
        self._print("Terminating......")
        self._stop()
        self.__terminating = True
        self._print("Good Bye~")

    def run_single(self):
        """인터렉션 없이 초기 설정 값으로 단독 1회 실행"""
        self.initialize()
        self.start()
        while self.operator.state == "running":
            time.sleep(0.5)

        self.terminate()

    def main(self):
        """main 함수"""
        signal.signal(signal.SIGINT, self.stop)
        signal.signal(signal.SIGTERM, self.stop)

        while not self.__terminating:
            try:
                key = input(self.MAIN_STATEMENT)
                self.on_command(key)
            except EOFError:
                break

    def on_command(self, key):
        """커맨드 처리"""
        for cmd in self.command_list:
            if key.lower() in cmd["cmd"]:
                cmd["action"]()
                return
        self._print("invalid command")

    def print_help(self):
        """가이드 문구 출력"""
        self._print("command list =================")
        for item in self.command_list:
            self._print(item["guide"], True)

    def initialize_with_command(self):
        """설정 값을 입력받아서 초기화 진행"""
        for config in self.config_list:
            self._print(config["guide"])
            value = input(f"현재값: {config['value']} >> ")
            value = config["value"] if value == "" else value
            self._print(f"설정값: {value}")
            config["action"](value)

        self.initialize()

    def _set_start_str(self, value):
        self.start_str = value

    def _set_end_str(self, value):
        self.end_str = value

    def _set_interval(self, value):
        next_value = float(value)
        if next_value > 0:
            self.interval = next_value

    def _set_budget(self, value):
        next_value = int(value)
        if next_value > 0:
            self.budget = next_value

    def _set_strategy(self, value):
        self.strategy = int(value)

    def _set_currency(self, value):
        self.currency = value

    def _print_state(self):
        if self.operator is None:
            self._print("초기화가 필요합니다")
            return
        self._print(self.operator.state)

    def _print_configuration(self, strategy_name):
        self._print("Simulation Configuration =====")
        self._print(f"Simulation Period {self.start_str} ~ {self.end_str}")
        self._print(f"Budget: {self.budget}, Interval: {self.interval}")
        self._print(f"Strategy: {strategy_name}")

    def _print_score(self):
        def print_score_and_main_statement(score):
            self._print("current score ==========")
            self._print(score)
            self._print(self.MAIN_STATEMENT)

        self.operator.get_score(print_score_and_main_statement)

    def _print_trading_result(self):
        results = self.operator.get_trading_results()

        if results is None or len(results) == 0:
            self._print("거래 기록이 없습니다")
            return

        for result in results:
            self._print(f"@{result['date_time']}, {result['type']}")
            self._print(f"{result['price']} x {result['amount']}")

    def _print(self, contents, logger_skip=False):
        if logger_skip is not True:
            self.logger.info(contents)
        print(contents)
