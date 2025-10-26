"""
Report Generation Class
보고서 생성 클래스

Handles trading report generation and file output.
거래 보고서 생성과 파일 출력을 담당합니다.
"""

import os
import psutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from ..log_manager import LogManager


class ReportGenerator:
    """
    Report Generation Class
    보고서 생성을 담당하는 클래스

    Handles trading report generation and file output.
    거래 보고서 생성과 파일 출력을 담당합니다.
    """

    OUTPUT_FOLDER = "output/"
    DEBUG_MODE = False

    def __init__(self):
        """
        Initialize Report Generator
        보고서 생성기 초기화
        """
        self.logger = LogManager.get_logger("ReportGenerator")

        if not os.path.isdir(self.OUTPUT_FOLDER):
            os.mkdir(self.OUTPUT_FOLDER)

    def create_report_file(
        self, filepath: str, summary: Tuple, trading_table: List[Dict[str, Any]]
    ) -> None:
        """
        Output report to file
        보고서를 파일로 출력합니다.

        Args:
            filepath: Report file path / 보고서 파일 경로
            summary: Summary tuple / 요약 튜플
            trading_table: Trading table data / 거래 테이블 데이터
        """
        # Ensure filepath is a string
        # 파일 경로가 문자열인지 확인
        filepath = str(filepath)
        final_path = self.OUTPUT_FOLDER + filepath + ".txt"

        with open(final_path, "w", encoding="utf-8") as report_file:
            if len(trading_table) > 0:
                report_file.write(
                    "### TRADING TABLE =================================\n"
                )

            for item in trading_table:
                if item["kind"] == 0:
                    report_file.write(
                        f"{item['date_time']}, {item['opening_price']}, {item['high_price']}, {item['low_price']}, {item['closing_price']}, {item['acc_price']}, {item['acc_volume']}\n"
                    )
                elif item["kind"] == 1:
                    report_file.write(
                        f"{item['date_time']}, [->] {item['id']}, {item['type']}, {item['price']}, {item['amount']}\n"
                    )
                elif item["kind"] == 2:
                    report_file.write(
                        f"{item['date_time']}, [<-] {item['request']['id']}, {item['type']}, {item['price']}, {item['amount']}, {item['msg']}\n"
                    )
                elif item["kind"] == 3:
                    report_file.write(
                        f"{item['date_time']}, [#] {item['balance']}, {item['cumulative_return']}, {item['price_change_ratio']}, {item['asset']}\n"
                    )

            report_file.write("### SUMMARY =======================================\n")
            report_file.write(
                f"Property                 {summary[0]:10} -> {summary[1]:10}\n"
            )
            report_file.write(
                f"Gap                                    {summary[1] - summary[0]:10}\n"
            )
            report_file.write(
                f"Cumulative return                    {summary[2]:10} %\n"
            )
            report_file.write(f"Price_change_ratio {summary[3]}\n")

            if self.DEBUG_MODE:
                self._write_debug_info(report_file)

    def _write_debug_info(self, report_file) -> None:
        """
        Write debug information
        디버그 정보를 작성합니다.

        Args:
            report_file: Report file object / 보고서 파일 객체
        """
        try:
            rss = self._get_rss_memory()
            report_file.write("### DEBUG INFO ====================================\n")
            report_file.write(f"memory usage: {rss: 10.5f} MB\n")
            # Additional debug information can be implemented as needed
            # 추가 디버그 정보는 필요에 따라 구현
        except Exception:
            # Skip debug info if it fails
            # 디버그 정보 작성이 실패하면 건너뜁니다
            pass

    @staticmethod
    def _get_rss_memory() -> float:
        """
        Get memory usage
        메모리 사용량을 반환합니다.

        Returns:
            Memory usage in MB / MB 단위의 메모리 사용량
        """
        try:
            process = psutil.Process()
            return process.memory_info().rss / 2**20  # Convert bytes to MB / Bytes to MB
        except (TypeError, AttributeError, OSError, Exception):
            # Handle cases where psutil is not available or fails
            # psutil이 사용 불가능하거나 실패하는 경우 처리
            return 0.0

    def create_trading_table(
        self,
        request_list: List[Dict[str, Any]],
        info_list: List[Dict[str, Any]],
        score_list: List[Dict[str, Any]],
        result_list: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Create trading table
        거래 테이블을 생성합니다.

        Args:
            request_list: Trading request list / 거래 요청 리스트
            info_list: Trading information list / 거래 정보 리스트
            score_list: Score list / 점수 리스트
            result_list: Trading result list / 거래 결과 리스트

        Returns:
            Sorted trading table / 정렬된 거래 테이블
        """
        list_sum = request_list + info_list + score_list + result_list
        trading_table = sorted(
            list_sum,
            key=lambda x: (
                datetime.strptime(x["date_time"], "%Y-%m-%dT%H:%M:%S"),
                x["kind"],
            ),
        )
        return trading_table

    def format_summary_log(self, summary: Tuple) -> None:
        """
        Format and output summary to log
        요약 정보를 로그로 출력합니다.

        Args:
            summary: Summary tuple / 요약 튜플
        """
        self.logger.info("### Return Report ===============================")
        self.logger.info(f"Property                 {summary[0]:10} -> {summary[1]:10}")
        self.logger.info(
            f"Gap                                    {summary[1] - summary[0]:10}"
        )
        self.logger.info(f"Cumulative return                    {summary[2]:10} %")
        self.logger.info(f"Price_change_ratio {summary[3]}")
        self.logger.info(f"Period {summary[5]}")

    def create_return_report_summary(
        self,
        asset_info_list: List[Dict[str, Any]],
        score_list: List[Dict[str, Any]],
        info_list: List[Dict[str, Any]],
        result_list: List[Dict[str, Any]],
        graph_filename: Optional[str] = None,
        spot_list: Optional[List[Dict[str, Any]]] = None,
        line_graph_list: Optional[List[Dict[str, Any]]] = None,
    ) -> Optional[Tuple]:
        """
        Create return report summary
        수익률 보고서 요약을 생성합니다.

        Args:
            asset_info_list: Asset information list / 자산 정보 리스트
            score_list: Score list / 점수 리스트
            info_list: Trading information list / 거래 정보 리스트
            result_list: Trading result list / 거래 결과 리스트
            graph_filename: Optional graph filename / 선택적 그래프 파일명
            spot_list: Optional spot list / 선택적 스팟 리스트
            line_graph_list: Optional line graph list / 선택적 선 그래프 리스트

        Returns:
            Summary tuple or None / 요약 튜플 또는 None
        """
        try:
            from .data_analyzer import DataAnalyzer

            analyzer = DataAnalyzer()

            start_value = analyzer._get_property_total_value(asset_info_list[0])
            last_value = analyzer._get_property_total_value(asset_info_list[-1])
            last_return = score_list[-1]["cumulative_return"]
            change_ratio = score_list[-1]["price_change_ratio"]
            min_max = analyzer.calculate_min_max_returns(score_list)

            period = info_list[0]["date_time"] + " - " + info_list[-1]["date_time"]

            summary = (
                start_value,
                last_value,
                last_return,
                change_ratio,
                graph_filename,  # Graph file path is set separately / 그래프 파일 경로는 별도로 설정
                period,
                min_max[0],
                min_max[1],
                (
                    asset_info_list[0]["date_time"],
                    info_list[0]["date_time"],
                    info_list[-1]["date_time"],
                ),
            )

            self.format_summary_log(summary)
            return summary

        except (IndexError, AttributeError) as err:
            self.logger.error("get return report FAIL")
            self.logger.error(err)
            return None
