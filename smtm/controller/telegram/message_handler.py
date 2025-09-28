"""
Telegram Message Handler
텔레그램 메시지 처리 담당 클래스

Handles Telegram API communication and message parsing.
텔레그램 API 통신 및 메시지 파싱을 담당합니다.
"""

import os
import time
import threading
from urllib import parse
from typing import Optional, Dict, Any, Callable
import requests
from dotenv import load_dotenv
from ...log_manager import LogManager
from ...worker import Worker

load_dotenv()


class TelegramMessageHandler:
    """
    Telegram Message Handler Class
    텔레그램 API 통신 및 메시지 처리를 담당하는 클래스

    Handles Telegram API communication and message processing.
    텔레그램 API 통신 및 메시지 처리를 담당합니다.
    """

    API_HOST = "https://api.telegram.org/"
    TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "telegram_token")
    CHAT_ID = int(os.environ.get("TELEGRAM_CHAT_ID", "123456"))
    POLLING_TIMEOUT = 10

    def __init__(self, token: Optional[str] = None, chat_id: Optional[str] = None):
        """
        Initialize Telegram Message Handler
        텔레그램 메시지 핸들러 초기화

        Args:
            token: Telegram bot token / 텔레그램 봇 토큰
            chat_id: Telegram chat ID / 텔레그램 채팅 ID
        """
        self.logger = LogManager.get_logger("TelegramMessageHandler")
        self.terminating = False
        self.last_update_id = 0
        self.message_callback: Optional[Callable[[str], None]] = None

        # Initialize Worker for asynchronous message sending
        # 비동기 메시지 전송을 위한 Worker 초기화
        self.post_worker = Worker("Telegram-Message-Worker")
        self.post_worker.start()

        if token is not None:
            self.TOKEN = token
        if chat_id is not None:
            self.CHAT_ID = int(chat_id)

        if token == "telegram_token":
            self.logger.error("Telegram token is not set")
            raise ValueError("Telegram token is not set")

    def set_message_callback(self, callback: Callable[[str], None]) -> None:
        """
        Set message callback function
        메시지 수신 시 호출될 콜백 함수를 설정합니다.

        Args:
            callback: Function to call when message is received / 메시지 수신 시 호출할 함수
        """
        self.message_callback = callback

    def start_polling(self) -> None:
        """
        Start message polling
        메시지 폴링을 시작합니다.
        """

        def looper():
            self.logger.debug(f"start get updates thread: {threading.get_ident()}")
            while not self.terminating:
                self._handle_message()
                time.sleep(0.5)

        get_updates_thread = threading.Thread(
            target=looper, name="get updates", daemon=True
        )
        get_updates_thread.start()

    def stop_polling(self) -> None:
        """
        Stop message polling
        메시지 폴링을 중지합니다.
        """
        self.terminating = True
        self.post_worker.stop()

    def _handle_message(self) -> None:
        """
        Handle incoming Telegram messages
        텔레그램 메시지를 확인해서 명령어를 처리합니다.
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
                    if "text" in result["message"] and self.message_callback:
                        self.message_callback(result["message"]["text"])
                    self.last_update_id = result["update_id"]
        except (ValueError, KeyError) as err:
            self.logger.error(f"Invalid data from server: {err}")

    def _get_updates(self) -> Optional[Dict[str, Any]]:
        """
        Get new messages using getUpdates API
        getUpdates API로 새로운 메시지를 가져옵니다.

        Returns:
            Updates dictionary or None if failed / 업데이트 딕셔너리 또는 실패 시 None
        """
        offset = self.last_update_id + 1
        return self._send_http(
            f"{self.API_HOST}{self.TOKEN}/getUpdates?offset={offset}&timeout={self.POLLING_TIMEOUT}"
        )

    def send_text_message(self, text: str, keyboard: Optional[str] = None) -> None:
        """
        Send text message asynchronously
        텍스트 메시지를 비동기로 전송합니다.

        Args:
            text: Message text to send / 전송할 메시지 텍스트
            keyboard: Optional keyboard markup / 선택적 키보드 마크업
        """
        encoded_text = parse.quote(text)
        if keyboard is not None:
            url = f"{self.API_HOST}{self.TOKEN}/sendMessage?chat_id={self.CHAT_ID}&text={encoded_text}&reply_markup={keyboard}"
        else:
            url = f"{self.API_HOST}{self.TOKEN}/sendMessage?chat_id={self.CHAT_ID}&text={encoded_text}"

        def send_message(task):
            if not self._send_http(task["url"]):
                self.logger.error(f"send message failed: {text}")

        # Use Worker for asynchronous processing (prevent main thread blocking)
        # Worker를 사용하여 비동기 처리 (메인 스레드 블로킹 방지)
        self.post_worker.post_task({"runnable": send_message, "url": url})

    def send_image_message(self, file_path: str) -> None:
        """
        Send image message asynchronously
        이미지 메시지를 비동기로 전송합니다.

        Args:
            file_path: Path to image file / 이미지 파일 경로
        """
        url = f"{self.API_HOST}{self.TOKEN}/sendPhoto?chat_id={self.CHAT_ID}"

        def send_image(task):
            if not self._send_http(task["url"], is_post=True, file=task["file"]):
                self.logger.error(f"send image failed: {task['file']}")

        # Use Worker for asynchronous processing
        # Worker를 사용하여 비동기 처리
        self.post_worker.post_task(
            {"runnable": send_image, "url": url, "file": file_path}
        )

    def _send_http(
        self, url: str, is_post: bool = False, file: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Send HTTP request
        HTTP 요청을 전송합니다.

        Args:
            url: Request URL / 요청 URL
            is_post: Whether to use POST method / POST 메서드 사용 여부
            file: Optional file to upload / 업로드할 선택적 파일

        Returns:
            Response dictionary or None if failed / 응답 딕셔너리 또는 실패 시 None
        """
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
