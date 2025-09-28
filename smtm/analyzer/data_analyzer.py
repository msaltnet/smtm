"""
Data Analysis Class
데이터 분석 클래스

Handles return rate calculation, statistical analysis, etc.
수익률 계산, 통계 분석 등을 담당합니다.
"""

import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from ..log_manager import LogManager


class DataAnalyzer:
    """
    Data Analysis Class
    데이터 분석을 담당하는 클래스

    Handles data analysis tasks such as return rate calculation and statistical analysis.
    수익률 계산 및 통계 분석 등의 데이터 분석 작업을 담당합니다.
    """

    def __init__(self):
        """
        Initialize Data Analyzer
        데이터 분석기 초기화
        """
        self.logger = LogManager.get_logger("DataAnalyzer")

    def calculate_cumulative_return(
        self, start_asset_info: Dict[str, Any], current_asset_info: Dict[str, Any]
    ) -> float:
        """
        Calculate cumulative return rate
        누적 수익률을 계산합니다.

        Args:
            start_asset_info: Starting asset information / 시작 자산 정보
            current_asset_info: Current asset information / 현재 자산 정보

        Returns:
            Cumulative return rate percentage / 누적 수익률 퍼센트
        """
        try:
            start_total = self._get_property_total_value(start_asset_info)
            current_total = self._get_property_total_value(current_asset_info)

            if start_total == 0:
                return 0.0

            cumulative_return = (current_total - start_total) / start_total * 100
            return round(cumulative_return, 3)
        except (IndexError, AttributeError) as e:
            self.logger.error(f"Failed to calculate cumulative return: {e}")
            return 0.0

    def calculate_asset_yields(
        self, start_asset_info: Dict[str, Any], current_asset_info: Dict[str, Any]
    ) -> List[Tuple[str, float, float, float, float]]:
        """
        Calculate asset-specific return rates
        자산별 수익률을 계산합니다.

        Args:
            start_asset_info: Starting asset information / 시작 자산 정보
            current_asset_info: Current asset information / 현재 자산 정보

        Returns:
            List of tuples (asset_name, buy_avg, current_price, amount, yield_rate) /
            (자산명, 평균매수가, 현재가, 수량, 수익률) 튜플 리스트
        """
        asset_list = []
        start_quote = start_asset_info["quote"]
        current_quote = current_asset_info["quote"]

        for name, item in current_asset_info["asset"].items():
            amount = float(item[1])
            buy_avg = float(item[0])
            price = float(current_quote[name])

            item_yield = 0
            if buy_avg != 0:
                item_yield = (price - buy_avg) / buy_avg * 100
                item_yield = round(item_yield, 3)

            asset_list.append((name, buy_avg, price, amount, item_yield))

        return asset_list

    def calculate_price_change_ratios(
        self, start_asset_info: Dict[str, Any], current_asset_info: Dict[str, Any]
    ) -> Dict[str, float]:
        """
        Calculate price change ratios
        가격 변동률을 계산합니다.

        Args:
            start_asset_info: Starting asset information / 시작 자산 정보
            current_asset_info: Current asset information / 현재 자산 정보

        Returns:
            Dictionary of asset name to price change ratio / 자산명별 가격 변동률 딕셔너리
        """
        price_change_ratio = {}
        start_quote = start_asset_info["quote"]
        current_quote = current_asset_info["quote"]

        for name in current_asset_info["asset"].keys():
            start_price = start_quote[name]
            current_price = current_quote[name]

            if start_price != 0:
                ratio = (current_price - start_price) / start_price * 100
                price_change_ratio[name] = round(ratio, 3)
            else:
                price_change_ratio[name] = 0.0

        return price_change_ratio

    def calculate_min_max_returns(
        self, score_list: List[Dict[str, Any]]
    ) -> Tuple[float, float]:
        """
        Calculate minimum and maximum return rates
        최고/최저 수익률을 계산합니다.

        Args:
            score_list: List of score records / 점수 기록 리스트

        Returns:
            Tuple of (min_return, max_return) / (최저수익률, 최고수익률) 튜플
        """
        if not score_list:
            return 0.0, 0.0

        return_list = [score["cumulative_return"] for score in score_list]
        return min(return_list), max(return_list)

    def calculate_rsi(
        self, prices: List[float], count: int = 14
    ) -> Optional[List[float]]:
        """
        Calculate RSI (Relative Strength Index)
        RSI를 계산합니다.

        Args:
            prices: List of prices / 가격 리스트
            count: RSI calculation period / RSI 계산 기간

        Returns:
            RSI values list or None / RSI 값 리스트 또는 None
        """
        if len(prices) <= count:
            return None

        deltas = np.diff(prices)
        seed = deltas[:count]
        up_avg = seed[seed >= 0].sum() / count
        down_avg = -seed[seed < 0].sum() / count

        if down_avg == 0:
            return None

        r_strength = up_avg / down_avg
        rsi = np.zeros_like(prices)
        rsi[: count + 1] = 100.0 - 100.0 / (1.0 + r_strength)

        for i in range(count + 1, len(prices)):
            delta = deltas[i - 1]  # cause the diff is 1 shorter

            if delta > 0:
                upval = delta
                downval = 0.0
            else:
                upval = 0.0
                downval = -delta

            up_avg = (up_avg * (count - 1) + upval) / count
            down_avg = (down_avg * (count - 1) + downval) / count

            if down_avg == 0:
                return None

            r_strength = up_avg / down_avg
            rsi[i] = 100.0 - 100.0 / (1.0 + r_strength)

        return rsi.tolist()

    @staticmethod
    def _get_property_total_value(asset_info: Dict[str, Any]) -> float:
        """
        Calculate total asset value
        총 자산 가치를 계산합니다.

        Args:
            asset_info: Asset information dictionary / 자산 정보 딕셔너리

        Returns:
            Total asset value / 총 자산 가치
        """
        total = float(asset_info["balance"])
        quote = asset_info["quote"]

        for name, item in asset_info["asset"].items():
            total += float(item[1]) * float(quote[name])

        return round(total)

    def create_score_record(
        self, start_asset_info: Dict[str, Any], current_asset_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create return rate record
        수익률 기록을 생성합니다.

        Args:
            start_asset_info: Starting asset information / 시작 자산 정보
            current_asset_info: Current asset information / 현재 자산 정보

        Returns:
            Score record dictionary / 점수 기록 딕셔너리
        """
        try:
            cumulative_return = self.calculate_cumulative_return(
                start_asset_info, current_asset_info
            )
            asset_list = self.calculate_asset_yields(
                start_asset_info, current_asset_info
            )
            price_change_ratio = self.calculate_price_change_ratios(
                start_asset_info, current_asset_info
            )

            return {
                "balance": float(current_asset_info["balance"]),
                "cumulative_return": cumulative_return,
                "price_change_ratio": price_change_ratio,
                "asset": asset_list,
                "date_time": current_asset_info["date_time"],
                "kind": 3,
            }
        except (IndexError, AttributeError) as e:
            self.logger.error(f"Failed to create score record: {e}")
            return {}
