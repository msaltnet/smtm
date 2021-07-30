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
    Worker,
    StrategyBuyAndHold,
    StrategySma0,
    Operator,
)


class TelegramController:
    """smtm 탤래그램 챗봇 컨트롤러"""

    def __init__(self):
        self.logger = LogManager.get_logger("TelegramController")
        self.worker = Worker("Chatbot-Worker")
        self.terminating = False
        self.operator = None
        self.interval = None
        self.budget = None
        self.strategy_num = None
        self.strategy = None
        self.need_init = True

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
        """메신저 확인 타이머 시작"""
        pass

    def _stop_timer(self):
        """메신저 확인 타이머 중지"""
        pass

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

    def terminate(self, signum=None, frame=None):
        """프로그램 종료"""
        del frame
        if signum is not None:
            print("강제 종료 신호 감지")
        print("프로그램 종료 중.....")
        self._stop_trading()
        self._finalize_operator()
        self.terminating = True
        print("Good Bye~")
