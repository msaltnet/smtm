"""TDD 연습용 모듈"""

import json
import requests
import copy

class TddExercise():
    URL = "https://api.upbit.com/v1/candles/minutes/1"
    QUERY_STRING = {"market": "KRW-BTC"}

    def __init__(self):
        self.is_initialized = False
        self.data = []
        self.index = 0
        self.end = None
        self.count = 100

    def set_period(self, end, count):
        self.end = end
        self.count = count

    def initialize_from_server(self, end=None, count=100):
        """Open Api를 사용해서 데이터를 가져와서 초기화한다"""
        query_string = {"market": "KRW-BTC"}

        if end is not None:
            query_string["to"] = end

        query_string["count"] = count

        try:
            response = requests.get(self.URL, params=query_string)
            response.raise_for_status()
            self.data = response.json()
            self.data.reverse()
            self.is_initialized = True
            print(f"data is updated from server # end: {end}, count: {count}")
        except ValueError as error:
            print("Invalid data from server")
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.HTTPError as error:
            print(error)
            raise UserWarning("Fail get data from sever") from error
        except requests.exceptions.RequestException as error:
            print(error)
            raise UserWarning("Fail get data from sever") from error
