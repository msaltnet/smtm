import os
import signal
import time
import threading
import json
from urllib import parse
import requests
from dotenv import load_dotenv
from ..config import Config
from ..log_manager import LogManager
from ..analyzer import Analyzer
from ..trader.upbit_trader import UpbitTrader
from ..trader.bithumb_trader import BithumbTrader
from ..data.data_provider_factory import DataProviderFactory
from ..strategy.strategy_factory import StrategyFactory
from ..operator import Operator
from ..worker import Worker
from ..trader.demo_trader import DemoTrader

load_dotenv()


class TelegramController:
    """
    자동 거래 시스템 탤래그램 챗봇 컨트롤러
    Telegram chatbot controller for trading system
    """

    API_HOST = "https://api.telegram.org/"
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "telegram_token")
    CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "123456"))
    POLLING_TIMEOUT = 10
    GUIDE_READY = "자동 거래 시작 전입니다.\n명령어를 입력해주세요.\n\n"
    GUIDE_RUNNING = "자동 거래 운영 중입니다.\n명령어를 입력해주세요.\n\n"
    AVAILABLE_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    UPBIT_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    BITHUMB_CURRENCY = ["BTC", "ETH"]

    def __init__(self, token=None, chatid=None):
        LogManager.set_stream_level(Config.operation_log_level)
        self.logger = LogManager.get_logger("TelegramController")
        self.post_worker = Worker("Chatbot-Post-Worker")
        self.post_worker.start()
        # chatbot variable
        self.terminating = False
        self.last_update_id = 0
        self.in_progress = None
        self.in_progress_step = 0
        self.main_keyboard = None
        self.setup_list = []
        self.score_query_list = []
        # smtm variable
        self.operator = None
        self.budget = None
        self.strategy = None
        self.data_provider = None
        self.trader = None
        self.command_list = []
        self.strategies = []
        self.data_providers = []
        self._update_strategy()
        self._update_data_provider()
        self._create_command()
        self.currency = None
        self.is_demo = False
        an_hour_tick = int(60 / Config.candle_interval) * 60
        self.score_query_tick = {
            "1. 최근 6시간": (an_hour_tick * 6, -1),
            "2. 최근 12시간": (an_hour_tick * 12, -1),
            "3. 최근 24시간": (an_hour_tick * 24, -1),
            "4. 24시간 전부터 12시간": (an_hour_tick * 12, -2),
            "5. 48시간 전부터 24시간": (an_hour_tick * 24, -2),
            "1": (an_hour_tick * 6, -1),
            "2": (an_hour_tick * 12, -1),
            "3": (an_hour_tick * 24, -1),
            "4": (an_hour_tick * 12, -2),
            "5": (an_hour_tick * 24, -2),
        }
        if token is not None:
            self.TOKEN = token
        if chatid is not None:
            self.CHAT_ID = int(chatid)

    def _update_strategy(self):
        self.strategies = []
        for idx, strategy in enumerate(StrategyFactory.get_all_strategy_info()):
            self.strategies.append(
                {
                    "name": f"{idx}. {strategy['name']}",
                    "selector": [
                        f"{idx}. {strategy['name']}".upper(),
                        f"{idx}",
                        f"{strategy['name']}".upper(),
                        f"{strategy['code']}",
                    ],
                    "builder": strategy["class"],
                }
            )

    def _update_data_provider(self):
        self.data_providers = []
        for idx, dp in enumerate(DataProviderFactory.get_all_strategy_info()):
            self.data_providers.append(
                {
                    "name": f"{idx}. {dp['name']}",
                    "selector": [
                        f"{idx}. {dp['name']}".upper(),
                        f"{idx}",
                        f"{dp['name']}".upper(),
                        f"{dp['code']}",
                    ],
                    "builder": dp["class"],
                }
            )

    def _create_command(self):
        self.command_list = [
            {
                "guide": "1. 시작 - 자동 거래 시작",
                "cmd": ["시작", "1", "1. 시작"],
                "action": self._start_trading,
            },
            {
                "guide": "2. 중지 - 자동 거래 중지",
                "cmd": ["중지", "2", "2. 중지"],
                "action": self._stop_trading,
            },
            {
                "guide": "3. 상태 조회 - 운영 상태 조회",
                "cmd": ["상태", "3", "3. 상태 조회", "상태 조회"],
                "action": self._query_state,
            },
            {
                "guide": "4. 수익률 조회 - 기간별 수익률 조회",
                "cmd": ["수익", "4", "수익률 조회", "4. 수익률 조회"],
                "action": self._query_score,
            },
            {
                "guide": "5. 거래내역 조회 - 모든 거래내역 조회",
                "cmd": ["거래", "5", "거래내역 조회", "5. 거래내역 조회"],
                "action": self._query_trading_records,
            },
        ]
        main_keyboard = {
            "keyboard": [
                [{"text": "1. 시작"}, {"text": "2. 중지"}],
                [
                    {"text": "3. 상태 조회"},
                    {"text": "4. 수익률 조회"},
                    {"text": "5. 거래내역 조회"},
                ],
            ]
        }
        main_keyboard = json.dumps(main_keyboard)
        self.main_keyboard = parse.quote(main_keyboard)
        strategy_list = []
        for s_item in self.strategies:
            strategy_list.append(s_item["name"])
        data_provider_list = []
        for dp_item in self.data_providers:
            data_provider_list.append(dp_item["name"])
        self.setup_list = [
            {
                "guide": "운영 예산을 정해주세요",
                "keyboard": ["50000", "100000", "500000", "1000000"],
            },
            {"guide": "거래할 화폐를 정해주세요", "keyboard": self.AVAILABLE_CURRENCY},
            {"guide": "사용할 데이터를 선택해 주세요", "keyboard": data_provider_list},
            {"guide": "거래소를 선택해 주세요", "keyboard": ["1. Upbit", "2. Bithumb"]},
            {
                "guide": "전략을 선택해 주세요",
                "keyboard": strategy_list,
            },
            {"guide": "자동 거래를 시작할까요?", "keyboard": ["1. Yes", "2. No"]},
        ]
        self._convert_keyboard_markup(self.setup_list)
        self.score_query_list = [
            {
                "guide": "조회할 기간을 정해주세요",
                "keyboard": [
                    "1. 최근 6시간",
                    "2. 최근 12시간",
                    "3. 최근 24시간",
                    "4. 24시간 전부터 12시간",
                    "5. 48시간 전부터 24시간",
                ],
            },
        ]
        self._convert_keyboard_markup(self.score_query_list)

    @staticmethod
    def _convert_keyboard_markup(setup_list):
        for item in setup_list:
            markup = {"keyboard": []}
            for key in item["keyboard"]:
                markup["keyboard"].append([{"text": key}])
            markup = json.dumps(markup)
            item["keyboard"] = parse.quote(markup)

    def main(self, demo=False):
        print("##### smtm telegram controller is started #####")
        self.is_demo = demo
        if self.is_demo:
            print("$$$ THIS IS DEMO MODE $$$")

        signal.signal(signal.SIGINT, self._terminate)
        signal.signal(signal.SIGTERM, self._terminate)
        self._start_get_updates_loop()
        while not self.terminating:
            time.sleep(0.5)

    def _start_get_updates_loop(self):
        """
        반복적 텔레그램 메세지를 확인하는 쓰레드 시작
        Start a thread to check for repetitive Telegram messages
        """

        def looper():
            self.logger.debug(f"start get updates thread: {threading.get_ident()}")
            while not self.terminating:
                self._handle_message()

        get_updates_thread = threading.Thread(
            target=looper, name="get updates", daemon=True
        )
        get_updates_thread.start()

    def _handle_message(self):
        """
        텔레그램 메세지를 확인해서 명령어를 처리
        Check Telegram messages to process commands
        """
        updates = self._get_updates()
        if updates is None:
            self.logger.error("get updates failed")
            return

        try:
            if updates["ok"]:
                for result in updates["result"]:
                    self.logger.debug(
                        f'result: {result["message"]["chat"]["id"]} : {self.CHAT_ID}'
                    )
                    if result["message"]["chat"]["id"] != self.CHAT_ID:
                        continue
                    if "text" in result["message"]:
                        self._execute_command(result["message"]["text"])
                    self.last_update_id = result["update_id"]
        except (ValueError, KeyError) as err:
            self.logger.error(f"Invalid data from server: {err}")

    def _execute_command(self, command):
        self.logger.debug(f"_execute_command: {command}")
        found = False
        try:
            if self.in_progress is not None:
                self.in_progress(command)
                return
        except TypeError as err:
            self.logger.debug(f"invalid in_progress: {err}")

        for item in self.command_list:
            if command in item["cmd"]:
                found = True
                item["action"](command)

        if not found:
            if self.operator is None:
                message = self.GUIDE_READY
            else:
                message = self.GUIDE_RUNNING
            for item in self.command_list:
                message += item["guide"] + "\n"
            self._send_text_message(message, self.main_keyboard)

    def _send_text_message(self, text, keyboard=None):
        encoded_text = parse.quote(text)
        if keyboard is not None:
            url = f"{self.API_HOST}{self.TOKEN}/sendMessage?chat_id={self.CHAT_ID}&text={encoded_text}&reply_markup={keyboard}"
        else:
            url = f"{self.API_HOST}{self.TOKEN}/sendMessage?chat_id={self.CHAT_ID}&text={encoded_text}"

        def send_message(task):
            if self._send_http(task["url"]):
                self.logger.error(f"send message failed: {text}")

        self.post_worker.post_task({"runnable": send_message, "url": url})

    def _send_image_message(self, file):
        url = f"{self.API_HOST}{self.TOKEN}/sendPhoto?chat_id={self.CHAT_ID}"

        def send_image(task):
            if self._send_http(task["url"], True, task["file"]):
                self.logger.error(f"send image failed: {task['file']}")

        self.post_worker.post_task({"runnable": send_image, "url": url, "file": file})

    def _get_updates(self):
        """
        getUpdates API로 새로운 메세지를 가져오기
        Get new messages with the getUpdates API
        """
        offset = self.last_update_id + 1
        return self._send_http(
            f"{self.API_HOST}{self.TOKEN}/getUpdates?offset={offset}&timeout={self.POLLING_TIMEOUT}"
        )

    def _send_http(self, url, is_post=False, file=None):
        try:
            if is_post:
                if file is not None:
                    with open(file, "rb") as image_file:
                        response = requests.post(url, files={"photo": image_file})
                else:
                    response = requests.post(url)
            else:
                response = requests.get(url)
            response.raise_for_status()
            result = response.json()
        except ValueError as err:
            self.logger.error(f"Invalid data from server: {err}")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result

    def _on_start_select_exchange(self, command):
        exchange = self._get_exchange_from_command(command)
        if exchange is None:
            self._send_text_message("지원하지 않는 거래소입니다.")
            return True

        if self.currency in getattr(self, f"{exchange.upper()}_CURRENCY"):
            self._set_trader(exchange)
            return False

        self._send_text_message("현재 지원하지 않는 코인입니다.")
        return True

    def _get_exchange_from_command(self, command):
        exchanges = {
            "1. UPBIT": "UPBIT",
            "1": "UPBIT",
            "UPBIT": "UPBIT",
            "2. BITHUMB": "BITHUMB",
            "2": "BITHUMB",
            "BITHUMB": "BITHUMB",
        }
        return exchanges.get(command.upper())

    def _set_trader(self, exchange):
        class_name = f"{exchange.title()}Trader"  # e.g., UpbitTrader, BithumbTrader
        trader_class = DemoTrader if self.is_demo else globals().get(class_name)
        if trader_class:
            self.trader = trader_class(budget=self.budget, currency=self.currency)

    def _get_summary_message(self):
        return "".join(
            [
                f"화폐: {self.currency}\n",
                f"전략: {self.strategy.NAME}\n",
                f"거래소: {self.trader.NAME}\n",
                f"예산: {self.budget}\n",
            ]
        )

    def _start_operator(self):
        def _alert_callback(msg):
            self.alert_callback(msg)

        self.operator = Operator(alert_callback=_alert_callback)
        self.operator.initialize(
            self.data_provider,
            self.strategy,
            self.trader,
            Analyzer(),
            budget=self.budget,
        )
        self.operator.set_interval(Config.candle_interval)
        return self.operator.start()

    def _start_trading(self, command):
        not_ok = True
        message = ""
        if self.in_progress_step == 0:
            not_ok = False
        elif self.in_progress_step == 1:
            try:
                self.budget = int(command)
                not_ok = False
            except ValueError:
                self.logger.info(f"invalid budget {command}")
        elif self.in_progress_step == 2:
            if command.upper() in self.AVAILABLE_CURRENCY:
                self.currency = command.upper()
                not_ok = False
        elif self.in_progress_step == 3:
            for dp_item in self.data_providers:
                if command.upper() in dp_item["selector"]:
                    self.data_provider = dp_item["builder"]()
                    not_ok = False
                    break
        elif self.in_progress_step == 4:
            not_ok = self._on_start_select_exchange(command)
        elif self.in_progress_step == 5:
            for s_item in self.strategies:
                if command.upper() in s_item["selector"]:
                    self.strategy = s_item["builder"]()
                    not_ok = False
                    break

            if not not_ok:
                message = self._get_summary_message()
        elif (
            self.in_progress_step == len(self.setup_list)
            and command.upper()
            in [
                "1. YES",
                "1",
                "Y",
                "YES",
            ]
            and self._start_operator()
        ):
            start_message = [
                "자동 거래가 시작되었습니다!\n",
                f"화폐: {self.currency}\n",
                f"전략: {self.strategy.NAME}\n",
                f"거래소: {self.trader.NAME}\n",
                f"예산: {self.budget}\n",
                f"거래 간격: {Config.candle_interval}",
            ]
            self._send_text_message("".join(start_message), self.main_keyboard)
            self.logger.info(
                f"## START! strategy: {self.strategy.NAME} , trader: {self.trader.NAME}"
            )
            self.in_progress = None
            self.in_progress_step = 0
            return

        if not_ok or self.in_progress_step >= len(self.setup_list):
            self._terminate_start_in_progress()
            return

        message += self.setup_list[self.in_progress_step]["guide"]
        keyboard = self.setup_list[self.in_progress_step]["keyboard"]
        self._send_text_message(message, keyboard)
        self.in_progress = self._start_trading
        self.in_progress_step += 1

    def _terminate_start_in_progress(self):
        self.in_progress = None
        self.in_progress_step = 0
        self.operator = None
        self.budget = None
        self.strategy = None
        self.data_provider = None
        self.trader = None
        self._send_text_message(
            "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요",
            self.main_keyboard,
        )

    def _stop_trading(self, command):
        del command
        last_report = None
        if self.operator is not None:
            last_report = self.operator.stop()
        self.in_progress = None
        self.in_progress_step = 0
        self.operator = None
        self.budget = None
        self.strategy = None
        self.data_provider = None
        self.trader = None

        if last_report is None:
            self._send_text_message("자동 거래가 중지되었습니다", self.main_keyboard)
        else:
            score_message = [
                "자동 거래가 중지되었습니다\n",
                f"{last_report['summary'][8][1]} - {last_report['summary'][8][2]}\n",
                f"자산 {last_report['summary'][0]} -> {last_report['summary'][1]}\n",
                f"수익률 {last_report['summary'][2]}\n",
                f"비교 수익률 {last_report['summary'][3]}\n",
            ]
            self._send_text_message("".join(score_message), self.main_keyboard)

    def _query_state(self, command):
        del command
        if self.operator is None:
            message = "자동 거래 시작 전입니다"
        else:
            message = "자동 거래 운영 중입니다"
        self._send_text_message(message)

    def _query_score(self, command):
        """
        구간 수익률과 그래프를 메세지로 전송
        "1. 최근 6시간"
        "2. 최근 12시간"
        "3. 최근 24시간"
        "4. 24시간 전부터 12시간"
        "5. 48시간 전부터 24시간"
        Message Band Returns and Graphs
        “1. Last 6 hours”
        “2. Last 12 hours”
        “3. Last 24 hours”
        “4. 24 hours to 12 hours ago”
        “5. 48 hours to 24 hours ago”
        """
        not_ok = True
        if self.operator is None:
            self._send_text_message("자동 거래 운영중이 아닙니다", self.main_keyboard)
            return

        message = ""
        if self.in_progress_step == 1:
            if command in self.score_query_tick.keys():

                def print_score_and_main_statement(score):
                    if score is None:
                        self._send_text_message(
                            "수익률 조회중 문제가 발생하였습니다.", self.main_keyboard
                        )
                        return

                    diff = score[1] - score[0]
                    ratio = round(diff / score[0] * 100, 3)
                    score_message = [
                        f"{score[8][1]} - {score[8][2]}\n",
                        f"자산 {score[0]} -> {score[1]}\n",
                        f"구간 수익률 {ratio}\n",
                        f"{score[8][0]}~\n",
                        f"누적 수익률 {score[2]}\n",
                        f"비교 수익률 {score[3]}\n",
                    ]

                    self._send_text_message("".join(score_message), self.main_keyboard)
                    if len(score) > 4 and score[4] is not None:
                        self._send_image_message(score[4])

                self.operator.get_score(
                    print_score_and_main_statement, self.score_query_tick[command]
                )
                not_ok = False

        if self.in_progress_step >= len(self.score_query_list):
            self.in_progress = None
            self.in_progress_step = 0
            if not_ok:
                self._send_text_message("다시 시작해 주세요", self.main_keyboard)
            else:
                self._send_text_message("조회중입니다", self.main_keyboard)
            return

        message += self.score_query_list[self.in_progress_step]["guide"]
        keyboard = self.score_query_list[self.in_progress_step]["keyboard"]
        self._send_text_message(message, keyboard)
        self.in_progress = self._query_score
        self.in_progress_step += 1

    def _query_trading_records(self, command):
        """
        현재까지 거래 기록을 메세지로 전송
        Message transaction history to date
        """
        del command
        if self.operator is None:
            self._send_text_message("자동 거래 운영중이 아닙니다", self.main_keyboard)
            return

        results = self.operator.get_trading_results()
        if results is None or len(results) == 0:
            self._send_text_message("거래 기록이 없습니다", self.main_keyboard)
            return

        message = []
        for result in results:
            message.append(f"@{result['date_time']}, {result['type']}\n")
            message.append(f"{result['price']} x {result['amount']}\n")
        message.append(f"총 {len(results)}건의 거래")
        self._send_text_message("".join(message), self.main_keyboard)

    def _terminate(self, signum=None, frame=None):
        del frame
        self.terminating = True
        self.post_worker.stop()
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        print("Good Bye~")

    def alert_callback(self, msg):
        """
        예외 상황 처리
        send a alert message to handle a exception case
        """
        self._send_text_message(f"Alert: {msg}", self.main_keyboard)
