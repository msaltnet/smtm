"""가상 거래소"""
import json
from datetime import datetime, timedelta
from .log_manager import LogManager


class VirtualMarket:
    """
    거래 요청 정보를 받아서 처리하여 가상의 거래 결과 정보를 생성한다

    http: http client 모듈(requests)
    end: 거래기간의 끝
    count: 거래기간까지 가져올 데이터의 갯수
    data: 사용될 거래 정보 목록
    turn_count: 현재까지 진행된 턴수
    balance: 잔고
    commission_ratio: 수수료율
    asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
    """

    URL = "https://api.upbit.com/v1/candles/minutes/1"
    QUERY_STRING = {"market": "KRW-BTC", "count": "1"}
    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    def __init__(self):
        self.logger = LogManager.get_logger(__name__)
        self.is_initialized = False
        self.http = None
        self.end = "2020-04-30 00:00:00"
        self.count = 100
        self.data = None
        self.turn_count = 0
        self.balance = 0
        self.commission_ratio = 0.0005
        self.asset = {}

    def initialize(self, http, end, count):
        """
        실제 거래소에서 거래 데이터를 가져와서 초기화한다

        http: http client 인스턴스
        end: 언제까지의 거래기간 정보를 사용할 것인지에 대한 날짜 시간 정보
        count: 거래기간까지 가져올 데이터의 갯수
        """
        if self.is_initialized:
            return

        self.http = http
        if end is not None:
            self.end = end
        if count is not None:
            self.count = count
        self.__update_data_from_server()
        self.logger.debug(f"Virtual Market is initialized {end}, {count}")

    def initialize_from_file(self, filepath, end, count):
        """
        파일로부터 거래 데이터를 가져와서 초기화한다

        filepath: 거래 데이터 파일
        end: 거래기간의 끝
        count: 거래기간까지 가져올 데이터의 갯수
        """
        if self.is_initialized:
            return

        self.end = end
        self.count = count
        try:
            with open(filepath, "r") as data_file:
                self.data = json.loads(data_file.read())
                self.is_initialized = True
        except FileNotFoundError as msg:
            self.logger.error(msg)

    def __update_data_from_server(self):
        self.QUERY_STRING["to"] = self.end
        self.QUERY_STRING["count"] = self.count

        try:
            response = self.http.request("GET", self.URL, params=self.QUERY_STRING)
            response.raise_for_status()
            self.data = json.loads(response.text)
            self.data.reverse()
            self.is_initialized = True
        except AttributeError as msg:
            self.logger.error(msg)
            raise UserWarning("fail to get data from server")
        except ValueError:
            self.logger.error("Invalid data from server")
            raise UserWarning("fail to get data from server")
        except self.http.exceptions.HTTPError as err:
            self.logger.error(err)
            raise UserWarning("fail to get data from server")
        except self.http.exceptions.RequestException as err:
            self.logger.error(err)
            raise UserWarning("fail to get data from server")

    def deposit(self, balance):
        """자산 입출금을 할 수 있다"""
        self.balance += balance
        self.logger.info(f"Balance update {balance} to {self.balance}")

    def set_commission_ratio(self, ratio):
        """수수료 비율 설정한다"""
        self.commission_ratio = ratio / 100

    def get_balance(self):
        """
        현금을 포함한 모든 자산 정보를 제공한다

        balance: 계좌 현금 잔고
        asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
        quote: 종목별 현재 가격 딕셔너리
        """
        asset_info = {"balance": self.balance}
        quote = None
        try:
            quote = {
                self.data[self.turn_count]["market"]: self.data[self.turn_count]["opening_price"]
            }
            name = None
            self.logger.info(f"asset list length {len(self.asset)} =====================")
            for name, item in self.asset.items():
                self.logger.info(f"item: {name}, item price: {item[0]}, amount: {item[1]}")
        except (KeyError, IndexError) as msg:
            self.logger.error(f"invalid trading data {msg}")
            return None

        asset_info["asset"] = self.asset
        asset_info["quote"] = quote
        return asset_info

    def send_request(self, request):
        """
        거래 요청을 처리해서 결과를 반환

        request: 거래 요청 정보
        Returns:
            result:
            {
                "request": 요청 정보
                "type": 거래 유형 sell, buy
                "price": 거래 가격
                "amount": 거래 수량
                "msg": 거래 결과 메세지
                "balance": 거래 후 계좌 현금 잔고
                "date_time": 시뮬레이션 모드에서는 데이터 시간 +2초
            }
        """
        if self.is_initialized is not True:
            self.logger.warning("virtual market is NOT initialized")
            return None
        next_index = self.turn_count + 1
        self.turn_count = next_index
        result = None

        current_dt = datetime.strptime(
            self.data[self.turn_count]["candle_date_time_kst"], self.ISO_DATEFORMAT
        )
        now = current_dt.isoformat()

        if next_index >= len(self.data) - 1:
            return {
                "request": request,
                "type": request["type"],
                "price": -1,
                "amount": -1,
                "msg": "game-over",
                "balance": self.balance,
                "date_time": now,
            }

        if request["price"] == 0 or request["amount"] == 0:
            return {
                "request": request,
                "type": request["type"],
                "price": 0,
                "amount": 0,
                "msg": "turn over",
                "balance": self.balance,
                "date_time": now,
            }

        if request["type"] == "buy":
            result = self.__handle_buy_request(request, next_index)
            result["date_time"] = now
        elif request["type"] == "sell":
            result = self.__handle_sell_request(request, next_index)
            result["date_time"] = now
        else:
            result = {
                "request": request,
                "type": request["type"],
                "price": -1,
                "amount": -1,
                "msg": "invalid type",
                "balance": self.balance,
                "date_time": now,
            }
        return result

    def __handle_buy_request(self, request, next_index):
        buy_asset_value = request["price"] * request["amount"]
        old_balance = self.balance
        if buy_asset_value * (1 + self.commission_ratio) > self.balance:
            return {
                "request": request,
                "type": request["type"],
                "price": 0,
                "amount": 0,
                "msg": "no money",
                "balance": self.balance,
            }

        try:
            if request["price"] < self.data[next_index]["low_price"]:
                return {
                    "request": request,
                    "type": request["type"],
                    "price": 0,
                    "amount": 0,
                    "msg": "not matched",
                    "balance": self.balance,
                }
            name = self.data[next_index]["market"]
            if name in self.asset:
                old = self.asset[name]
                final_amount = old[1] + request["amount"]
                total_value = (request["amount"] * request["price"]) + (old[0] * old[1])
                self.asset[name] = (round(total_value / final_amount), final_amount)
            else:
                self.asset[name] = (request["price"], request["amount"])

            self.balance -= buy_asset_value * (1 + self.commission_ratio)
            self.balance = round(self.balance)
            self.__print_balance_info("buy", old_balance, self.balance, buy_asset_value)
            return {
                "request": request,
                "type": request["type"],
                "price": request["price"],
                "amount": request["amount"],
                "msg": "success",
                "balance": self.balance,
            }
        except KeyError as msg:
            self.logger.error(f"invalid trading data {msg}")
            return {
                "request": request,
                "type": request["type"],
                "price": -1,
                "amount": -1,
                "msg": "internal error",
                "balance": self.balance,
            }

    def __handle_sell_request(self, request, next_index):
        old_balance = self.balance
        try:
            name = self.data[next_index]["market"]
            if name not in self.asset:
                return {
                    "request": request,
                    "type": request["type"],
                    "price": 0,
                    "amount": 0,
                    "msg": "asset empty",
                    "balance": self.balance,
                }

            if request["price"] >= self.data[next_index]["high_price"]:
                return {
                    "request": request,
                    "type": request["type"],
                    "price": 0,
                    "amount": 0,
                    "msg": "not matched",
                    "balance": self.balance,
                }

            sell_amount = request["amount"]
            if request["amount"] > self.asset[name][1]:
                sell_amount = self.asset[name][1]
                self.logger.warning(
                    f"sell request is bigger than asset {request['amount']} > {sell_amount}"
                )
                del self.asset[name]
            else:
                self.asset[name] = (
                    self.asset[name][0],
                    self.asset[name][1] - sell_amount,
                )

            sell_asset_value = sell_amount * request["price"]
            self.balance += sell_amount * request["price"] * (1 - self.commission_ratio)
            self.balance = round(self.balance)
            self.__print_balance_info("sell", old_balance, self.balance, sell_asset_value)
            return {
                "request": request,
                "type": request["type"],
                "price": request["price"],
                "amount": sell_amount,
                "msg": "success",
                "balance": self.balance,
            }
        except KeyError as msg:
            self.logger.error(f"invalid trading data {msg}")
            return {
                "request": request,
                "type": request["type"],
                "price": -1,
                "amount": -1,
                "msg": "internal error",
                "balance": self.balance,
            }

    def __print_balance_info(self, trading_type, old, new, total_asset_value):
        self.logger.debug(f"[Balance] from {old}")
        if trading_type == "buy":
            self.logger.debug(f"[Balance] - {trading_type}_asset_value {total_asset_value}")
        elif trading_type == "sell":
            self.logger.debug(f"[Balance] + {trading_type}_asset_value {total_asset_value}")
        self.logger.debug(f"[Balance] - commission {total_asset_value * self.commission_ratio}")
        self.logger.debug(f"[Balance] to {new}")
