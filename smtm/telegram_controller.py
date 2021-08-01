"""텔래그램 챗봇을 활용한 시스템 운영 인터페이스

Operator를 사용해서 시스템을 컨트롤하는 모듈
"""
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
    Operator,
)

load_dotenv()


class TelegramController:
    """smtm 탤래그램 챗봇 컨트롤러"""

    def __init__(self):
        self.API_HOST = "https://api.telegram.org/"
        self.TEST_FILE = "data/telegram_chatbot.jpg"
        self.TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "telegram_token")
        self.CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "telegram_chat_id"))
        self.POLLING_TIMEOUT = 10
        self.logger = LogManager.get_logger("TelegramController")
        self.post_worker = Worker("Chatbot-Post-Worker")
        self.post_worker.start()
        # chatbot variable
        self.terminating = False
        self.get_updates_thread = None
        self.last_update_id = 0
        self.in_progress = None
        self.main_keyboard = None
        # smtm variable
        self.operator = None
        self.interval = None
        self.budget = None
        self.strategy_num = None
        self.strategy = None
        self.command_list = []
        self._create_command()
        self.main_guide = {
            "ready": "자동 거래 시작 전입니다.\n명령어를 입력해주세요.",
            "running": "자동 거래 운영 중입니다.\n명령어를 입력해주세요."
        }
        LogManager.set_stream_level(30)

    def _create_command(self):
        """명령어 정보를 생성한다"""
        self.command_list = [
            {
                "guide": "{0:15}자동 거래 시작".format("1. 시작"),
                "cmd": ["시작", "1", "1. 시작"],
                "action": self._start_trading,
            },
            {
                "guide": "{0:15}자동 거래 중지".format("2. 중지"),
                "cmd": ["중지", "2", "2. 중지"],
                "action": self._stop_trading,
            },
            {
                "guide": "{0:15}운영 상태 조회".format("3. 상태 조회"),
                "cmd": ["상태", "3", "3. 상태 조회", "상태 조회"],
                "action": self._query_state,
            },
            {
                "guide": "{0:15}수익률 조회".format("4. 수익률 조회"),
                "cmd": ["수익", "4", "수익률 조회", "4. 수익률 조회"],
                "action": self._query_score,
            },
            {
                "guide": "{0:15}거래내역 조회".format("5. 거래내역 조회"),
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

        self.get_updates_thread = threading.Thread(target=looper, name="get updates", daemon=True)
        self.get_updates_thread.start()

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
        except (ValueError, KeyError):
            self.logger.error("Invalid data from server")

    def _execute_command(self, command):
        self.logger.debug(f"_execute_command: {command}")
        found = False
        try:
            if self.in_progress is not None:
                self.in_progress(command)
                return
        except TypeError:
            self.logger.debug("invalid in_progress")

        for item in self.command_list:
            if command in item["cmd"]:
                found = True
                item["action"](command)

        if not found:
            if self.operator is None:
                message = self.main_guide["ready"]
            else:
                message = self.main_guide["running"]
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
        except ValueError:
            self.logger.error("Invalid data from server")
            return None
        except requests.exceptions.HTTPError as msg:
            self.logger.error(msg)
            return None
        except requests.exceptions.RequestException as msg:
            self.logger.error(msg)
            return None

        return result

    def _initialize_operator(self, budget, interval=60):
        """오퍼레이터 초기화"""
        pass

    def _start_trading(self, command):
        """자동 거래 시작"""
        pass

    def _stop_trading(self, command):
        """자동 거래 중지"""
        pass

    def _query_state(self, command):
        """현재 상태를 메세지로 전송"""
        if self.operator is None:
            message = "자동 거래 시작 전입니다."
        else:
            message = "자동 거래 운영 중입니다."
        self._send_text_message(message)

    def _query_score(self, command):
        """구간 수익률과 그래프를 메세지로 전송"""

        def print_score_and_main_statement(score):
            print("current score ==========")
            print(score)

        self.operator.get_score(print_score_and_main_statement)

    def _query_trading_records(self, command):
        """현재까지 거래 기록을 메세지로 전송"""

    def _terminate(self, signum=None, frame=None):
        """프로그램 종료"""
        del frame
        self.terminating = True
        self.post_worker.stop()
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        print("Good Bye~")
