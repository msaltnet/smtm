import copy
import time
from datetime import datetime, timedelta, timezone
import requests
from ..log_manager import LogManager
from ..date_converter import DateConverter
from .database import Database


class DataRepository:
    """
    거래 데이터를 클라우드에서 가져오고, 저장해서 제공하는 DataRepository 클래스
    Config에서 업비트와 바이낸스 데이터를 선택할 수 있음

    DataRepository class to fetch, store, and serve transaction data from the exchange service
    Allows you to select Ubit and Binance data in Config
    """

    def __init__(self, db_file=None, interval=60, source="upbit", database=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        target_db_file = db_file if db_file is not None else "smtm.db"
        if database is not None:
            self.database = database
        else:
            self.database = Database(target_db_file)
        self.interval = interval
        self.interval_min = interval // 60
        self.is_upbit = True
        if source == "upbit":
            if interval == 60:
                self.url = "https://api.upbit.com/v1/candles/minutes/1"
            elif interval == 180:
                self.url = "https://api.upbit.com/v1/candles/minutes/3"
            elif interval == 300:
                self.url = "https://api.upbit.com/v1/candles/minutes/5"
            elif interval == 600:
                self.url = "https://api.upbit.com/v1/candles/minutes/10"
            else:
                raise UserWarning(f"not supported interval: {interval}")
        elif source == "binance":
            self.url = "https://api.binance.com/api/v3/klines"
            self.is_upbit = False
            if self.interval_min not in [1, 3, 5, 15, 30]:
                raise UserWarning(f"not supported interval: {interval}")
        else:
            raise UserWarning(f"not supported simulation data: {source}")

    def get_data(self, start, end, market="KRW-BTC"):
        """
        거래 데이터를 제공
        데이터베이스에서 데이터 조회해서 결과를 반환하거나
        데이터베이스에 데이터가 없을 경우 서버에서 데이터를 가져와서 반환
        서버에서 가져온 데이터는 데이터베이스에 업데이트

        Provide transaction data
        Retrieve data from the database and return the result
        If there is no data in the database, fetch the data from the server and return it
        Update the database with the data fetched from the server
        """
        self.logger.info(f"get data from repo: {start} to {end}, {market}")
        target_start = DateConverter.floor_min(start, self.interval_min)
        target_end = DateConverter.floor_min(end, self.interval_min)
        count_info = DateConverter.to_end_min(
            start_iso=target_start, end_iso=target_end, interval_min=self.interval_min
        )
        total_count = count_info[0][2]
        db_data = self._query(target_start, target_end, market)

        self.logger.info(f"total vs database: {total_count} vs {len(db_data)}")
        if len(db_data) > total_count:
            raise UserWarning("Something wrong in DB")

        if total_count == len(db_data):
            self.logger.info(f"from database: {total_count}")
            self._convert_to_iso_datetime_string(db_data)
            return db_data

        server_data = self._fetch_from_server(target_start, target_end, market)
        self._convert_to_iso_datetime_string(server_data)
        return server_data

    @staticmethod
    def _convert_to_iso_datetime_string(data_list):
        for data in data_list:
            data["date_time"] = data["date_time"].replace(" ", "T")

    @staticmethod
    def _convert_to_sqlite_datetime_string(data_list):
        for data in data_list:
            data["date_time"] = data["date_time"].replace("T", " ")

    @staticmethod
    def _convert_to_dt(string):
        return datetime.strptime(string, "%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def _convert_to_string(dt):
        return dt.strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def _is_equal(db_data, fetch_data):
        target_db_data = copy.deepcopy(db_data)
        target_fetch_data = copy.deepcopy(fetch_data)
        if len(target_db_data) != len(target_fetch_data):
            return False

        for data in target_db_data:
            del data["period"]
            del data["recovered"]

        for data in target_fetch_data:
            if "recovered" in data:
                del data["recovered"]

        DataRepository._convert_to_iso_datetime_string(target_db_data)
        return target_db_data == target_fetch_data

    def _query(self, start, end, market):
        start_datetime = start.replace("T", " ")
        end_datetime = end.replace("T", " ")
        return self.database.query(
            start_datetime,
            end_datetime,
            market,
            period=self.interval,
            is_upbit=self.is_upbit,
        )

    def _update(self, data):
        self._convert_to_sqlite_datetime_string(data)
        self.database.update(data, period=self.interval, is_upbit=self.is_upbit)
        self.logger.info("update database: %d", len(data))

    def _fetch_from_server(self, start, end, market):
        if self.is_upbit is True:
            return self._fetch_from_upbit(start, end, market)

        return self._fetch_from_binance(start, end, market)

    def _fetch_from_binance(self, start, end, market):
        """
        바이낸스 서버에서 n번 데이터 조회해서 최종 결과를 반환
        1회 조회시 갯수 제한이 있기 때문에 여러번 조회해서 합쳐야함
        바이낸스는 현재 공식적으로 최대 1000개까지 조회 가능

        Fetch n data from the Binance server and return the final result
        Since there is a limit on the number of queries per query, you need to query multiple times and combine them
        Binance currently officially supports up to 1000 queries
        """
        total_data = []
        dt_list = DateConverter.to_end_min(
            start_iso=start, end_iso=end, max_count=1000, interval_min=self.interval_min
        )
        for dt in dt_list:
            self.logger.info(f"query from {dt[0]} to {dt[1]}, count: {dt[2]}")
            query_data = self._query(dt[0], dt[1], market)
            if len(query_data) >= dt[2]:
                fetch_data = query_data
            else:
                self.logger.info("fetch from binance")
                fetch_data = self._fetch_from_binance_up_to_1000(
                    dt[0], dt[1], dt[2], market
                )
                if len(fetch_data) != dt[2]:
                    fetch_data = self._recovery_binance_head_broken_data(
                        fetch_data, dt[0], dt[1], market
                    )
                fetch_data = self._recovery_broken_data(
                    fetch_data, dt[0], dt[2], market
                )
                if len(fetch_data) != dt[2]:
                    raise UserWarning(
                        f"something wrong in binance data {len(fetch_data)} vs {dt[2]}"
                    )
                self._update(fetch_data)

            total_data += fetch_data
        return total_data

    def _recovery_binance_head_broken_data(self, fetch_data, start, end, market):
        """
        바이낸스 데이터의 앞부분이 깨진 경우
        1000개를 더 가져와서 시작부분까지 역으로 복사해서 채워준다
        업비트에서는 발생하지 않는 문제

        If the front of the Binance data is broken
        Fetch 1000 more and copy it backwards to fill up to the start
        Not a problem with Upbit
        """
        new_data = []
        broken_count = 0

        # 데이터가 하나도 없는 경우 앞부분 데이터를 채워줄 1000개 데이터를 추가로 가져옴
        if len(fetch_data) == 0:
            new_start = self._convert_to_string(
                self._convert_to_dt(start) + timedelta(seconds=self.interval * 1000)
            )
            new_end = self._convert_to_string(
                self._convert_to_dt(end) + timedelta(seconds=self.interval * 1000)
            )
            recovery_data = self._fetch_from_binance_up_to_1000(
                new_start, new_end, 1000, market
            )
            if len(recovery_data) == 0:
                raise UserWarning(f"critical error in binance data recovery process")
            new_data.append(copy.deepcopy(recovery_data[0]))
        else:
            new_data.append(copy.deepcopy(fetch_data[0]))

        # 시작부분까지 데이터를 복사해서 채워줌
        while True:
            current_dt = self._convert_to_dt(new_data[0]["date_time"])
            start_dt = self._convert_to_dt(start)
            delta = current_dt - start_dt
            if delta.total_seconds() > 0:
                recovery_item = copy.deepcopy(new_data[0])
                current_dt = current_dt - timedelta(seconds=self.interval)
                current_datetime = self._convert_to_string(current_dt)
                recovery_item["date_time"] = current_datetime
                recovery_item["recovered"] = 1
                new_data.insert(0, recovery_item)
                self._report_broken_block(current_datetime, market)
                broken_count += 1
            else:
                break

        if broken_count > 0:
            self.logger.info(f"Recovered broken head data: {broken_count}")

        return new_data + fetch_data

    @staticmethod
    def _get_kst_time_from_unix_time_ms(unix_time_ms):
        """
        밀리세컨드 단위의 유닉스 시간을 한국 시간으로 변환해서 반환한다
        Convert milliseconds unit Unix time to Korean time and return it
        """
        return DateConverter.to_iso_string(
            datetime.fromtimestamp(unix_time_ms / 1000, tz=timezone(timedelta(hours=9)))
        )

    def _fetch_from_binance_up_to_1000(self, start, end, count, market):
        """
        바이낸스 서버에서 최대 1000개까지 데이터 조회해서 반환
        바이낸스의 경우 throttling이 대해 관대함

        Fetch up to 1000 data from the Binance server and return it
        Binance is generous about throttling
        https://www.binance.com/en/support/faq/frequently-asked-questions-on-api-360004492232
        """
        start_ms = self._convert_to_dt(start).timestamp() * 1000
        end_ms = self._convert_to_dt(end).timestamp() * 1000
        query_string = {
            "symbol": market,
            "startTime": int(start_ms),
            "endTime": int(end_ms),
            "limit": count,
            "interval": f"{self.interval_min}m",
        }
        self.logger.debug(f"query_string {query_string}")
        try:
            response = requests.get(self.url, params=query_string)
            response.raise_for_status()
            data = response.json()
            final_data = []
            for item in data:
                final_data.append(
                    {
                        "market": market,
                        "date_time": self._get_kst_time_from_unix_time_ms(item[0]),
                        "opening_price": float(item[1]),
                        "high_price": float(item[2]),
                        "low_price": float(item[3]),
                        "closing_price": float(item[4]),
                        "acc_price": float(item[7]),
                        "acc_volume": float(item[5]),
                    }
                )
            return final_data

        except ValueError as error:
            self.logger.error(f"Invalid data from server: {error}")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning(f"{error}") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error

    def _fetch_from_upbit(self, start, end, market):
        """
        업비트 서버에서 n번 데이터 조회해서 최종 결과를 반환
        1회 조회시 갯수 제한이 있기 때문에 여러번 조회해서 합쳐야함
        업비트는 현재 공식적으로 최대 200개까지 조회 가능

        Fetch n data from the Upbit server and return the final result
        Since there is a limit on the number of queries per query, you need to query multiple times and combine them
        Upbit currently officially supports up to 200 queries
        """
        total_data = []
        dt_list = DateConverter.to_end_min(
            start_iso=start, end_iso=end, max_count=200, interval_min=self.interval_min
        )
        for dt in dt_list:
            self.logger.info(f"query from {dt[0]} to {dt[1]}, count: {dt[2]}")
            query_data = self._query(dt[0], dt[1], market)
            if len(query_data) >= dt[2]:
                fetch_data = query_data
            else:
                self.logger.info("fetch from upbit")
                fetch_data = self._fetch_from_upbit_up_to_200(dt[1], dt[2], market)
                fetch_data = self._recovery_broken_data(
                    fetch_data, dt[0], dt[2], market
                )
                self._update(fetch_data)

            total_data += fetch_data
        return total_data

    def _recovery_broken_data(self, data, start, count, market):
        """
        서버에서 가져온 데이터가 중간에 거래 데이터가 없는 경우 바로 앞의 데이터를 복사해서 채워준다

        If the data fetched from the server does not have transaction data in the middle, copy the previous data and fill it
        """
        new_data = []
        current_dt = self._convert_to_dt(start)
        current_datetime = start
        last_item = None
        idx = 0
        broken_count = 0
        while len(new_data) < count:
            if len(data) <= idx:
                # 주어진 데이터에 유효한 데이터가 부족한 경우 마지막 데이터로 채울 수 있게 조정
                item_dt = self._convert_to_dt("2099-01-01T00:00:00")
            else:
                item_dt = self._convert_to_dt(data[idx]["date_time"])
            delta = current_dt - item_dt

            if delta.total_seconds() > 0:
                # 기준보다 과거의 데이터 저장, 첫 데이터가 깨진 경우 사용
                self.logger.debug(f"pass data: {idx}")
                last_item = copy.deepcopy(data[idx])
                idx += 1
                continue

            if delta.total_seconds() == 0:
                # 일치하는 데이터 복사
                new_data.append(copy.deepcopy(data[idx]))
                last_item = copy.deepcopy(data[idx])
                idx += 1
            else:
                # 일치할때까지 저장된 과거의 데이터로 채움
                if last_item is None:
                    raise UserWarning("something wrong in recovery data")

                recovery_item = copy.deepcopy(last_item)
                recovery_item["date_time"] = current_datetime
                recovery_item["recovered"] = 1
                new_data.append(recovery_item)
                self._report_broken_block(current_datetime, market)
                broken_count += 1

            current_dt = current_dt + timedelta(seconds=self.interval)
            current_datetime = self._convert_to_string(current_dt)
        if broken_count > 0:
            self.logger.info(f"Recovered broken data: {broken_count}")
        return new_data

    def _report_broken_block(self, dt, market):
        self.logger.error(f"Broken data {dt}, {market}, {self.interval}")

    def _fetch_from_upbit_up_to_200(self, end, count, market):
        result = None
        while result is None:
            try:
                result = self._fetch_from_upbit_up_to_200_impl(end, count, market)
            except UserWarning as msg:
                if str(msg).find("429 Client Error: Too Many Requests") == 0:
                    self.logger.warning("Try again for Upbit throttling")
                    time.sleep(0.5)
                else:
                    self.logger.warning(msg)
                    raise UserWarning("Fail get data from sever") from msg

        return result

    def _fetch_from_upbit_up_to_200_impl(self, end, count, market):
        """
        업비트 서버에서 최대 200개까지 데이터 조회해서 반환
        1, 3, 5, 15, 10, 30, 60, 240분 가능

        Fetch up to 200 data from the Upbit server and return it
        1, 3, 5, 15, 10, 30, 60, 240 minutes possible

        https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
        """

        to_datetime = DateConverter.from_kst_to_utc_str(end) + "Z"
        query_string = {"market": market, "to": to_datetime, "count": count}
        self.logger.debug(f"query_string {query_string}")
        try:
            response = requests.get(self.url, params=query_string)
            response.raise_for_status()
            data = response.json()
            data.reverse()
            final_data = []
            for item in data:
                final_data.append(
                    {
                        "market": item["market"],
                        "date_time": item["candle_date_time_kst"],
                        "opening_price": float(item["opening_price"]),
                        "high_price": float(item["high_price"]),
                        "low_price": float(item["low_price"]),
                        "closing_price": float(item["trade_price"]),
                        "acc_price": float(item["candle_acc_trade_price"]),
                        "acc_volume": float(item["candle_acc_trade_volume"]),
                    }
                )
            return final_data

        except ValueError as error:
            self.logger.error(f"Invalid data from server: {error}")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning(f"{error}") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
