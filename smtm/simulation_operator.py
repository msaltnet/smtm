from .log_manager import LogManager
from .operator import Operator

class SimulationOperator(Operator):
    """
    각 모듈을 연동해 시뮬레이션을 진행하는 클래스
    """

    def __init__(self):
        super().__init__()
        self.logger = LogManager.get_logger(__name__)

    def initialize(self, http, threading, dataProvider, strategy, trader, analyzer, end=None, count=100, budget=500):
        """
        시뮬레이션에 사용될 각 모듈을 전달 받아 초기화를 진행한다

        end: 언제까지의 거래기간 정보를 사용할 것인지에 대한 날짜 시간 정보 yyyy-MM-dd HH:mm:ss
        count: 사용될 거래 정도 갯수
        budget: 사용될 예산
        """
        super().initialize(http, threading, dataProvider, strategy, trader, analyzer)
        try:
            dataProvider.initialize_from_server(http, end=end, count=count)
            trader.initialize(http, end=end, count=count, budget=budget)
            strategy.initialize(budget)
            def handle_info_request(name, callback):
                if name == 'asset':
                    trader.send_account_info_request(callback)

            analyzer.initialize(handle_info_request)
        except AttributeError:
            self.is_initialized = False
            self.logger.error("initialize fail")

    def _excute_trading(self):
        """자동 거래를 실행 후 타이머를 실행한다"""
        self.logger.debug("##################### trading is started")
        self.is_timer_running = False
        try:
            self.strategy.update_trading_info(self.dp.get_info())
            def send_request_callback(result):
                self.logger.info("send_request_callback is called")
                if result.msg == 'game-over':
                    self.analyzer.create_report()
                    self.stop()
                    return
                self.strategy.update_result(result)
                self.analyzer.put_result(result)
            target_request = self.strategy.get_request()

            if target_request is not None:
                self.trader.send_request(target_request, send_request_callback)
                self.analyzer.put_request(target_request)
        except AttributeError:
            self.logger.error('excuting fail')

        self.logger.debug("##################### trading is completed")
        self._start_timer()
        return True

    def setup(self, interval):
        super().setup(interval)

    def start(self):
        return super().start()

    def stop(self):
        super().stop()
