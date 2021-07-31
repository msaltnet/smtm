"""실습용으로 만든 간단한 텔래그램 챗봇

1. 반복적으로 메세지를 읽어오기
2. 메세지를 분석해서 명령어를 추출하기
3. 명령어를 그대로 텍스트 메세지로 전송하기
4. 'image' 명령어를 수신할 경우 이미지 전송하기
"""
import os
import signal
import time
import threading
from urllib import parse
import requests
from dotenv import load_dotenv
from smtm import (
    LogManager,
    Worker,
)

load_dotenv()


class TelegramChatbot:
    """간단한 탤래그램 챗봇"""

    def __init__(self):
        self.API_HOST = "https://api.telegram.org/"
        self.TEST_FILE = "data/telegram_chatbot.jpg"
        self.TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "telegram_token")
        self.CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "telegram_chat_id"))
        self.POLLING_TIMEOUT = 10
        self.logger = LogManager.get_logger("TelegramChatbot")
        self.post_worker = Worker("Chatbot-Post-Worker")
        self.post_worker.start()
        self.terminating = False
        self.get_updates_thread = None
        self.last_update_id = 0

    def main(self):
        """main 함수"""
        print("##### telegram chatbot is started #####")

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


if __name__ == "__main__":
    tcb = TelegramChatbot()
    tcb.main()