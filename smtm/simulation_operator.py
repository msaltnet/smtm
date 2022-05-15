"""시뮬레이션에 사용되는 모듈들을 연동하여 시뮬레이션을 운영하는 SimulationOperator 클래스"""

import time
from datetime import datetime
from .log_manager import LogManager
from .operator import Operator


class SimulationOperator(Operator):
    """각 모듈을 연동해 시뮬레이션을 진행하는 클래스"""
    PERIODIC_RECORD_INFO = (360, -1)  # (turn, index) e.g. (360, -1) 최근 6시간
    PERIODIC_RECORD_INTERVAL_TURN = 300

    def __init__(self, periodic_record_enable=False):
        super().__init__()
        self.logger = LogManager.get_logger(__class__.__name__)
        self.turn = 0
        self.budget = 0
        self.current_turn = 0
        self.last_periodic_turn = 0
        self.periodic_record_enable = periodic_record_enable

    def _execute_trading(self, task):
        """자동 거래를 실행 후 타이머를 실행한다

        simulation_terminated 상태는 시뮬레이션에만 존재하는 상태로서 시뮬레이션이 끝났으나
        Operator는 중지되지 않은 상태. Operator의 시작과 중지는 외부부터 실행되어야 한다.
        """
        del task
        self.logger.info(f"############# Simulation trading is started : {self.turn + 1}")
        self.is_timer_running = False
        try:
            self.current_turn += 1
            trading_info = self.data_provider.get_info()
            self.strategy.update_trading_info(trading_info)
            self.analyzer.put_trading_info(trading_info)

            def send_request_callback(result):
                self.logger.debug("send_request_callback is called")
                if result == "pass":
                    return

                if result == "error!":
                    self.logger.error("request fail")
                    return

                if result["msg"] == "game-over":
                    trading_info = self.data_provider.get_info()
                    self.analyzer.put_trading_info(trading_info)
                    self.last_report = self.analyzer.create_report(tag=self.tag)
                    self.state = "simulation_terminated"
                    return

                self.strategy.update_result(result)
                self.analyzer.put_result(result)

            target_request = self.strategy.get_request()
            if target_request is None:
                self.logger.error("request should be submitted at simulation!")
                return
            self.trader.send_request(target_request, send_request_callback)
            self.analyzer.put_requests(target_request)

            if self.periodic_record_enable is True:
                self._periodic_internal_get_score()

        except AttributeError as err:
            self.logger.error(f"excuting fail: {err}")

        self.turn += 1
        self.logger.debug("############# Simulation trading is completed")
        self._start_timer()

    def get_score(self, callback, index_info=None, graph_tag=None):
        """현재 수익률을 인자로 전달받은 콜백함수를 통해 전달한다
        시뮬레이션이 종료된 경우 마지막 수익률 전달한다

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
            self.logger.debug("already terminated return last report")
            callback(self.last_report["summary"])
            return

        def get_score_callback(task):
            now = datetime.now()
            if graph_tag is not None:
                graph_filename = f"{self.OUTPUT_FOLDER}gs{round(time.time())}-{graph_tag}.jpg"
            else:
                graph_filename = f"{self.OUTPUT_FOLDER}gs{round(time.time())}-{now.month:02d}{now.day:02d}T{now.hour:02d}{now.minute:02d}.jpg"

            try:
                index_info = task["index_info"]
                task["callback"](
                    self.analyzer.get_return_report(
                        graph_filename=graph_filename, index_info=index_info
                    )
                )
            except TypeError as err:
                self.logger.error(f"invalid callback: {err}")

        self.worker.post_task(
            {"runnable": get_score_callback, "callback": callback, "index_info": index_info}
        )

    def _periodic_internal_get_score(self):
        if self.current_turn - self.last_periodic_turn < self.PERIODIC_RECORD_INTERVAL_TURN:
            return

        def internal_get_score_callback(score):
            self.logger.info(f"save score graph to {score[4]}")

        self.get_score(
            internal_get_score_callback,
            index_info=self.PERIODIC_RECORD_INFO,
            graph_tag=f"P{self.current_turn:06d}",
        )
        self.last_periodic_turn = self.current_turn
