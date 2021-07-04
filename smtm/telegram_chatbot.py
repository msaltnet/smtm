"""텔래그램 챗봇을 활용한 시스템 운영 인터페이스

Operator를 사용해서 시스템을 컨트롤하는 모듈
"""
import signal
import time
from . import (
    LogManager,
    Analyzer,
    UpbitTrader,
    UpbitDataProvider,
    BithumbTrader,
    BithumbDataProvider,
    StrategyBuyAndHold,
    StrategySma0,
    Operator,
)


class TelegramChatbot:
    """smtm 탤래그램 챗봇 컨트롤러"""

    def __init__(self):
        self.logger = LogManager.get_logger("TelegramChatbot")
        self.terminating = False
        self.operator = None
        LogManager.set_stream_level(30)

    def main(self):
        """main 함수"""
        print("##### smtm telegram chatbot is started #####")

        signal.signal(signal.SIGINT, self.terminate)
        signal.signal(signal.SIGTERM, self.terminate)

        while not self.terminating:
            try:
                time.sleep(0.5)
            except EOFError:
                break

    def check_message(self):
        """주기적으로 텔레그램 메세지를 확인해서 명령어를 처리"""
        pass

    def _start_timer(self):
        pass

    def _stop_timer(self):
        pass

    def _initialize_operator(self):
        pass

    def _start_trading(self):
        pass

    def _stop_trading(self):
        pass
