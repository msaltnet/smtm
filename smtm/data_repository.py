"""거래 데이터를 클라우드에서 가져오고, 저장해서 제공
현재는 업비트의 1분단위 거래 내역만 사용 가능
"""
import copy
from datetime import datetime, timedelta
import requests
from .log_manager import LogManager
from .date_converter import DateConverter
from .database import Database


class DataRepository:
    def __init__(self, db_file=None):
        self.logger = LogManager.get_logger(__class__.__name__)
        db = db_file if db_file is not None else "smtm.db"
        self.database = Database(db)
        self.verify_mode = False

    def get_data(self, start, end, market="KRW-BTC"):
        """거래 데이터를 제공
        데이터베이스에서 데이터 조회해서 결과를 반환하거나
        서버에서 데이터를 가져와서 반환
        """
        count_info = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=100000000)
        total_count = count_info[0][2]
        db_data = self._query(start, end, market)

        self.logger.info(f"total vs database: {total_count} vs {len(db_data)}")
        if total_count == len(db_data):
            self.logger.info(f"from database: {total_count}")
            self._convert_to_upbit_datetime_string(db_data)
            return db_data
        elif len(db_data) > total_count:
            raise UserWarning("Something wrong in DB")

        server_data = self._fetch_from_upbit(start, end, market)
        self._convert_to_upbit_datetime_string(server_data)
        return server_data

    @staticmethod
    def _convert_to_upbit_datetime_string(data_list):
        for data in data_list:
            data["date_time"] = data["date_time"].replace(" ", "T")

    @staticmethod
    def _convert_to_datetime(data_list):
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
        if len(db_data) != len(fetch_data):
            print(f"### _is_equal: False, size")
            return False

        for data in db_data:
            del data["period"]

        DataRepository._convert_to_upbit_datetime_string(db_data)
        print(f"### _is_equal: {db_data == fetch_data}")
        return db_data == fetch_data

    def _query(self, start, end, market):
        start_datetime = start.replace("T", " ")
        end_datetime = end.replace("T", " ")
        return self.database.query(start_datetime, end_datetime, market)

    def _update(self, data):
        self._convert_to_datetime(data)
        self.database.update(data)
        self.logger.info(f"update database: {len(data)}")

    def _fetch_from_upbit(self, start, end, market):
        """업비트 서버에서 n번 데이터 조회해서 최종 결과를 반환
        1회 조회시 갯수 제한이 있기 때문에 여러번 조회해서 합쳐야함
        업비트는 현재 공식적으로 최대 200개까지 조회 가능
        """
        total_data = []
        dt_list = DateConverter.to_end_min(start_iso=start, end_iso=end, max_count=200)
        for dt in dt_list:
            self.logger.info(f"fetch from {dt[0]} to {dt[1]}, count: {dt[2]}")
            query_data = self._query(dt[0], dt[1], market)
            if len(query_data) >= dt[2]:
                if self.verify_mode:
                    fetch_data = self._fetch_from_upbit_up_to_200(dt[1], dt[2], market)
                    recovered_data = self._recovery_upbit_data(fetch_data, dt[0], dt[2], market)
                    self._is_equal(query_data, recovered_data)
                else:
                    fetch_data = query_data
            else:
                fetch_data = self._fetch_from_upbit_up_to_200(dt[1], dt[2], market)
                fetch_data = self._recovery_upbit_data(fetch_data, dt[0], dt[2], market)
                self._update(fetch_data)

            total_data += fetch_data
        return total_data

    def _recovery_upbit_data(self, data, start, count, market, period=60):
        new_data = []
        current_dt = self._convert_to_dt(start)
        current_datetime = start
        last_item = None
        idx = 0
        broken_count = 0

        while len(new_data) < count:
            if len(data) <= idx:
                item_dt = self._convert_to_dt("2099-01-01T00:00:00")
            else:
                item_dt = self._convert_to_dt(data[idx]["date_time"])
            delta = current_dt - item_dt
            if delta.total_seconds() > 0:
                # drop
                last_item = copy.deepcopy(data[idx])
                idx += 1
                continue
            elif delta.total_seconds() == 0:
                # keep
                new_data.append(copy.deepcopy(data[idx]))
                last_item = copy.deepcopy(data[idx])
                idx += 1
            else:
                # recovery from last
                if last_item is None:
                    raise UserWarning("something wrong in recovery data")

                recovery_item = copy.deepcopy(last_item)
                recovery_item["date_time"] = current_datetime
                recovery_item["recovered"] = 1
                new_data.append(recovery_item)
                self._report_broken_block(current_datetime, market)
                broken_count += 1

            current_dt = current_dt + timedelta(seconds=period)
            current_datetime = self._convert_to_string(current_dt)
        if broken_count > 0:
            self.logger.info(f"Recovered broken data: {broken_count}")
        return new_data

    def _report_broken_block(self, datetime, market, period=60):
        self.logger.error(f"Broken data {datetime}, {market}, {period}")

    def _fetch_from_upbit_up_to_200(self, end, count, market):
        """업비트 서버에서 최대 200개까지 데이터 조회해서 반환
        1, 3, 5, 15, 10, 30, 60, 240분 가능
        https://docs.upbit.com/reference#%EC%8B%9C%EC%84%B8-%EC%BA%94%EB%93%A4-%EC%A1%B0%ED%9A%8C
        """

        URL = f"https://api.upbit.com/v1/candles/minutes/1"
        to = DateConverter.from_kst_to_utc_str(end) + "Z"
        query_string = {"market": market, "to": to, "count": count}
        self.logger.debug(f"query_string {query_string}")
        try:
            response = requests.get(URL, params=query_string)
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
            self.logger.error("Invalid data from server")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            self.logger.error(error)
            raise UserWarning("Fail get data from sever") from error
