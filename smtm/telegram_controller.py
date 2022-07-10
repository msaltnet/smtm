"""텔래그램 챗봇을 활용한 자동 거래 시스템 운영 인터페이스 TelegramController 클래스"""

import os
import signal
import time
import threading
import json
from urllib import parse
import requests
from dotenv import load_dotenv
from . import (
    LogManager,
    Analyzer,
    UpbitTrader,
    UpbitDataProvider,
    BithumbTrader,
    BithumbDataProvider,
    Worker,
    StrategyBuyAndHold,
    StrategySma0,
    StrategyRsi,
    Operator,
)

load_dotenv()


class TelegramController:
    """자동 거래 시스템 탤래그램 챗봇 컨트롤러"""

    API_HOST = "https://api.telegram.org/"
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "telegram_token")
    CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "123456"))
    POLLING_TIMEOUT = 10
    INTERVAL = 60
    GUIDE_READY = "자동 거래 시작 전입니다.\n명령어를 입력해주세요.\n\n"
    GUIDE_RUNNING = "자동 거래 운영 중입니다.\n명령어를 입력해주세요.\n\n"
    AVAILABLE_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    UPBIT_CURRENCY = ["BTC", "ETH", "DOGE", "XRP"]
    BITHUMB_CURRENCY = ["BTC", "ETH"]

    def __init__(self):
        LogManager.set_stream_level(30)
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
        self._create_command()
        self.currency = None

    def _create_command(self):
        """명령어 정보를 생성한다"""
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
                [{"text": "3. 상태 조회"}, {"text": "4. 수익률 조회"}, {"text": "5. 거래내역 조회"}],
            ]
        }
        main_keyboard = json.dumps(main_keyboard)
        self.main_keyboard = parse.quote(main_keyboard)
        self.setup_list = [
            {"guide": "운영 예산을 정해주세요", "keyboard": ["50000", "100000", "500000", "1000000"]},
            {"guide": "거래할 화폐를 정해주세요", "keyboard": self.AVAILABLE_CURRENCY},
            {"guide": "거래소를 선택해 주세요", "keyboard": ["1. Upbit", "2. Bithumb"]},
            {"guide": "전략을 선택해 주세요", "keyboard": ["1. Buy and Hold", "2. Simple Moving Average", "3. RSI"]},
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

    def main(self):
        """main 함수"""
        print("##### smtm telegram controller is started #####")

        signal.signal(signal.SIGINT, self._terminate)
        signal.signal(signal.SIGTERM, self._terminate)

        self._start_get_updates_loop()
        while not self.terminating:
            try:
                time.sleep(0.5)
            except EOFError:
                break

    def _start_get_updates_loop(self):
        """반복적 텔레그램 메세지를 확인하는 쓰레드 관리"""

        def looper():
            self.logger.debug(f"start get updates thread: {threading.get_ident()}")
            while not self.terminating:
                self._handle_message()

        get_updates_thread = threading.Thread(target=looper, name="get updates", daemon=True)
        get_updates_thread.start()

    def _handle_message(self):
        """텔레그램 메세지를 확인해서 명령어를 처리"""
        updates = self._get_updates()
        try:
            if updates is not None and updates["ok"]:
                for result in updates["result"]:
                    self.logger.debug(f'result: {result["message"]["chat"]["id"]} : {self.CHAT_ID}')
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
            self._send_http(task["url"])

        self.post_worker.post_task({"runnable": send_message, "url": url})

    def _send_image_message(self, file):
        url = f"{self.API_HOST}{self.TOKEN}/sendPhoto?chat_id={self.CHAT_ID}"

        def send_image(task):
            self._send_http(task["url"], True, task["file"])

        self.post_worker.post_task({"runnable": send_image, "url": url, "file": file})

    def _get_updates(self):
        """getUpdates API로 새로운 메세지를 가져오기"""
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

    def _on_start_step3(self, command):
        not_ok = True
        if command.upper() in ["1. UPBIT", "1", "UPBIT"]:
            if self.currency in self.UPBIT_CURRENCY:
                self.data_provider = UpbitDataProvider(currency=self.currency)
                self.trader = UpbitTrader(budget=self.budget, currency=self.currency)
                not_ok = False
            else:
                self._send_text_message("현재 지원하지 않는 코인입니다.")
        elif command.upper() in ["2. BITHUMB", "2", "BITHUMB"]:
            if self.currency in self.BITHUMB_CURRENCY:
                self.data_provider = BithumbDataProvider(currency=self.currency)
                self.trader = BithumbTrader(budget=self.budget, currency=self.currency)
                not_ok = False
            else:
                self._send_text_message("현재 지원하지 않는 코인입니다.")
        return not_ok

    def _start_trading(self, command):
        """초기화 후 자동 거래 시작"""
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
            not_ok = self._on_start_step3(command)
        elif self.in_progress_step == 4:
            if command.upper() in ["1. BUY AND HOLD", "1", "BUY AND HOLD", "BNH"]:
                self.strategy = StrategyBuyAndHold()
                not_ok = False
            elif command.upper() in [
                "2. SIMPLE MOVING AVERAGE",
                "2",
                "SIMPLE MOVING AVERAGE",
                "SMA",
            ]:
                self.strategy = StrategySma0()
                not_ok = False
            elif command.upper() in [
                "3. RSI",
                "3",
                "RSI",
            ]:
                self.strategy = StrategyRsi()
                not_ok = False

            if not not_ok:
                message = "".join(
                    [
                        f"화폐: {self.currency}\n",
                        f"전략: {self.strategy.NAME}\n",
                        f"거래소: {self.trader.NAME}\n",
                        f"예산: {self.budget}\n",
                    ]
                )
        elif self.in_progress_step == len(self.setup_list) and command.upper() in [
            "1. YES",
            "1",
            "Y",
            "YES",
        ]:
            def _on_exception(msg):
                self.on_exception(msg)
            self.operator = Operator(on_exception=_on_exception)
            self.operator.initialize(
                self.data_provider,
                self.strategy,
                self.trader,
                Analyzer(),
                budget=self.budget,
            )
            self.operator.set_interval(self.INTERVAL)
            if self.operator.start():
                start_message = [
                    "자동 거래가 시작되었습니다!\n",
                    f"화폐: {self.currency}\n",
                    f"전략: {self.strategy.NAME}\n",
                    f"거래소: {self.trader.NAME}\n",
                    f"예산: {self.budget}\n",
                    f"거래 간격: {self.INTERVAL}",
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
        self._send_text_message("자동 거래가 시작되지 않았습니다.\n처음부터 다시 시작해주세요", self.main_keyboard)

    def _stop_trading(self, command):
        """자동 거래 중지"""
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
                f"자동 거래가 중지되었습니다\n",
                f"{last_report['summary'][8][1]} - {last_report['summary'][8][2]}\n",
                f"자산 {last_report['summary'][0]} -> {last_report['summary'][1]}\n",
                f"수익률 {last_report['summary'][2]}\n",
                f"비교 수익률 {last_report['summary'][3]}\n",
            ]
            self._send_text_message("".join(score_message), self.main_keyboard)

    def _query_state(self, command):
        """현재 상태를 메세지로 전송"""
        del command
        if self.operator is None:
            message = "자동 거래 시작 전입니다"
        else:
            message = "자동 거래 운영 중입니다"
        self._send_text_message(message)

    def _query_score(self, command):
        """구간 수익률과 그래프를 메세지로 전송
        "1. 최근 6시간"
        "2. 최근 12시간"
        "3. 최근 24시간"
        "4. 24시간 전부터 12시간"
        "5. 48시간 전부터 24시간"
        """
        query_list = {
            "1. 최근 6시간": (60 * 6, -1),
            "2. 최근 12시간": (60 * 12, -1),
            "3. 최근 24시간": (60 * 24, -1),
            "4. 24시간 전부터 12시간": (60 * 12, -2),
            "5. 48시간 전부터 24시간": (60 * 24, -2),
            "1": (60 * 6, -1),
            "2": (60 * 12, -1),
            "3": (60 * 24, -1),
            "4": (60 * 12, -2),
            "5": (60 * 24, -2),
        }
        not_ok = True
        if self.operator is None:
            self._send_text_message("자동 거래 운영중이 아닙니다", self.main_keyboard)
            return

        message = ""
        if self.in_progress_step == 1:
            if command in query_list.keys():

                def print_score_and_main_statement(score):
                    if score is None:
                        self._send_text_message("수익률 조회중 문제가 발생하였습니다.", self.main_keyboard)
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

                self.operator.get_score(print_score_and_main_statement, query_list[command])
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
        """현재까지 거래 기록을 메세지로 전송"""
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
        """프로그램 종료"""
        del frame
        self.terminating = True
        self.post_worker.stop()
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        print("Good Bye~")

    def on_exception(self, msg):
        self._send_text_message(f"트레이딩 중 문제가 발생하여 트레이딩이 중단되었습니다! {msg}", self.main_keyboard)
