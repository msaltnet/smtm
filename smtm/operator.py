import time
import threading
from datetime import datetime
from .log_manager import LogManager
from .worker import Worker


class Operator:
    """
    코어 모듈을 사용하여 시스템의 운영을 담당하는 클래스
    Classes that use core modules to run the system

    PERIODIC_RECORD :
        주기적으로 수익률 보고서와 그래프를 생성하는 기능
        Ability to generate periodic yield reports and graphs

    Attributes:
        data_provider: 사용될 DataProvider 인스턴스
        strategy: 사용될 Strategy 인스턴스
        trader: 사용될 Trader 인스턴스
        analyzer: 거래 분석용 Analyzer 인스턴스
        interval: 매매 프로세스가 수행되는 간격 # default 10 second
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    OUTPUT_FOLDER = "output/"
    PERIODIC_RECORD = True
    PERIODIC_RECORD_INFO = (360, -1)  # (turn, index) e.g. (360, -1) 최근 6시간
    PERIODIC_RECORD_INTERVAL_SEC = 300 * 60

    def __init__(self, alert_callback=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.data_provider = None
        self.strategy = None
        self.trader = None
        self.interval = 10  # default 10 second
        self.is_timer_running = False
        self.timer = None
        self.analyzer = None
        self.worker = Worker("Operator-Worker")
        self.state = None
        self.is_trading_activated = False
        self.tag = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.timer_expired_time = None
        self.last_report = None
        self.last_periodic_time = datetime.now()
        self.alert_callback = alert_callback

    def initialize(self, data_provider, strategy, trader, analyzer, budget=500):
        """
        운영에 필요한 모듈과 정보를 설정 및 각 모듈 초기화 수행

        data_provider: 운영에 사용될 DataProvider 객체
        strategy: 운영에 사용될 Strategy 객체
        trader: 운영에 사용될 Trader 객체
        analyzer: 운영에 사용될 Analyzer 객체
        """
        if self.state is not None:
            return

        def _add_spot_callback(date_time, value):
            analyzer.add_drawing_spot(date_time, value)

        def _add_line_callback(date_time, value):
            analyzer.add_value_for_line_graph(date_time, value)

        def _alert_callback(msg):
            if self.alert_callback is not None:
                self.alert_callback(msg)
            else:
                self.logger.warning(f"alert callback is called: {msg}")

        self.data_provider = data_provider
        self.strategy = strategy
        self.trader = trader
        self.analyzer = analyzer
        self.state = "ready"
        self.strategy.initialize(
            budget,
            add_spot_callback=_add_spot_callback,
            add_line_callback=_add_line_callback,
            alert_callback=_alert_callback,
        )
        self.analyzer.initialize(trader.get_account_info)
        self.tag = datetime.now().strftime("%Y%m%d-%H%M%S")
        try:
            self.tag += "-" + self.trader.NAME + "-" + self.strategy.CODE
        except AttributeError as err:
            self.logger.warning(
                f"can't get additional info form strategy and trader: {err}"
            )

    def set_interval(self, interval):
        """
        자동 거래 시간 간격을 설정한다.
        Set the time interval for automated trades.

        interval : 거래 프로세스가 수행되는 간격
        """
        self.interval = interval

    def start(self):
        if self.state != "ready":
            return False

        if self.is_timer_running:
            return False

        self.logger.info("===== Start operating =====")
        self.state = "running"
        self.analyzer.make_start_point()
        self.worker.start()
        self.worker.post_task({"runnable": self._execute_trading})
        return True

    def _start_timer(self):
        self.logger.debug(
            f"start timer {self.is_timer_running} : {self.state} : {threading.get_ident()}"
        )
        if self.is_timer_running or self.state != "running":
            return

        def on_timer_expired():
            self.timer_expired_time = datetime.now()
            self.worker.post_task({"runnable": self._execute_trading})

        if self.interval < 1:
            # call the handler directly to enhance performance. Timer create new thread always.
            self.is_timer_running = True
            on_timer_expired()
            return

        adjusted_interval = self.interval
        if self.interval > 1 and self.timer_expired_time is not None:
            time_delta = datetime.now() - self.timer_expired_time
            adjusted_interval = self.interval - round(time_delta.total_seconds(), 1)

        self.timer = threading.Timer(adjusted_interval, on_timer_expired)
        self.timer.start()

        self.is_timer_running = True
        return

    def _execute_trading(self, task):
        del task
        self.logger.debug("trading is started #####################")
        self.is_timer_running = False
        try:
            trading_info = self.data_provider.get_info()
            self.strategy.update_trading_info(trading_info)
            self.analyzer.put_trading_info(trading_info)
            self.logger.debug(f"trading_info {trading_info}")

            def send_request_callback(result):
                self.logger.debug("send_request_callback is called")
                if result == "error!":
                    self.logger.error("request fail")
                    return
                self.strategy.update_result(result)

                if "state" in result and result["state"] != "requested":
                    self.analyzer.put_result(result)

            target_request = self.strategy.get_request()
            self.logger.debug(f"target_request {target_request}")
            if target_request is not None:
                self.trader.send_request(target_request, send_request_callback)
                self.analyzer.put_requests(target_request)
        except (AttributeError, TypeError) as msg:
            self.logger.error(f"excuting fail {msg}")
        except Exception as exc:
            if self.alert_callback is not None:
                self.alert_callback("Something bad happened during trading")
            raise RuntimeError("Something bad happened during trading") from exc

        if self.PERIODIC_RECORD is True:
            self._periodic_internal_get_score()

        self.logger.debug("trading is completed #####################")
        self._start_timer()

    def stop(self):
        if self.state != "running":
            return None

        self.logger.info("cancel timer first")
        if self.timer is not None:
            self.timer.cancel()
        self.is_timer_running = False

        self.trader.cancel_all_requests()
        trading_info = self.data_provider.get_info()
        self.analyzer.put_trading_info(trading_info)
        self.last_report = self.analyzer.create_report(tag=self.tag)
        self.logger.info("===== Stop operating =====")
        self.state = "terminating"

        def on_terminated():
            self.state = "ready"

        self.worker.register_on_terminated(on_terminated)
        self.worker.stop()

        return self.last_report

    def get_score(self, callback, index_info=None, graph_tag=None):
        """
        현재 수익률을 인자로 전달받은 콜백함수를 통해 전달한다
        Pass the current yield to the callback function passed as an argument

        index_info: 수익률 구간 정보
            (
                interval: 구간의 길이로 turn의 갯수 예) 180: interval이 60인 경우 180분
                index: 구간의 인덱스 예) -1: 최근 180분, 0: 첫 180분
            )
        Returns:
            (
                start_budget: 시작 자산
                final_balance: 최종 자산
                cumulative_return : 기준 시점부터 누적 수익률
                price_change_ratio: 기준 시점부터 보유 종목별 가격 변동률 딕셔너리
                graph: 그래프 파일 패스
                return_high: 기간내 최고 수익률
                return_low: 기간내 최저 수익률
            )
        """

        if self.state != "running":
            self.logger.warning(f"invalid state : {self.state}")
            return

        def get_score_callback(task):
            now = datetime.now()

            if graph_tag is not None:
                graph_filename = (
                    f"{self.OUTPUT_FOLDER}g{round(time.time())}-{graph_tag}.jpg"
                )
            else:
                dt = now.strftime("%m%dT%H%M")
                graph_filename = f"{self.OUTPUT_FOLDER}g{round(time.time())}-{dt}.jpg"

            try:
                index_info = task["index_info"]
                task["callback"](
                    self.analyzer.get_return_report(
                        graph_filename=graph_filename, index_info=index_info
                    )
                )
            except TypeError as msg:
                self.logger.error(f"invalid callback {msg}")

        self.logger.info(f"get_score: {index_info}")
        self.worker.post_task(
            {
                "runnable": get_score_callback,
                "callback": callback,
                "index_info": index_info,
            }
        )

    def get_trading_results(self):
        return self.analyzer.get_trading_results()

    def _periodic_internal_get_score(self):
        now = datetime.now()
        time_delta = now - self.last_periodic_time

        if time_delta.total_seconds() < self.PERIODIC_RECORD_INTERVAL_SEC:
            return

        def internal_get_score_callback(score):
            self.logger.info(f"save score graph to {score[4]}")

        self.get_score(
            internal_get_score_callback,
            index_info=self.PERIODIC_RECORD_INFO,
            graph_tag=f"P{now.month:02d}{now.day:02d}T{now.hour:02d}{now.minute:02d}",
        )
        self.last_periodic_time = now
