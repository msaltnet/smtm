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
    MESSAGE = {
        "ko": {
            "GUIDE_READY": "자동 거래 시작 전입니다.\n명령어를 입력해주세요.\n\n",
            "GUIDE_RUNNING": "자동 거래 운영 중입니다.\n명령어를 입력해주세요.\n\n",
            "PERIOD_1": "1. 최근 6시간",
            "PERIOD_2": "2. 최근 12시간",
            "PERIOD_3": "3. 최근 24시간",
            "PERIOD_4": "4. 24시간 전부터 12시간",
            "PERIOD_5": "5. 48시간 전부터 24시간",
            "COMMAND_G_1": "1. 시작 - 자동 거래 시작",
            "COMMAND_G_2": "2. 중지 - 자동 거래 중지",
            "COMMAND_G_3": "3. 상태 조회 - 운영 상태 조회",
            "COMMAND_G_4": "4. 수익률 조회 - 기간별 수익률 조회",
            "COMMAND_G_5": "5. 거래내역 조회 - 모든 거래내역 조회",
            "COMMAND_C_1": "시작",
            "COMMAND_C_2": "중지",
            "COMMAND_C_3": "상태 조회",
            "COMMAND_C_4": "수익률 조회",
            "COMMAND_C_5": "거래내역 조회",
            "SETUP_1": "운영 예산을 정해주세요",
            "SETUP_2": "거래할 화폐를 정해주세요",
            "SETUP_3": "사용할 데이터를 선택해 주세요",
            "SETUP_4": "거래소를 선택해 주세요",
            "SETUP_5": "전략을 선택해 주세요",
            "SETUP_6": "자동 거래를 시작할까요?",
            "SETUP_7": "조회할 기간을 정해주세요",
            "ERROR_EXCHANGE": "지원하지 않는 거래소입니다.",
            "ERROR_CURRENCY": "현재 지원하지 않는 코인입니다.",
            "ERROR_RESTART": "자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요",
            "ERROR_QUERY": "수익률 조회중 문제가 발생하였습니다.",
            "INFO_CURRENCY": "화폐",
            "INFO_STRATEGY": "전략",
            "INFO_TRADER": "거래소",
            "INFO_BUDGET": "예산",
            "INFO_INTERVAL": "거래 간격",
            "INFO_START": "자동 거래가 시작되었습니다",
            "NOTIFY_STOP": "자동 거래가 중지되었습니다",
            "NOTIFY_ASSET": "자산",
            "NOTIFY_RATE": "수익률",
            "NOTIFY_COMPARE_RATE": "비교 수익률",
            "NOTIFY_PERIOD_RATE": "구간 수익률",
            "NOTIFY_TOTAL_RATE": "누적 수익률",
            "INFO_STATUS_READY": "자동 거래 시작 전입니다",
            "INFO_STATUS_RUNNING": "자동 거래 운영 중입니다",
            "INFO_RESTART_QUERY": "다시 시작해 주세요",
            "INFO_QUERY_RUNNING": "조회중입니다",
            "INFO_QUERY_EMPTY": "거래 기록이 없습니다",
        },
        "en": {
            "GUIDE_READY": "Before starting automatic trading.\nPlease enter a command.\n\n",
            "GUIDE_RUNNING": "Automatic trading is in operation.\nPlease enter a command.\n\n",
            "PERIOD_1": "1. Last 6 hours",
            "PERIOD_2": "2. Last 12 hours",
            "PERIOD_3": "3. Last 24 hours",
            "PERIOD_4": "4. 24 hours to 12 hours ago",
            "PERIOD_5": "5. 48 hours to 24 hours ago",
            "COMMAND_G_1": "1. Start - Start automatic trading",
            "COMMAND_G_2": "2. Stop - Stop automatic trading",
            "COMMAND_G_3": "3. Status - Operation status check",
            "COMMAND_G_4": "4. Return rate - Return rate by period",
            "COMMAND_G_5": "5. Transaction history - View all transaction history",
            "COMMAND_C_1": "Start",
            "COMMAND_C_2": "Stop",
            "COMMAND_C_3": "Status",
            "COMMAND_C_4": "Return rate",
            "COMMAND_C_5": "Transaction history",
            "SETUP_1": "Please set the operating budget",
            "SETUP_2": "Please select the currency to trade",
            "SETUP_3": "Please select the data to use",
            "SETUP_4": "Please select the exchange",
            "SETUP_5": "Please select a strategy",
            "SETUP_6": "Do you want to start automatic trading?",
            "SETUP_7": "Please select the period to query",
            "ERROR_EXCHANGE": "Unsupported exchange",
            "ERROR_CURRENCY": "Currently unsupported coin",
            "ERROR_RESTART": "Automatic trading has not started.\nPlease start over",
            "ERROR_QUERY": "There was a problem with the return rate query.",
            "INFO_CURRENCY": "Currency",
            "INFO_STRATEGY": "Strategy",
            "INFO_TRADER": "Exchange",
            "INFO_BUDGET": "Budget",
            "INFO_INTERVAL": "Trading interval",
            "INFO_START": "Automatic trading has started",
            "NOTIFY_STOP": "Automatic trading has stopped",
            "NOTIFY_ASSET": "Asset",
            "NOTIFY_RATE": "Return rate",
            "NOTIFY_COMPARE_RATE": "Comparison rate",
            "NOTIFY_PERIOD_RATE": "Period rate",
            "NOTIFY_TOTAL_RATE": "Total rate",
            "INFO_STATUS_READY": "Before starting automatic trading",
            "INFO_STATUS_RUNNING": "Automatic trading is in operation",
            "INFO_RESTART_QUERY": "Please start over",
            "INFO_QUERY_RUNNING": "Querying",
            "INFO_QUERY_EMPTY": "No transaction history",
        },
    }
    AVAILABLE_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    UPBIT_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    BITHUMB_CURRENCY = ["BTC", "ETH"]

    def __init__(self, token=None, chatid=None):
        self.msg = self.MESSAGE.get(Config.language, self.MESSAGE["ko"])
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
            self.msg["PERIOD_1"]: (an_hour_tick * 6, -1),
            self.msg["PERIOD_2"]: (an_hour_tick * 12, -1),
            self.msg["PERIOD_3"]: (an_hour_tick * 24, -1),
            self.msg["PERIOD_4"]: (an_hour_tick * 12, -2),
            self.msg["PERIOD_5"]: (an_hour_tick * 24, -2),
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
                "guide": self.msg["COMMAND_G_1"],
                "cmd": [self.msg["COMMAND_C_1"], "1"],
                "action": self._start_trading,
            },
            {
                "guide": self.msg["COMMAND_G_2"],
                "cmd": [self.msg["COMMAND_C_2"], "2"],
                "action": self._stop_trading,
            },
            {
                "guide": self.msg["COMMAND_G_3"],
                "cmd": [self.msg["COMMAND_C_3"], "3"],
                "action": self._query_state,
            },
            {
                "guide": self.msg["COMMAND_G_4"],
                "cmd": [self.msg["COMMAND_C_4"], "4"],
                "action": self._query_score,
            },
            {
                "guide": self.msg["COMMAND_G_5"],
                "cmd": [self.msg["COMMAND_C_5"], "5"],
                "action": self._query_trading_records,
            },
        ]
        main_keyboard = {
            "keyboard": [
                [{"text": self.msg["COMMAND_C_1"]}, {"text": self.msg["COMMAND_C_2"]}],
                [
                    {"text": self.msg["COMMAND_C_3"]},
                    {"text": self.msg["COMMAND_C_4"]},
                    {"text": self.msg["COMMAND_C_5"]},
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
                "guide": self.msg["SETUP_1"],
                "keyboard": ["50000", "100000", "500000", "1000000"],
            },
            {
                "guide": self.msg["SETUP_2"],
                "keyboard": self.AVAILABLE_CURRENCY,
            },
            {"guide": self.msg["SETUP_3"], "keyboard": data_provider_list},
            {"guide": self.msg["SETUP_4"], "keyboard": ["1. Upbit", "2. Bithumb"]},
            {
                "guide": self.msg["SETUP_5"],
                "keyboard": strategy_list,
            },
            {"guide": self.msg["SETUP_6"], "keyboard": ["1. Yes", "2. No"]},
        ]
        self._convert_keyboard_markup(self.setup_list)
        self.score_query_list = [
            {
                "guide": self.msg["SETUP_7"],
                "keyboard": [
                    self.msg["PERIOD_1"],
                    self.msg["PERIOD_2"],
                    self.msg["PERIOD_3"],
                    self.msg["PERIOD_4"],
                    self.msg["PERIOD_5"],
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
            print("$$$ DEMO MODE $$$")

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
                message = self.msg["GUIDE_READY"]
            else:
                message = self.msg["GUIDE_RUNNING"]
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
            if not self._send_http(task["url"]):
                self.logger.error(f"send message failed: {text}")

        self.post_worker.post_task({"runnable": send_message, "url": url})

    def _send_image_message(self, file):
        url = f"{self.API_HOST}{self.TOKEN}/sendPhoto?chat_id={self.CHAT_ID}"

        def send_image(task):
            if not self._send_http(task["url"], True, task["file"]):
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
            self._send_text_message(self.msg["ERROR_EXCHANGE"])
            return True

        if self.currency in getattr(self, f"{exchange.upper()}_CURRENCY"):
            self._set_trader(exchange)
            return False

        self._send_text_message(self.msg["ERROR_CURRENCY"])
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
                f"{self.msg['INFO_CURRENCY']}: {self.currency}\n",
                f"{self.msg['INFO_STRATEGY']}: {self.strategy.NAME}\n",
                f"{self.msg['INFO_TRADER']}: {self.trader.NAME}\n",
                f"{self.msg['INFO_BUDGET']}: {self.budget}\n",
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
                    try:
                        self.data_provider = dp_item["builder"](
                            self.currency, interval=Config.candle_interval
                        )
                        not_ok = False
                    except UserWarning as err:
                        self.logger.error(f"invalid data provider: {err}")
                        self._send_text_message(
                            self.msg["ERROR_RESTART"], self.main_keyboard
                        )
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
                f"{self.msg['INFO_START']}\n",
                f"{self.msg['INFO_CURRENCY']}: {self.currency}\n",
                f"{self.msg['INFO_STRATEGY']}: {self.strategy.NAME}\n",
                f"{self.msg['INFO_TRADER']}: {self.trader.NAME}\n",
                f"{self.msg['INFO_BUDGET']}: {self.budget}\n",
                f"{self.msg['INFO_INTERVAL']}: {Config.candle_interval}",
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
            self.msg["ERROR_RESTART"],
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
            self._send_text_message(self.msg["NOTIFY_STOP"], self.main_keyboard)
        else:
            score_message = [
                f"{self.msg['NOTIFY_STOP']}\n",
                f"{last_report['summary'][8][1]} - {last_report['summary'][8][2]}\n",
                f"{self.msg['NOTIFY_ASSET']}: {last_report['summary'][0]} -> {last_report['summary'][1]}\n",
                f"{self.msg['NOTIFY_RATE']}: {last_report['summary'][2]}\n",
                f"{self.msg['NOTIFY_COMPARE_RATE']}: {last_report['summary'][3]}\n",
            ]
            self._send_text_message("".join(score_message), self.main_keyboard)

    def _query_state(self, command):
        del command
        if self.operator is None:
            message = self.msg["INFO_STATUS_READY"]
        else:
            message = self.msg["INFO_STATUS_RUNNING"]
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
            self._send_text_message(self.msg["INFO_STATUS_READY"], self.main_keyboard)
            return

        message = ""
        if self.in_progress_step == 1:
            if command in self.score_query_tick.keys():

                def print_score_and_main_statement(score):
                    if score is None:
                        self._send_text_message(
                            self.msg["ERROR_QUERY"], self.main_keyboard
                        )
                        return

                    diff = score[1] - score[0]
                    ratio = round(diff / score[0] * 100, 3)
                    score_message = [
                        f"{score[8][1]} - {score[8][2]}\n",
                        f"{self.msg['NOTIFY_ASSET']}: {score[0]} -> {score[1]}\n",
                        f"{self.msg['NOTIFY_PERIOD_RATE']}: {ratio}\n",
                        f"{score[8][0]}~\n",
                        f"{self.msg['NOTIFY_TOTAL_RATE']}: {score[2]}\n",
                        f"{self.msg['NOTIFY_COMPARE_RATE']}: {score[3]}\n",
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
                self._send_text_message(
                    self.msg["INFO_RESTART_QUERY"], self.main_keyboard
                )
            else:
                self._send_text_message(
                    self.msg["INFO_QUERY_RUNNING"], self.main_keyboard
                )
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
            self._send_text_message(self.msg["INFO_STATUS_READY"], self.main_keyboard)
            return

        results = self.operator.get_trading_results()
        if results is None or len(results) == 0:
            self._send_text_message(self.msg["INFO_QUERY_EMPTY"], self.main_keyboard)
            return

        message = []
        for result in results:
            message.append(f"@{result['date_time']}, {result['type']}\n")
            message.append(f"{result['price']} x {result['amount']}\n")
        message.append(f"Total {len(results)} records\n")
        self._send_text_message("".join(message), self.main_keyboard)

    def _terminate(self, signum=None, frame=None):
        del frame
        self.terminating = True
        self.post_worker.stop()
        if signum is not None:
            print("Received a termination signal")
        print("##### smtm telegram controller is terminated #####")
        print("Good Bye~")

    def alert_callback(self, msg):
        """
        예외 상황 처리
        send a alert message to handle a exception case
        """
        self._send_text_message(f"Alert: {msg}", self.main_keyboard)
