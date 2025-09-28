"""
Data Repository Class
데이터 저장소 클래스

Handles storage, retrieval, and management of trading data.
거래 데이터의 저장, 조회, 관리를 담당합니다.
"""

import copy
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Callable
from ..log_manager import LogManager


class DataRepository:
    """
    Data Repository Class
    거래 데이터의 저장, 조회, 관리를 담당하는 클래스

    Manages storage, retrieval, and management of trading data.
    거래 데이터의 저장, 조회, 관리를 담당합니다.
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    RECORD_INTERVAL = 60

    def __init__(self):
        """
        Initialize Data Repository
        데이터 저장소 초기화
        """
        self.logger = LogManager.get_logger("DataRepository")

        # Data storage
        # 데이터 저장소
        self.request_list: List[Dict[str, Any]] = []
        self.result_list: List[Dict[str, Any]] = []
        self.info_list: List[Dict[str, Any]] = []
        self.asset_info_list: List[Dict[str, Any]] = []
        self.score_list: List[Dict[str, Any]] = []
        self.spot_list: List[Dict[str, Any]] = []
        self.line_graph_list: List[Dict[str, Any]] = []

        # Starting point information
        # 시작점 정보
        self.start_asset_info: Optional[Dict[str, Any]] = None
        self.is_simulation = False

    def add_trading_info(self, info: List[Dict[str, Any]]) -> None:
        """
        Store trading information
        거래 정보를 저장합니다.

        Args:
            info: List of trading information / 거래 정보 리스트
        """
        target = None
        for item in info:
            if item["type"] == "primary_candle":
                target = item
                break

        if target is None:
            return

        new = copy.deepcopy(target)
        new["kind"] = 0
        self.info_list.append(new)

    def add_requests(self, requests: List[Dict[str, Any]]) -> None:
        """
        Store trading request information
        거래 요청 정보를 저장합니다.

        Args:
            requests: List of trading requests / 거래 요청 리스트
        """
        for request in requests:
            new = copy.deepcopy(request)
            if request["type"] == "cancel":
                new["price"] = 0
                new["amount"] = 0
            else:
                if float(request["price"]) <= 0 or float(request["amount"]) <= 0:
                    continue
                new["price"] = float(new["price"])
                new["amount"] = float(new["amount"])
            new["kind"] = 1
            self.request_list.append(new)

    def add_result(self, result: Dict[str, Any]) -> None:
        """
        Store trading result information
        거래 결과 정보를 저장합니다.

        Args:
            result: Trading result dictionary / 거래 결과 딕셔너리
        """
        try:
            if float(result["price"]) <= 0 or float(result["amount"]) <= 0:
                return
        except KeyError as err:
            self.logger.warning(f"Invalid result: {err}")
            return

        new = copy.deepcopy(result)
        new["price"] = float(new["price"])
        new["amount"] = float(new["amount"])
        new["kind"] = 2
        self.result_list.append(new)

    def add_asset_info(self, asset_info: Dict[str, Any]) -> None:
        """
        Store asset information
        자산 정보를 저장합니다.

        Args:
            asset_info: Asset information dictionary / 자산 정보 딕셔너리
        """
        new = copy.deepcopy(asset_info)
        new["balance"] = float(new["balance"])

        if self.start_asset_info is None and len(self.asset_info_list) == 0:
            self.start_asset_info = new

        self.asset_info_list.append(new)

    def add_spot(self, date_time: str, value: float) -> None:
        """
        Store spot position for graph
        그래프에 그려질 점의 위치를 저장합니다.

        Args:
            date_time: Date and time string / 날짜 시간 문자열
            value: Spot value / 점의 값
        """
        self.spot_list.append({"date_time": date_time, "value": value})

    def add_line_graph_value(self, date_time: str, value: float) -> None:
        """
        Store additional line graph value
        추가 선 그래프의 값을 저장합니다.

        Args:
            date_time: Date and time string / 날짜 시간 문자열
            value: Line graph value / 선 그래프 값
        """
        self.line_graph_list.append({"date_time": date_time, "value": value})

    def add_score_record(self, score_record: Dict[str, Any]) -> None:
        """
        Store return rate record
        수익률 기록을 저장합니다.

        Args:
            score_record: Score record dictionary / 점수 기록 딕셔너리
        """
        score_record["kind"] = 3
        self.score_list.append(score_record)

    def reset_data(self) -> None:
        """
        Reset all data
        모든 데이터를 초기화합니다.
        """
        self.request_list = []
        self.result_list = []
        self.info_list = []
        self.asset_info_list = []
        self.score_list = []
        self.spot_list = []
        self.line_graph_list = []
        self.start_asset_info = None

    def set_start_point(self) -> None:
        """
        Set starting point
        시작점을 설정합니다.
        """
        self.start_asset_info = None
        self.request_list = []
        self.result_list = []
        self.asset_info_list = []

    def update_start_point(self, info: Dict[str, Any]) -> None:
        """
        Update starting point
        시작점을 업데이트합니다.

        Args:
            info: Asset information dictionary / 자산 정보 딕셔너리
        """
        self.start_asset_info = info

    def get_trading_results(self) -> List[Dict[str, Any]]:
        """
        Get trading results
        거래 결과를 반환합니다.

        Returns:
            List of trading results / 거래 결과 리스트
        """
        return self.result_list

    def get_interval_data(self, index_info: tuple) -> tuple:
        """
        Get interval-specific data
        구간별 데이터를 반환합니다.

        Args:
            index_info: Index information tuple (period, index) / 인덱스 정보 튜플 (기간, 인덱스)

        Returns:
            Tuple of filtered data lists / 필터링된 데이터 리스트들의 튜플
        """
        period = index_info[0]
        index = index_info[1]
        start = period * index
        end = start + period if index != -1 else None

        if abs(start) > len(self.info_list):
            if start < 0:
                info_list = self.info_list[:period]
            else:
                last = period * -1
                info_list = self.info_list[last:]
        else:
            info_list = self.info_list[start:end]

        start_dt = datetime.strptime(info_list[0]["date_time"], self.ISO_DATEFORMAT)
        end_dt = datetime.strptime(info_list[-1]["date_time"], self.ISO_DATEFORMAT)

        # Workaround for short term query
        # w/a for short term query
        if start_dt == end_dt:
            end_dt = end_dt + timedelta(minutes=2)

        score_list = []
        asset_info_list = []
        result_list = []
        spot_list = []
        line_graph_list = []

        self._make_filtered_list(start_dt, end_dt, score_list, self.score_list)
        self._make_filtered_list(
            start_dt, end_dt, asset_info_list, self.asset_info_list
        )
        self._make_filtered_list(start_dt, end_dt, result_list, self.result_list)
        self._make_filtered_list(start_dt, end_dt, spot_list, self.spot_list)
        self._make_filtered_list(
            start_dt, end_dt, line_graph_list, self.line_graph_list
        )

        return (
            asset_info_list,
            score_list,
            info_list,
            result_list,
            spot_list,
            line_graph_list,
        )

    @staticmethod
    def _make_filtered_list(
        start_dt: datetime, end_dt: datetime, dest: List, source: List
    ) -> None:
        """
        Filter data within time range
        시간 범위에 맞는 데이터를 필터링합니다.

        Args:
            start_dt: Start datetime / 시작 날짜시간
            end_dt: End datetime / 종료 날짜시간
            dest: Destination list / 대상 리스트
            source: Source list / 소스 리스트
        """
        for target in source:
            target_dt = datetime.strptime(
                target["date_time"], DataRepository.ISO_DATEFORMAT
            )
            if start_dt <= target_dt <= end_dt:
                dest.append(target)

    def should_make_periodic_record(self) -> bool:
        """
        Check if periodic record should be created
        주기적 기록을 생성해야 하는지 확인합니다.

        Returns:
            True if periodic record should be created, False otherwise /
            주기적 기록을 생성해야 하면 True, 그렇지 않으면 False
        """
        if not self.asset_info_list:
            return True

        now = datetime.now()
        if self.is_simulation:
            now = datetime.strptime(
                self.info_list[-1]["date_time"], self.ISO_DATEFORMAT
            )

        last = datetime.strptime(
            self.asset_info_list[-1]["date_time"], self.ISO_DATEFORMAT
        )
        delta = now - last

        return delta.total_seconds() > self.RECORD_INTERVAL
