"""텔래그램 챗봇을 활용한 시스템 운영 인터페이스

Operator를 사용해서 시스템을 컨트롤하는 모듈
"""
import os
import signal
import time
import threading
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
        # smtm variable
        self.operator = None
        self.interval = None
        self.budget = None
        self.strategy_num = None
        self.strategy = None
        self.need_init = True
        self.command_list = []
        self.create_command()
        LogManager.set_stream_level(30)

    def create_command(self):
        """명령어 정보를 생성한다"""
        self.command_list = [
            {
                "guide": "{0:15}챗봇 상태 조회".format("0. 상태"),
                "cmd": ["상태", "0"],
                "action": None,
            },
            {
                "guide": "{0:15}자동 거래 초기화".format("1. 초기화"),
                "cmd": ["초기화", "1"],
                "action": None,
            },
            {
                "guide": "{0:15}자동 거래 시작".format("2. 시작"),
                "cmd": ["시작", "2"],
                "action": None,
            },
            {
                "guide": "{0:15}자동 거래 중지".format("3. 중지"),
                "cmd": ["중지", "3"],
                "action": None,
            },
            {
                "guide": "{0:15}수익률 조회".format("4. 수익"),
                "cmd": ["수익", "4"],
                "action": None,
            },
            {
                "guide": "{0:15}거래내역 조회".format("5. 거래"),
                "cmd": ["거래", "5"],
                "action": None,
            },
        ]

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

    def _initialize_operator(self, budget, interval=60):
        """오퍼레이터 초기화"""
        pass

    def _start_trading(self):
        """자동 거래 시작"""
        pass

    def _stop_trading(self):
        """자동 거래 중지"""
        pass

    def get_state(self):
        """현재 상태 출력 출력"""
        pass

    def get_score(self, index=None):
        """현재 수익률과 그래프 출력"""
        pass

    def get_trading_record(self, count=-1):
        """현재까지 거래 기록 출력"""
        pass

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
                commands = []
                for result in updates["result"]:
                    self.logger.debug(f'result: {result["message"]["chat"]["id"]} : {self.CHAT_ID}')
                    if result["message"]["chat"]["id"] != self.CHAT_ID:
                        continue
                    if "text" in result["message"]:
                        commands.append(result["message"]["text"])
                    self.last_update_id = result["update_id"]
                self._execute_command(commands)
        except (ValueError, KeyError):
            self.logger.error("Invalid data from server")

    def _execute_command(self, commands):
        for command in commands:
            self.logger.debug(f"_execute_command: {command}")
            if command == "photo":
                self._send_image_message(self.TEST_FILE)
            else:
                self._send_text_message(command)

    def _send_text_message(self, text):
        encoded_text = parse.quote(text)
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

    def _terminate(self, signum=None, frame=None):
        """프로그램 종료"""
        del frame
        self.terminating = True
        self.post_worker.stop()
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        print("Good Bye~")
