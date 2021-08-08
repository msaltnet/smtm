"""거래 데이터를 클라우드에서 가져오고, 저장해서 제공
현재는 업비트의 1분단위 거래 내역만 사용 가능
"""
from datetime import datetime
import requests
from .log_manager import LogManager
from .date_converter import DateConverter
from .database import Database


class DataRepository:
    UPBIT_FORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.database = Database()

    def get_data(self, start, end, market="BTC"):
        """거래 데이터를 제공
        데이터베이스에서 데이터 조회해서 결과를 반환하거나
        서버에서 데이터를 가져와서 반환
        """
        start_dt = datetime.strptime(start, self.UPBIT_FORMAT)
        end_dt = datetime.strptime(end, self.UPBIT_FORMAT)
        count_info = DateConverter.to_end_min(
            start_dt=start_dt, end_dt=end_dt, max_count=10000000000
        )
        total_count = count_info[0][2]
        start_datetime = start.replace("T", " ")
        end_datetime = end.replace("T", " ")
        db_data = self.database.query(start_datetime, end_datetime, market)

        self.logger.info(f"total vs database: {total_count} vs {len(db_data)}")
        if total_count == len(db_data):
            self.logger.info(f"from database: {total_count}")
            return self._convert_to_upbit_datetime_string(db_data)
        elif len(db_data) > total_count:
            self.logger.error("Something wrong in DB")

        server_data = self._fetch_from_upbit(start, end, market)
        self._convert_to_datetime(server_data)
        self.database.update(server_data)
        self.logger.info(f"update database: {len(server_data)}")
        return server_data

    def _convert_to_upbit_datetime_string(self, data_list):
        for data in data_list:
            data["date_time"] = data["date_time"].replace(" ", "T")

    def _convert_to_datetime(self, data_list):
        for data in data_list:
            data["date_time"] = data["date_time"].replace("T", " ")

    def _fetch_from_upbit(self, start, end, market):
        """업비트 서버에서 n번 데이터 조회해서 최종 결과를 반환
        1회 조회시 갯수 제한이 있기 때문에 여러번 조회해서 합쳐야함
        업비트는 현재 공식적으로 최대 200개까지 조회 가능
        """
        total_data = []
        start_dt = datetime.strptime(start, self.UPBIT_FORMAT)
        end_dt = datetime.strptime(end, self.UPBIT_FORMAT)
        dt_list = DateConverter.to_end_min(start_dt=start_dt, end_dt=end_dt, max_count=200)
        for dt in dt_list:
            total_data += self._fetch_from_upbit_up_to_200(dt[1], dt[2], market)
        return total_data

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
