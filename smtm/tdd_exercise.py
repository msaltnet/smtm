"""TDD 연습용 모듈"""

import json
import requests
import copy


class TddExercise:
    URL = "https://api.upbit.com/v1/candles/minutes/1"
    QUERY_STRING = {"market": "KRW-BTC"}

    def __init__(self):
        self.data = []
        self.to = None
        self.count = 100

    def set_period(self, to, count):
        self.to = to
        self.count = count

    def initialize_from_server(self):
        """Open Api를 사용해서 데이터를 가져와서 초기화한다"""
        query_string = {"market": "KRW-BTC", "to": self.to, "count": self.count}

        response = requests.get(self.URL, params=query_string)
        self.data = response.json()
        # print(self.data)
        # print(self.data[0])
