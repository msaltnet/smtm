"""
Graph Generation Class
그래프 생성 클래스

Handles graph generation and visualization using matplotlib.
matplotlib을 사용한 그래프 생성과 시각화를 담당합니다.
"""

import os
import pandas as pd
import matplotlib
import mplfinance as mpf
import numpy as np
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from ..log_manager import LogManager

matplotlib.use("Agg")


class GraphGenerator:
    """
    Graph Generation Class
    그래프 생성을 담당하는 클래스

    Handles graph generation and visualization using matplotlib and mplfinance.
    matplotlib과 mplfinance를 사용한 그래프 생성과 시각화를 담당합니다.
    """

    OUTPUT_FOLDER = "output/"
    GRAPH_MAX_COUNT = 1440
    RSI_ENABLE = False
    RSI = (30, 70, 14)  # set (low, high, count) tuple to draw e.g. (30, 70, 14)

    def __init__(self, sma_info: Tuple[int, int, int] = (10, 40, 120)):
        """
        Initialize Graph Generator
        그래프 생성기 초기화

        Args:
            sma_info: SMA (Simple Moving Average) configuration tuple / SMA 설정 튜플
        """
        self.logger = LogManager.get_logger("GraphGenerator")
        self.sma_info = sma_info

        if not os.path.isdir(self.OUTPUT_FOLDER):
            os.mkdir(self.OUTPUT_FOLDER)

    def create_plot_data(
        self,
        info_list: List[Dict[str, Any]],
        result_list: List[Dict[str, Any]],
        score_list: List[Dict[str, Any]],
        spot_list: Optional[List[Dict[str, Any]]] = None,
        line_graph_list: Optional[List[Dict[str, Any]]] = None,
    ) -> pd.DataFrame:
        """
        Create data for graph plotting
        그래프를 그리기 위한 데이터를 생성합니다.

        Args:
            info_list: Trading information list / 거래 정보 리스트
            result_list: Trading result list / 거래 결과 리스트
            score_list: Score list / 점수 리스트
            spot_list: Optional spot list / 선택적 스팟 리스트
            line_graph_list: Optional line graph list / 선택적 선 그래프 리스트

        Returns:
            DataFrame for plotting / 그래프 그리기용 DataFrame
        """
        result_pos = 0
        score_pos = 0
        spot_pos = 0
        line_pos = 0
        last_avr_price = None
        last_acc_return = 0
        plot_data = []

        # Create a single table by combining trading, return rate information for graph plotting
        # 그래프를 그리기 위해 매매, 수익률 정보를 트레이딩 정보와 합쳐서 하나의 테이블로 생성
        for info in info_list:
            new = info.copy()
            info_time = datetime.strptime(info["date_time"], "%Y-%m-%dT%H:%M:%S")

            # Generate and add trading information
            # 매매 정보를 생성해서 추가
            while result_pos < len(result_list):
                result = result_list[result_pos]
                result_time = datetime.strptime(
                    result["date_time"], "%Y-%m-%dT%H:%M:%S"
                )
                if info_time < result_time:
                    break

                if result["type"] == "buy":
                    new["buy"] = result["price"]
                elif result["type"] == "sell":
                    new["sell"] = result["price"]
                result_pos += 1

            # Generate and add additional spot information
            # 추가 spot 정보를 생성해서 추가
            if spot_list is not None:
                spot_pos = self._add_spot_plot_info(spot_list, spot_pos, new, info_time)

            # Generate and add additional line graph information
            # 추가 line graph 정보를 생성해서 추가
            if line_graph_list is not None:
                line_pos = self._add_line_plot_info(
                    line_graph_list, line_pos, new, info_time
                )

            # Add return rate information
            # 수익률 정보를 추가
            while score_pos < len(score_list):
                score = score_list[score_pos]
                score_time = datetime.strptime(score["date_time"], "%Y-%m-%dT%H:%M:%S")

                if info_time >= score_time:
                    new["return"] = last_acc_return = score["cumulative_return"]
                    last_avr_price = None

                    if (
                        len(score["asset"]) > 0
                        and score["asset"][0][1] > 0  # 평균 가격
                        and score["asset"][0][3] > 0  # 현재 수량
                    ):
                        new["avr_price"] = last_avr_price = score["asset"][0][1]
                    score_pos += 1
                else:
                    new["return"] = last_acc_return
                    if last_avr_price is not None:
                        new["avr_price"] = last_avr_price
                    break
            plot_data.append(new)

        if len(plot_data) > self.GRAPH_MAX_COUNT:
            self.logger.warning(
                f"Graph data is trimmed. {len(plot_data)} -> {self.GRAPH_MAX_COUNT}"
            )

        return pd.DataFrame(plot_data)[-self.GRAPH_MAX_COUNT :]

    def _add_line_plot_info(
        self,
        line_graph_list: List[Dict[str, Any]],
        line_pos: int,
        new: Dict[str, Any],
        info_time: datetime,
    ) -> int:
        """
        Add line graph information
        라인 그래프 정보를 추가합니다.

        Args:
            line_graph_list: Line graph data list / 라인 그래프 데이터 리스트
            line_pos: Current line position / 현재 라인 위치
            new: New data dictionary / 새로운 데이터 딕셔너리
            info_time: Information time / 정보 시간

        Returns:
            Updated line position / 업데이트된 라인 위치
        """
        line_graph_info = self._get_single_info(line_graph_list, line_pos, info_time)
        if line_graph_info[0] is not None:
            new["line_graph"] = line_graph_info[0]
        return line_graph_info[1]

    def _add_spot_plot_info(
        self,
        spot_list: List[Dict[str, Any]],
        spot_pos: int,
        new: Dict[str, Any],
        info_time: datetime,
    ) -> int:
        """
        Add spot information
        스팟 정보를 추가합니다.

        Args:
            spot_list: Spot data list / 스팟 데이터 리스트
            spot_pos: Current spot position / 현재 스팟 위치
            new: New data dictionary / 새로운 데이터 딕셔너리
            info_time: Information time / 정보 시간

        Returns:
            Updated spot position / 업데이트된 스팟 위치
        """
        spot_info = self._get_single_info(spot_list, spot_pos, info_time)
        if spot_info[0] is not None:
            new["spot"] = spot_info[0]
        return spot_info[1]

    def _get_single_info(
        self, target_list: List[Dict[str, Any]], start_pos: int, ref_time: datetime
    ) -> Tuple[Optional[float], int]:
        """
        Get single information
        단일 정보를 가져옵니다.

        Args:
            target_list: Target data list / 대상 데이터 리스트
            start_pos: Starting position / 시작 위치
            ref_time: Reference time / 참조 시간

        Returns:
            Tuple of (value, position) / (값, 위치) 튜플
        """
        target_pos = start_pos
        target_info = None

        while target_pos < len(target_list):
            item = target_list[target_pos]
            target_item_time = datetime.strptime(item["date_time"], "%Y-%m-%dT%H:%M:%S")
            if ref_time < target_item_time:
                break
            target_info = item["value"]
            target_pos += 1

        return target_info, target_pos

    def draw_graph(
        self,
        info_list: List[Dict[str, Any]],
        result_list: List[Dict[str, Any]],
        score_list: List[Dict[str, Any]],
        filename: str,
        is_fullpath: bool = False,
        spot_list: Optional[List[Dict[str, Any]]] = None,
        line_graph_list: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Draw graph
        그래프를 그립니다.

        Args:
            info_list: Trading information list / 거래 정보 리스트
            result_list: Trading result list / 거래 결과 리스트
            score_list: Score list / 점수 리스트
            filename: Graph filename / 그래프 파일명
            is_fullpath: Whether filename is full path / 파일명이 전체 경로인지 여부
            spot_list: Optional spot list / 선택적 스팟 리스트
            line_graph_list: Optional line graph list / 선택적 선 그래프 리스트

        Returns:
            Graph file path / 그래프 파일 경로
        """
        spots = None
        if spot_list is not None:
            spots = sorted(
                spot_list,
                key=lambda x: (datetime.strptime(x["date_time"], "%Y-%m-%dT%H:%M:%S"),),
            )

        line_values = None
        if line_graph_list is not None:
            line_values = sorted(
                line_graph_list,
                key=lambda x: (datetime.strptime(x["date_time"], "%Y-%m-%dT%H:%M:%S"),),
            )

        total = self.create_plot_data(
            info_list,
            result_list,
            score_list,
            spot_list=spots,
            line_graph_list=line_values,
        )

        total = total.rename(
            columns={
                "date_time": "Date",
                "opening_price": "Open",
                "high_price": "High",
                "low_price": "Low",
                "closing_price": "Close",
                "acc_volume": "Volume",
            }
        )
        total = total.set_index("Date")
        total.index = pd.to_datetime(total.index)

        apds = []

        # Add RSI
        # RSI 추가
        if self.RSI_ENABLE:
            rsi = self._calculate_rsi(total["Close"], count=self.RSI[2])
            if rsi is not None:
                rsi_low = np.full(len(rsi), self.RSI[0])
                rsi_high = np.full(len(rsi), self.RSI[1])
                apds.append(
                    mpf.make_addplot(
                        rsi, panel=2, color="lime", ylim=(10, 90), secondary_y=False
                    )
                )
                apds.append(
                    mpf.make_addplot(
                        rsi_low, panel=2, color="red", width=0.5, secondary_y=False
                    )
                )
                apds.append(
                    mpf.make_addplot(
                        rsi_high, panel=2, color="red", width=0.5, secondary_y=False
                    )
                )

        # Add trading points
        # 매매 포인트 추가
        if "buy" in total.columns:
            apds.append(
                mpf.make_addplot(
                    total["buy"], type="scatter", markersize=100, marker="^"
                )
            )
        if "sell" in total.columns:
            apds.append(
                mpf.make_addplot(
                    total["sell"], type="scatter", markersize=100, marker="v"
                )
            )
        if "avr_price" in total.columns:
            apds.append(mpf.make_addplot(total["avr_price"]))
        if "return" in total.columns:
            apds.append(
                mpf.make_addplot(
                    (total["return"]), panel=1, color="g", secondary_y=True
                )
            )
        if "spot" in total.columns:
            apds.append(
                mpf.make_addplot(
                    (total["spot"]),
                    type="scatter",
                    markersize=50,
                    marker=".",
                    color="g",
                )
            )
        if "line_graph" in total.columns:
            apds.append(
                mpf.make_addplot(
                    (total["line_graph"]), color="red", width=0.7, secondary_y=True
                )
            )

        destination = self.OUTPUT_FOLDER + filename + ".jpg"
        if is_fullpath:
            destination = filename

        fig_save_opt = {"fname": destination, "dpi": 300, "pad_inches": 0.25}
        candle_type = "candle" if len(total["Close"]) < 500 else "line"

        mpf.plot(
            total,
            type=candle_type,
            volume=True,
            addplot=apds,
            mav=self.sma_info,
            style="starsandstripes",
            savefig=fig_save_opt,
            figscale=1.25,
        )

        self.logger.info(f'"{destination}" graph file created!')
        return destination

    def _calculate_rsi(
        self, prices: pd.Series, count: int = 14
    ) -> Optional[List[float]]:
        """
        Calculate RSI (Relative Strength Index)
        RSI를 계산합니다.

        Args:
            prices: Price series / 가격 시리즈
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
            delta = deltas[i - 1]

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
