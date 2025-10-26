"""
Refactored Analyzer Class
리팩터링된 Analyzer 클래스

Combines separated components while maintaining the existing interface.
분할된 컴포넌트들을 조합하여 기존 인터페이스를 유지합니다.
"""

from typing import List, Dict, Any, Optional, Callable, Tuple
from ..log_manager import LogManager
from .data_repository import DataRepository
from .data_analyzer import DataAnalyzer
from .graph_generator import GraphGenerator
from .report_generator import ReportGenerator


class Analyzer:
    """
    Refactored Trading Analyzer
    리팩터링된 거래 분석기

    Combines separated components by applying the Single Responsibility Principle.
    단일 책임 원칙을 적용하여 분할된 컴포넌트들을 조합합니다.
    """

    def __init__(self, sma_info: Tuple[int, int, int] = (10, 40, 120)):
        """
        Initialize Analyzer
        Analyzer 초기화

        Args:
            sma_info: SMA (Simple Moving Average) configuration tuple / SMA 설정 튜플
        """
        self.logger = LogManager.get_logger("Analyzer")

        # Initialize components
        # 컴포넌트 초기화
        self.data_repository = DataRepository()
        self.data_analyzer = DataAnalyzer()
        self.graph_generator = GraphGenerator(sma_info)
        self.report_generator = ReportGenerator()

        # Callback functions
        # 콜백 함수
        self.get_asset_info_func: Optional[Callable] = None
        self.alert_callback: Optional[Callable] = None

        # Attributes for backward compatibility
        # 하위 호환성을 위한 속성들
        self.request_list = self.data_repository.request_list
        self.result_list = self.data_repository.result_list
        self.info_list = self.data_repository.info_list
        self.asset_info_list = self.data_repository.asset_info_list
        self.score_list = self.data_repository.score_list
        self.spot_list = self.data_repository.spot_list
        self.line_graph_list = self.data_repository.line_graph_list
        self.start_asset_info = self.data_repository.start_asset_info
        self.is_simulation = self.data_repository.is_simulation
        self.sma_info = sma_info
        
        # Additional attributes for backward compatibility
        # 추가 하위 호환성 속성들
        self.OUTPUT_FOLDER = "output/"
        self.GRAPH_MAX_COUNT = 1000
        self.RSI_ENABLE = False
        self.RSI = (30, 70, 2)

    def initialize(
        self, get_asset_info_func: Callable, alert_callback: Optional[Callable] = None
    ) -> None:
        """
        Initialize with callback functions
        콜백 함수와 함께 초기화합니다.

        Args:
            get_asset_info_func: Function to get asset information / 자산 정보를 가져오는 함수
            alert_callback: Optional alert callback function / 선택적 알림 콜백 함수
        """
        self.get_asset_info_func = get_asset_info_func
        self.alert_callback = alert_callback

    def add_drawing_spot(self, date_time: str, value: float) -> None:
        """
        Add drawing spot position
        그래프에 그려질 점의 위치를 저장합니다.

        Args:
            date_time: Date and time string / 날짜 시간 문자열
            value: Spot value / 점의 값
        """
        self.data_repository.add_spot(date_time, value)

    def add_value_for_line_graph(self, date_time: str, value: float) -> None:
        """
        Add value for additional line graph
        추가 선 그래프의 값을 저장합니다.

        Args:
            date_time: Date and time string / 날짜 시간 문자열
            value: Line graph value / 선 그래프 값
        """
        self.data_repository.add_line_graph_value(date_time, value)

    def put_trading_info(self, info: List[Dict[str, Any]]) -> None:
        """
        Store trading information
        거래 정보를 저장합니다.

        Args:
            info: List of trading information / 거래 정보 리스트
        """
        self.data_repository.add_trading_info(info)
        self.make_periodic_record()

    def put_requests(self, requests: List[Dict[str, Any]]) -> None:
        """
        Store trading request information
        거래 요청 정보를 저장합니다.

        Args:
            requests: List of trading requests / 거래 요청 리스트
        """
        self.data_repository.add_requests(requests)

    def put_result(self, result: Dict[str, Any]) -> None:
        """
        Store trading result information
        거래 결과 정보를 저장합니다.

        Args:
            result: Trading result dictionary / 거래 결과 딕셔너리
        """
        self.data_repository.add_result(result)
        self.update_asset_info()

    def update_asset_info(self) -> None:
        """
        Update asset information
        자산 정보를 업데이트합니다.
        """
        if self.get_asset_info_func is None:
            self.logger.warning("get_asset_info_func is NOT set")
            return

        asset_info = self.get_asset_info_func()
        self.data_repository.add_asset_info(asset_info)
        self.make_score_record(asset_info)

    def make_start_point(self) -> None:
        """
        Set starting point
        시작점을 설정합니다.
        """
        self.data_repository.set_start_point()
        self.update_asset_info()

    def update_start_point(self, info: Dict[str, Any]) -> None:
        """
        Update starting point
        시작점을 업데이트합니다.

        Args:
            info: Asset information dictionary / 자산 정보 딕셔너리
        """
        self.data_repository.update_start_point(info)

    def make_periodic_record(self) -> None:
        """
        Create periodic record
        주기적 기록을 생성합니다.
        """
        if self.data_repository.should_make_periodic_record():
            self.update_asset_info()

    def make_score_record(self, new_info: Dict[str, Any]) -> None:
        """
        Create return rate record
        수익률 기록을 생성합니다.

        Args:
            new_info: New asset information / 새로운 자산 정보
        """
        if self.data_repository.start_asset_info is None:
            return

        score_record = self.data_analyzer.create_score_record(
            self.data_repository.start_asset_info, new_info
        )

        if score_record:
            self.data_repository.add_score_record(score_record)

    def get_return_report(
        self, graph_filename: Optional[str] = None, index_info: Optional[Tuple] = None
    ) -> Optional[Tuple]:
        """
        Get return report
        수익률 보고서를 반환합니다.

        Args:
            graph_filename: Optional graph filename / 선택적 그래프 파일명
            index_info: Optional index information for interval data / 구간 데이터용 선택적 인덱스 정보

        Returns:
            Return report summary tuple or None / 수익률 보고서 요약 튜플 또는 None
        """
        self.update_asset_info()

        asset_info_list = self.data_repository.asset_info_list
        score_list = self.data_repository.score_list
        info_list = self.data_repository.info_list
        result_list = self.data_repository.result_list
        spot_list = self.data_repository.spot_list
        line_graph_list = self.data_repository.line_graph_list

        if index_info is not None:
            interval_data = self.data_repository.get_interval_data(index_info)
            asset_info_list = interval_data[0]
            score_list = interval_data[1]
            info_list = interval_data[2]
            result_list = interval_data[3]
            spot_list = interval_data[4]
            line_graph_list = interval_data[5]

        # Generate graph
        # 그래프 생성
        if graph_filename is not None:
            graph = self.graph_generator.draw_graph(
                info_list,
                result_list,
                score_list,
                graph_filename,
                is_fullpath=True,
                spot_list=spot_list,
                line_graph_list=line_graph_list,
            )
        else:
            graph = None

        # Generate summary
        # 요약 생성
        summary = self.report_generator.create_return_report_summary(
            asset_info_list,
            score_list,
            info_list,
            result_list,
            graph_filename=graph,
            spot_list=spot_list,
            line_graph_list=line_graph_list,
        )

        return summary

    def get_trading_results(self) -> List[Dict[str, Any]]:
        """
        Get trading results
        거래 결과를 반환합니다.

        Returns:
            List of trading results / 거래 결과 리스트
        """
        return self.data_repository.get_trading_results()

    def create_report(self, tag: str = "untitled-report") -> Optional[Dict[str, Any]]:
        """
        Create return rate report
        수익률 보고서를 생성합니다.

        Args:
            tag: Report tag name / 보고서 태그명

        Returns:
            Report dictionary or None / 보고서 딕셔너리 또는 None
        """
        try:
            summary = self.get_return_report()
            if summary is None:
                self.logger.error("invalid return report")
                return None

            trading_table = self.report_generator.create_trading_table(
                self.data_repository.request_list,
                self.data_repository.info_list,
                self.data_repository.score_list,
                self.data_repository.result_list,
            )

            # Create report file
            # 보고서 파일 생성
            self.report_generator.create_report_file(tag, summary, trading_table)

            # Generate graph
            # 그래프 생성
            self.graph_generator.draw_graph(
                self.data_repository.info_list,
                self.data_repository.result_list,
                self.data_repository.score_list,
                tag,
                spot_list=self.data_repository.spot_list,
                line_graph_list=self.data_repository.line_graph_list,
            )

            return {"summary": summary, "trading_table": trading_table}

        except (IndexError, AttributeError):
            self.logger.error("create report FAIL")
            return None

    def make_rsi(self, prices: List[float], count: int = 14) -> Optional[List[float]]:
        """
        Calculate RSI (Relative Strength Index)
        RSI를 계산합니다.

        Args:
            prices: List of prices / 가격 리스트
            count: RSI calculation period / RSI 계산 기간

        Returns:
            RSI values list or None / RSI 값 리스트 또는 None
        """
        return self.data_analyzer.calculate_rsi(prices, count)

    def dump(self, filename: str = "dump") -> None:
        """
        Dump data to files
        데이터를 파일로 덤프합니다.

        Args:
            filename: Base filename for dump files / 덤프 파일의 기본 파일명
        """
        self._write_to_file(filename + ".1", self.data_repository.request_list)
        self._write_to_file(filename + ".2", self.data_repository.result_list)
        self._write_to_file(filename + ".3", self.data_repository.info_list)
        self._write_to_file(filename + ".4", self.data_repository.asset_info_list)
        self._write_to_file(filename + ".5", self.data_repository.score_list)

    def load_dump(self, filename: str = "dump") -> None:
        """
        Load data from files
        파일에서 데이터를 로드합니다.

        Args:
            filename: Base filename for dump files / 덤프 파일의 기본 파일명
        """
        self.data_repository.request_list = self._load_list_from_file(filename + ".1")
        self.data_repository.result_list = self._load_list_from_file(filename + ".2")
        self.data_repository.info_list = self._load_list_from_file(filename + ".3")
        self.data_repository.asset_info_list = self._load_list_from_file(
            filename + ".4"
        )
        self.data_repository.score_list = self._load_list_from_file(filename + ".5")

    @staticmethod
    def _write_to_file(filename: str, target_list: List[Dict[str, Any]]) -> None:
        """
        Write list to file
        리스트를 파일로 저장합니다.

        Args:
            filename: Target filename / 대상 파일명
            target_list: List to save / 저장할 리스트
        """
        import ast

        # Ensure filename is a string
        # 파일명이 문자열인지 확인
        filename = str(filename)

        with open(filename, "w", encoding="utf-8") as dump_file:
            dump_file.write("[\n")
            for item in target_list:
                dump_file.write(f"{item},\n")
            dump_file.write("]\n")

    @staticmethod
    def _load_list_from_file(filename: str) -> List[Dict[str, Any]]:
        """
        Load list from file
        파일에서 리스트를 로드합니다.

        Args:
            filename: Source filename / 소스 파일명

        Returns:
            Loaded list / 로드된 리스트
        """
        import ast

        # Ensure filename is a string
        # 파일명이 문자열인지 확인
        filename = str(filename)

        with open(filename, "r", encoding="utf-8") as dump_file:
            data = dump_file.read()
            target_list = ast.literal_eval(data)
            return target_list

    @staticmethod
    def _get_min_max_return(score_list: List[Dict[str, Any]]) -> Tuple[float, float]:
        """
        Get minimum and maximum return values
        최소 및 최대 수익률 값을 반환합니다.

        Args:
            score_list: List of score records / 점수 기록 리스트

        Returns:
            Tuple of (min_return, max_return) / (최소 수익률, 최대 수익률) 튜플
        """
        if not score_list:
            return 0.0, 0.0
        
        returns = [record.get("cumulative_return", 0.0) for record in score_list]
        return min(returns), max(returns)

    def _get_rss_memory(self) -> float:
        """
        Get RSS memory usage
        RSS 메모리 사용량을 반환합니다.

        Returns:
            Memory usage in MB / MB 단위의 메모리 사용량
        """
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024

    def _make_alert(self, msg: str) -> None:
        """
        Send alert
        알림을 전송합니다.

        Args:
            msg: Alert message / 알림 메시지
        """
        if self.alert_callback is not None:
            self.alert_callback(msg)
