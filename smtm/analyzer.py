"""거래 요청, 결과 정보를 저장하고 투자 결과를 분석하는 Analayzer 클래스"""

import copy
import os
from datetime import datetime
from datetime import timedelta
import ast
import matplotlib
import pandas as pd
import mplfinance as mpf
import psutil
import numpy as np
from .log_manager import LogManager

matplotlib.use("Agg")


class Analyzer:
    """거래 요청, 결과 정보를 저장하고 투자 결과를 분석하는 클래스

    request_list: 거래 요청 데이터 목록
    result_list: 거래 결과 데이터 목록
    info_list: 거래 데이터 목록
    asset_info_list: 특정 시점에 기록된 자산 데이터 목록
    score_list: 특정 시점에 기록된 수익률 데이터 목록
    get_asset_info_func: 자산 정보 업데이트를 요청하기 위한 콜백 함수
    """

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
    OUTPUT_FOLDER = "output/"
    RECORD_INTERVAL = 60
    GRAPH_MAX_COUNT = 1440
    DEBUG_MODE = True
    RSI = None  # set (low, high, count) tuple to draw e.g. (30, 70, 14)

    def __init__(self, sma_info=(10, 40, 60)):
        self.request_list = []
        self.result_list = []
        self.info_list = []
        self.asset_info_list = []
        self.score_list = []
        self.spot_list = []
        self.start_asset_info = None
        self.get_asset_info_func = None
        self.logger = LogManager.get_logger(__class__.__name__)
        self.is_simulation = False
        self.sma_info = sma_info

        if os.path.isdir("output") is False:
            os.mkdir("output")

    def initialize(self, get_asset_info_func):
        """콜백 함수를 입력받아 초기화한다

        get_asset_info_func: 거래 데이터를 요청하는 함수로 func(arg1) arg1은 정보 타입
        """
        self.get_asset_info_func = get_asset_info_func

    def add_drawing_spot(self, date_time, value):
        """그래프에 그려질 점의 위치를 입력받아서 저장한다

        date_time: 그래프의 시간축 정보로 info_list의 date_time과 같은 형식
        value: 그래프의 y축에 해당하는 정보로 price 정보와 비슷한 수준의 값을 갖는 것이 좋다
        """
        self.spot_list.append({"date_time": date_time, "value": value})

    def put_trading_info(self, info):
        """거래 정보를 저장한다

        kind: 보고서를 위한 데이터 종류
            0: 거래 데이터
            1: 매매 요청
            2: 매매 결과
            3: 수익률 정보
        """
        new = copy.deepcopy(info)
        new["kind"] = 0
        self.info_list.append(new)
        self.make_periodic_record()

    def put_requests(self, requests):
        """거래 요청 정보를 저장한다

        request:
        {
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간
        }
        kind: 보고서를 위한 데이터 종류
            0: 거래 데이터
            1: 매매 요청
            2: 매매 결과
            3: 수익률 정보
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

    def put_result(self, result):
        """거래 결과 정보를 저장한다

        request: 거래 요청 정보
        result:
        {
            "request": 요청 정보
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "state": 거래 상태 requested, done
            "msg": 거래 결과 메세지
            "date_time": 시뮬레이션 모드에서는 데이터 시간 +2초
        }
        kind: 보고서를 위한 데이터 종류
            0: 거래 데이터
            1: 매매 요청
            2: 매매 결과
            3: 수익률 정보
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
        self.update_asset_info()

    def update_asset_info(self):
        """자산 정보를 저장한다

        returns:
        {
            balance: 계좌 현금 잔고
            asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
            quote: 종목별 현재 가격 딕셔너리
        }
        """
        if self.get_asset_info_func is None:
            self.logger.warning("get_asset_info_func is NOT set")
            return

        asset_info = self.get_asset_info_func()
        new = copy.deepcopy(asset_info)
        new["balance"] = float(new["balance"])
        if self.start_asset_info is None and len(self.asset_info_list) == 0:
            self.start_asset_info = new
        self.asset_info_list.append(new)
        self.make_score_record(new)

    def make_start_point(self):
        """시작시점 거래정보를 기록한다"""
        self.start_asset_info = None
        self.request_list = []
        self.result_list = []
        self.asset_info_list = []
        self.update_asset_info()

    def update_start_point(self, info):
        """기준 시작 자산 정보를 변경한다"""
        self.start_asset_info = info

    def make_periodic_record(self):
        """최소 간격을 유지하며 수익율을 기록한다
        RECORD_INTERVAL: 수익률 기록 간의 최소 시간(초)
        """
        now = datetime.now()
        if self.is_simulation:
            now = datetime.strptime(self.info_list[-1]["date_time"], self.ISO_DATEFORMAT)

        last = datetime.strptime(self.asset_info_list[-1]["date_time"], self.ISO_DATEFORMAT)
        delta = now - last

        if delta.total_seconds() > self.RECORD_INTERVAL:
            self.update_asset_info()

    def make_score_record(self, new_info):
        """수익률 기록을 생성한다

        score_record:
            balance: 계좌 현금 잔고
            cumulative_return: 시스템 시작 시점부터 누적 수익률
            price_change_ratio: 시스템 시작 시점부터 보유 종목별 가격 변동률 딕셔너리
            asset: 자산 정보 튜플 리스트 (종목, 평균 가격, 현재 가격, 수량, 수익률(소숫점3자리))
            date_time: 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간
            kind: 3, 보고서를 위한 데이터 종류
        """

        try:
            start_total = self.__get_start_property_value(self.start_asset_info)
            start_quote = self.start_asset_info["quote"]
            current_total = float(new_info["balance"])
            current_quote = new_info["quote"]
            cumulative_return = 0
            new_asset_list = []
            price_change_ratio = {}
            self.logger.debug(f"make_score_record new_info {new_info}")

            for name, item in new_info["asset"].items():
                item_yield = 0
                amount = float(item[1])
                buy_avg = float(item[0])
                price = float(current_quote[name])
                current_total += amount * price
                item_price_diff = price - buy_avg
                if item_price_diff != 0 and buy_avg != 0:
                    item_yield = (price - buy_avg) / buy_avg * 100
                    item_yield = round(item_yield, 3)

                self.logger.debug(
                    f"yield record {name}, buy_avg: {buy_avg}, {price}, {amount}, {item_yield}"
                )
                new_asset_list.append((name, buy_avg, price, amount, item_yield))
                start_price = start_quote[name]
                price_change_ratio[name] = 0
                price_diff = price - start_price
                if price_diff != 0:
                    price_change_ratio[name] = price_diff / start_price * 100
                    price_change_ratio[name] = round(price_change_ratio[name], 3)
                self.logger.debug(
                    f"price change ratio {start_price} -> {price}, {price_change_ratio[name]}%"
                )

            total_diff = current_total - start_total
            if total_diff != 0:
                cumulative_return = (current_total - start_total) / start_total * 100
                cumulative_return = round(cumulative_return, 3)
            self.logger.info(
                f"cumulative_return {start_total} -> {current_total}, {cumulative_return}%"
            )

            self.score_list.append(
                {
                    "balance": float(new_info["balance"]),
                    "cumulative_return": cumulative_return,
                    "price_change_ratio": price_change_ratio,
                    "asset": new_asset_list,
                    "date_time": new_info["date_time"],
                    "kind": 3,
                }
            )
        except (IndexError, AttributeError) as msg:
            self.logger.error(f"making score record fail {msg}")

    def get_return_report(self, graph_filename=None, index_info=None):
        """현시점 기준 간단한 수익률 보고서를 제공한다

        index_info: 수익률 구간 정보
            (
                interval: 구간의 길이로 turn의 갯수 예) 180: interval이 60인 경우 180분
                index: 구간의 인덱스 예) -1: 최근 180분, 0: 첫 180분
            )
        Returns:
            (
                start_budget: 시작 자산
                final_balance: 최종 자산
                cumulative_return: 시스템 시작 시점부터 누적 수익률
                price_change_ratio: 시스템 시작 시점부터 보유 종목별 가격 변동률 딕셔너리
                graph: 그래프 파일 패스
                period: 수익률 산출 구간
                return_high: 기간내 최고 수익률
                return_low: 기간내 최저 수익률
                date_info: 시스템 시작 시간, 구간 시작 시간, 구간 종료 시간
            )
        """
        self.update_asset_info()

        asset_info_list = self.asset_info_list
        score_list = self.score_list
        info_list = self.info_list
        result_list = self.result_list
        spot_list = self.spot_list

        if index_info is not None:
            interval_data = self.__make_interval_data(index_info)
            asset_info_list = interval_data[0]
            score_list = interval_data[1]
            info_list = interval_data[2]
            result_list = interval_data[3]
            spot_list = interval_data[4]

        return self.__get_return_report(
            asset_info_list,
            score_list,
            info_list,
            result_list,
            graph_filename=graph_filename,
            spot_list=spot_list,
        )

    @staticmethod
    def make_rsi(prices, count=14):
        """
        compute the n period relative strength indicator
        http://stockcharts.com/school/doku.php?id=chart_school:glossary_r#relativestrengthindex
        http://www.investopedia.com/terms/r/rsi.asp
        """
        if len(prices) <= count:
            return None

        deltas = np.diff(prices)
        seed = deltas[:count]
        up_avg = seed[seed >= 0].sum() / count
        down_avg = -seed[seed < 0].sum() / count
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

            r_strength = up_avg / down_avg
            rsi[i] = 100.0 - 100.0 / (1.0 + r_strength)

        return rsi

    def __make_interval_data(self, index_info):
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
        start_dt = datetime.strptime(info_list[0]["date_time"], "%Y-%m-%dT%H:%M:%S")
        end_dt = datetime.strptime(info_list[-1]["date_time"], "%Y-%m-%dT%H:%M:%S")

        # w/a for short term query
        if start_dt == end_dt:
            end_dt = end_dt + timedelta(minutes=2)

        score_list = []
        asset_info_list = []
        result_list = []
        spot_list = []
        self.__make_filtered_list(start_dt, end_dt, score_list, self.score_list)
        self.__make_filtered_list(start_dt, end_dt, asset_info_list, self.asset_info_list)
        self.__make_filtered_list(start_dt, end_dt, result_list, self.result_list)
        self.__make_filtered_list(start_dt, end_dt, spot_list, self.spot_list)

        return (asset_info_list, score_list, info_list, result_list, spot_list)

    @staticmethod
    def _get_min_max_return(score_list):
        return_list = []
        for score in score_list:
            return_list.append(score["cumulative_return"])
        return (min(return_list), max(return_list))

    @staticmethod
    def __make_filtered_list(start_dt, end_dt, dest, source):
        for target in source:
            target_dt = datetime.strptime(target["date_time"], "%Y-%m-%dT%H:%M:%S")
            if start_dt <= target_dt <= end_dt:
                dest.append(target)

    def __get_return_report(
        self,
        asset_info_list,
        score_list,
        info_list,
        result_list,
        graph_filename=None,
        spot_list=None,
    ):
        try:
            graph = None
            start_value = Analyzer.__get_start_property_value(asset_info_list[0])
            last_value = Analyzer.__get_last_property_value(asset_info_list[-1])
            last_return = score_list[-1]["cumulative_return"]
            change_ratio = score_list[-1]["price_change_ratio"]
            min_max = self._get_min_max_return(score_list)
            if graph_filename is not None:
                graph = self.__draw_graph(
                    info_list,
                    result_list,
                    score_list,
                    graph_filename,
                    is_fullpath=True,
                    spot_list=spot_list,
                )
            period = info_list[0]["date_time"] + " - " + info_list[-1]["date_time"]
            summary = (
                start_value,
                last_value,
                last_return,
                change_ratio,
                graph,
                period,
                min_max[0],
                min_max[1],
                (
                    self.start_asset_info["date_time"],
                    info_list[0]["date_time"],
                    info_list[-1]["date_time"],
                ),
            )
            self.logger.info("### Return Report ===============================")
            self.logger.info(f"Property                 {start_value:10} -> {last_value:10}")
            self.logger.info(
                f"Gap                                    {last_value - start_value:10}"
            )
            self.logger.info(f"Cumulative return                    {last_return:10} %")
            self.logger.info(f"Price_change_ratio {change_ratio}")
            self.logger.info(f"Period {period}")
            return summary
        except (IndexError, AttributeError):
            self.logger.error("get return report FAIL")

    def get_trading_results(self):
        """거래 결과 목록을 반환한다"""
        return self.result_list

    def create_report(self, tag="untitled-report"):
        """수익률 보고서를 생성한다

        수익률 보고서를 생성하고, 그래프를 파일로 저장한다.
        tag: 생성할 리포트 파일명
        Returns:
            {
                "summary": (
                    start_budget: 시작 자산
                    final_balance: 최종 자산
                    cumulative_return : 시스템 시작 시점부터 누적 수익률
                    price_change_ratio: 시스템 시작 시점부터 보유 종목별 가격 변동률 딕셔너리
                    graph: 그래프 파일 패스
                    period: 수익률 산출 구간
                    return_high: 기간내 최고 수익률
                    return_low: 기간내 최저 수익률
                    date_info: 시스템 시작 시간, 구간 시작 시간, 구간 종료 시간
                ),
                "trading_table" : [
                    {
                        "date_time": 생성 시간, 정렬 기준 값
                        거래 정보, 매매 요청 및 결과 정보, 수익률 정보 딕셔너리
                    }
                ]
            }
        """

        try:
            summary = self.get_return_report()
            if summary is None:
                self.logger.error("invalid return report")
                return None

            list_sum = self.request_list + self.info_list + self.score_list + self.result_list
            trading_table = sorted(
                list_sum,
                key=lambda x: (
                    datetime.strptime(x["date_time"], self.ISO_DATEFORMAT),
                    x["kind"],
                ),
            )
            self.__create_report_file(tag, summary, trading_table)
            self.__draw_graph(
                self.info_list, self.result_list, self.score_list, tag, spot_list=self.spot_list
            )
            return {"summary": summary, "trading_table": trading_table}
        except (IndexError, AttributeError):
            self.logger.error("create report FAIL")

    def __create_report_file(self, filepath, summary, trading_table):
        """
        보고서를 정해진 형식에 맞게 파일로 출력한다

        ### TRADING TABLE =================================
        date_time, opening_price, high_price, low_price, closing_price, acc_price, acc_volume
        2020-02-23T00:00:00, 5000, 15000, 4500, 5500, 1500000000, 1500

        date_time, [->] id, type, price, amount
        2020-02-23T00:00:01, 1607862457.560075, sell, 1234567890, 1234567890

        date_time, [<-] request id, type, price, amount, msg
        2020-02-23T00:00:01, 1607862457.560075, sell, 1234567890, 1234567890, success, 1234567890

        date_time, [#] balance, cumulative_return, price_change_ratio, asset
        2020-02-23T00:00:01, 1234567890, 1234567890, 1234567890, 1234567890

        ### SUMMARY =======================================
        Property                 1234567890 -> 1234567890
        Gap                                    1234567890
        Cumulative return                    1234567890 %
        Price_change_ratio {'mango': -50.0, 'apple': 50.0}
        """
        final_path = self.OUTPUT_FOLDER + filepath + ".txt"
        with open(final_path, "w") as report_file:
            if len(trading_table) > 0:
                report_file.write("### TRADING TABLE =================================\n")

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
            report_file.write(f"Property                 {summary[0]:10} -> {summary[1]:10}\n")
            report_file.write(
                f"Gap                                    {summary[1] - summary[0]:10}\n"
            )
            report_file.write(f"Cumulative return                    {summary[2]:10} %\n")
            report_file.write(f"Price_change_ratio {summary[3]}\n")

            if self.DEBUG_MODE is True:
                rss = self._get_rss_memory()
                report_file.write("### DEBUG INFO ====================================\n")
                report_file.write(f"memory usage: {rss: 10.5f} MB\n")
                report_file.write(f"request_list: {len(self.request_list)}\n")
                report_file.write(f"result_list: {len(self.result_list)}\n")
                report_file.write(f"info_list: {len(self.info_list)}\n")
                report_file.write(f"asset_info_list: {len(self.asset_info_list)}\n")
                report_file.write(f"score_list: {len(self.score_list)}\n")

    @staticmethod
    def _get_rss_memory():
        process = psutil.Process()
        return process.memory_info().rss / 2 ** 20  # Bytes to MB

    def __get_spot_info(self, spot_list, start_pos, ref_time):
        spot_pos = start_pos
        spot_info = None
        while spot_pos < len(spot_list):
            spot = spot_list[spot_pos]
            spot_time = datetime.strptime(spot["date_time"], self.ISO_DATEFORMAT)
            if ref_time < spot_time:
                break
            spot_info = spot["value"]
            spot_pos += 1
        return spot_info, spot_pos

    def __create_plot_data(self, info_list, result_list, score_list, spot_list=None):
        result_pos = 0
        score_pos = 0
        spot_pos = 0
        last_avr_price = None
        last_acc_return = 0
        plot_data = []
        spots = None
        if spot_list is not None:
            spots = sorted(
                spot_list,
                key=lambda x: (datetime.strptime(x["date_time"], self.ISO_DATEFORMAT),),
            )

        # 그래프를 그리기 위해 매매, 수익률 정보를 트레이딩 정보와 합쳐서 하나의 테이블로 생성
        for info in info_list:
            new = info.copy()
            info_time = datetime.strptime(info["date_time"], self.ISO_DATEFORMAT)

            # 매매 정보를 생성해서 추가. 없는 경우 추가 안함. 기간내 매매별 하나씩만 추가됨
            while result_pos < len(result_list):
                result = result_list[result_pos]
                result_time = datetime.strptime(result["date_time"], self.ISO_DATEFORMAT)
                if info_time < result_time:
                    break

                if result["type"] == "buy":
                    new["buy"] = result["price"]
                elif result["type"] == "sell":
                    new["sell"] = result["price"]
                result_pos += 1

            # 추가 spot 정보를 생성해서 추가. 없는 경우 추가 안함. 기간내 하나만 추가됨
            if spots is not None:
                spot_info = self.__get_spot_info(spots, spot_pos, info_time)
                if spot_info[0] is not None:
                    new["spot"] = spot_info[0]
                spot_pos = spot_info[1]

            # 수익률 정보를 추가. 정보가 없는 경우 최근 정보로 채움
            while score_pos < len(score_list):
                score = score_list[score_pos]
                score_time = datetime.strptime(score["date_time"], self.ISO_DATEFORMAT)

                # keep last one only
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
        return pd.DataFrame(plot_data)[-self.GRAPH_MAX_COUNT :]

    def __draw_graph(
        self, info_list, result_list, score_list, filename, is_fullpath=False, spot_list=None
    ):
        total = self.__create_plot_data(info_list, result_list, score_list, spot_list=spot_list)
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

        if self.RSI is not None:
            rsi = self.make_rsi(total["Close"], count=self.RSI[2])
            if rsi is not None:
                rsi_low = np.full(len(rsi), self.RSI[0])
                rsi_high = np.full(len(rsi), self.RSI[1])
                apds.append(
                    mpf.make_addplot(rsi, panel=2, color="lime", ylim=(10, 90), secondary_y=False)
                )
                apds.append(
                    mpf.make_addplot(rsi_low, panel=2, color="red", width=0.5, secondary_y=False)
                )
                apds.append(
                    mpf.make_addplot(rsi_high, panel=2, color="red", width=0.5, secondary_y=False)
                )

        if "buy" in total.columns:
            apds.append(mpf.make_addplot(total["buy"], type="scatter", markersize=100, marker="^"))
        if "sell" in total.columns:
            apds.append(mpf.make_addplot(total["sell"], type="scatter", markersize=100, marker="v"))
        if "avr_price" in total.columns:
            apds.append(mpf.make_addplot(total["avr_price"]))
        if "return" in total.columns:
            apds.append(mpf.make_addplot((total["return"]), panel=1, color="g", secondary_y=True))
        if "spot" in total.columns:
            apds.append(
                mpf.make_addplot(
                    (total["spot"]), type="scatter", markersize=50, marker=".", color="g"
                )
            )

        destination = self.OUTPUT_FOLDER + filename + ".jpg"
        if is_fullpath:
            destination = filename

        mpf.plot(
            total,
            type="candle",
            volume=True,
            addplot=apds,
            mav=self.sma_info,
            style="starsandstripes",
            savefig=dict(fname=destination, dpi=300, pad_inches=0.25),
            figscale=1.25,
        )
        self.logger.info(f'"{destination}" graph file created!')
        return destination

    @staticmethod
    def __get_start_property_value(start_asset_info):
        return round(Analyzer.__get_property_total_value(start_asset_info))

    @staticmethod
    def __get_last_property_value(asset_info):
        return round(Analyzer.__get_property_total_value(asset_info))

    @staticmethod
    def __get_property_total_value(asset_info_list):
        total = float(asset_info_list["balance"])
        quote = asset_info_list["quote"]
        for name, item in asset_info_list["asset"].items():
            total += float(item[1]) * float(quote[name])
        return total

    @staticmethod
    def _write_to_file(filename, target_list):
        with open(filename, "w") as dump_file:
            dump_file.write("[\n")
            for item in target_list:
                dump_file.write(f"{item},\n")
            dump_file.write("]\n")

    @staticmethod
    def _load_list_from_file(filename):
        with open(filename) as dump_file:
            data = dump_file.read()
            target_list = ast.literal_eval(data)
            return target_list

    def dump(self, filename="dump"):
        """주요 데이터를 파일로 저장한다"""
        self._write_to_file(filename + ".1", self.request_list)
        self._write_to_file(filename + ".2", self.result_list)
        self._write_to_file(filename + ".3", self.info_list)
        self._write_to_file(filename + ".4", self.asset_info_list)
        self._write_to_file(filename + ".5", self.score_list)

    def load_dump(self, filename="dump"):
        """주요 데이터를 파일로부터 읽어온다"""
        self.request_list = self._load_list_from_file(filename + ".1")
        self.result_list = self._load_list_from_file(filename + ".2")
        self.info_list = self._load_list_from_file(filename + ".3")
        self.asset_info_list = self._load_list_from_file(filename + ".4")
        self.score_list = self._load_list_from_file(filename + ".5")
