"""실습용으로 만든 간단한 텔래그램 챗봇

1. 주기적으로 메세지를 읽어오기
2. 메세지를 분석해서 명령어를 추출하기
3. 텍스트 메세지 전송하기
4. 이미지 전송하기
"""
import signal
import time
import threading
from . import (
    LogManager,
    Worker,
)


class TelegramChatbot:
    """간단한 탤래그램 챗봇"""

    def __init__(self):
        self.logger = LogManager.get_logger("TelegramChatbot")
        self.get_worker = Worker("Chatbot-Get-Worker")
        self.post_worker = Worker("Chatbot-Post-Worker")
        self.terminating = False
        self.last_checking_time = 0
        self.polling_period = [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 2, 2, 5]
        self.polling_idx = 0

    def main(self):
        """main 함수"""
        print("##### telegram chatbot is started #####")

        signal.signal(signal.SIGINT, self._terminate)
        signal.signal(signal.SIGTERM, self._terminate)

        self._start_timer(self.polling_period[self.polling_idx])
        self.polling_idx += 1
        while not self.terminating:
            try:
                time.sleep(1)
            except EOFError:
                break

    def _handle_message(self, task):
        """주기적으로 텔레그램 메세지를 확인해서 명령어를 처리 후 타이머를 시작"""
        del task
        self.polling_idx += 1
        if self.polling_idx >= len(self.polling_period):
            self.polling_idx = len(self.polling_period) - 1
        self._start_timer(self.polling_period[self.polling_idx])

    def _start_timer(self, time):
        """메신저 확인 타이머 시작"""
        self.logger.debug(f"start timer {time}, {threading.get_ident()}")

        def on_timer_expired():
            self.get_worker.post_task({"runnable": self._handle_message})

        self.timer = threading.Timer(time, on_timer_expired)
        self.timer.start()

    def _stop_timer(self):
        """메신저 확인 타이머 중지"""
        pass

    def _initialize_operator(self, budget, interval=60):
        """오퍼레이터 초기화"""
        pass

    def _terminate(self, signum=None, frame=None):
        """프로그램 종료"""
        del frame
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        print("Good Bye~")


if __name__ == "__main__":
    tcb = TelegramChatbot()
    tcb.main()