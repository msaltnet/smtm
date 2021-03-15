"""업비트 거래소를 통한 거래 처리"""

import os
import jwt  # PyJWT
import uuid
import hashlib
from urllib.parse import urlencode
import requests
from dotenv import load_dotenv

load_dotenv()

from .log_manager import LogManager
from .trader import Trader


class UpbitTrader(Trader):
    """
    거래 요청 정보를 받아서 거래소에 요청하고 거래소에서 받은 결과를 제공해주는 클래스

    id: 요청 정보 id "1607862457.560075"
    type: 거래 유형 sell, buy
    price: 거래 가격
    amount: 거래 수량
    """

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.ACCESS_KEY = os.environ["UPBIT_OPEN_API_ACCESS_KEY"]
        self.SECRET_KEY = os.environ["UPBIT_OPEN_API_SECRET_KEY"]
        self.SERVER_URL = os.environ["UPBIT_OPEN_API_SERVER_URL"]

    def send_request(self, request, callback):
        """거래 요청을 처리한다"""
        pass

    def send_account_info_request(self, callback):
        """계좌 요청 정보를 요청한다"""
        pass
