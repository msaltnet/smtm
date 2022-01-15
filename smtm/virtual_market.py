"""업비트 거래소의 과거 거래 정보를 이용한 가상 거래소 역할의 VirtualMarket 클래스"""
from datetime import datetime, timedelta
from .data_repository import DataRepository
from .log_manager import LogManager


class VirtualMarket:
    """
    거래 요청 정보를 받아서 처리하여 가상의 거래 결과 정보를 생성한다

    end: 거래기간의 끝
    count: 거래기간까지 가져올 데이터의 갯수
    data: 사용될 거래 정보 목록
    turn_count: 현재까지 진행된 턴수
    balance: 잔고
    commission_ratio: 수수료율
    asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
    """

    URL = "https://api.upbit.com/v1/candles/minutes/1"

    def __init__(self, market="KRW-BTC"):
        self.logger = LogManager.get_logger(__class__.__name__)
        self.repo = DataRepository("smtm.db")
        self.data = None
        self.turn_count = 0
        self.balance = 0
        self.commission_ratio = 0.0005
        self.asset = {}
        self.is_initialized = False
        self.market = market

    def initialize(self, end=None, count=100, budget=0):
        """
        실제 거래소에서 거래 데이터를 가져와서 초기화한다

        end: 언제까지의 거래기간 정보를 사용할 것인지에 대한 날짜 시간 정보
        count: 거래기간까지 가져올 데이터의 갯수
        """
        end_dt = datetime.strptime(end, "%Y-%m-%dT%H:%M:%S")
        start_dt = end_dt - timedelta(minutes=count)
        start = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        self.data = self.repo.get_data(start, end, market=self.market)
        self.balance = budget
        self.is_initialized = True
        self.logger.debug(f"Virtual Market is initialized end: {end}, count: {count}")

    def get_balance(self):
        """
        현금을 포함한 모든 자산 정보를 제공한다

        returns:
        {
            balance: 계좌 현금 잔고
            asset: 자산 목록, 마켓이름을 키값으로 갖고 (평균 매입 가격, 수량)을 갖는 딕셔너리
            quote: 종목별 현재 가격 딕셔너리
            date_time: 기준 데이터 시간
        }
        """
        asset_info = {"balance": self.balance}
        quote = None
        try:
            quote = {
                self.data[self.turn_count]["market"]: self.data[self.turn_count]["closing_price"]
            }
            for name, item in self.asset.items():
                self.logger.debug(f"asset item: {name}, item price: {item[0]}, amount: {item[1]}")
        except (KeyError, IndexError) as msg:
            self.logger.error(f"invalid trading data {msg}")
            return None

        asset_info["asset"] = self.asset
        asset_info["quote"] = quote
        asset_info["date_time"] = self.data[self.turn_count]["date_time"]
        return asset_info

    def handle_request(self, request):
        """
        거래 요청을 처리해서 결과를 반환

        request: 거래 요청 정보
        Returns:
        result:
            {
                "request": 요청 정보
                "type": 거래 유형 sell, buy, cancel
                "price": 거래 가격
                "amount": 거래 수량
                "state": 거래 상태 requested, done
                "msg": 거래 결과 메세지
                "date_time": 시뮬레이션 모드에서는 데이터 시간
                "balance": 거래 후 계좌 현금 잔고
            }
        """
        if self.is_initialized is not True:
            self.logger.error("virtual market is NOT initialized")
            return None
        now = self.data[self.turn_count]["date_time"]
        self.turn_count += 1
        next_index = self.turn_count

        if next_index >= len(self.data) - 1:
            return {
                "request": request,
                "type": request["type"],
                "price": 0,
                "amount": 0,
                "balance": self.balance,
                "msg": "game-over",
                "date_time": now,
                "state": "done",
            }

        if request["price"] == 0 or request["amount"] == 0:
            self.logger.info("turn over")
            return None

        if request["type"] == "buy":
            result = self.__handle_buy_request(request, next_index, now)
        elif request["type"] == "sell":
            result = self.__handle_sell_request(request, next_index, now)
        else:
            self.logger.warning("invalid type request")
            result = "error!"
        return result

    def __handle_buy_request(self, request, next_index, dt):
        buy_value = request["price"] * request["amount"]
        buy_total_value = buy_value * (1 + self.commission_ratio)
        old_balance = self.balance

        if buy_total_value > self.balance:
            self.logger.info("no money")
            return "error!"

        try:
            if request["price"] < self.data[next_index]["low_price"]:
                self.logger.info("not matched")
                return "pass"

            name = self.data[next_index]["market"]
            if name in self.asset:
                asset = self.asset[name]
                new_amount = asset[1] + request["amount"]
                new_amount = round(new_amount, 6)
                new_value = (request["amount"] * request["price"]) + (asset[0] * asset[1])
                self.asset[name] = (round(new_value / new_amount), new_amount)
            else:
                self.asset[name] = (request["price"], request["amount"])

            self.balance -= buy_total_value
            self.balance = round(self.balance)
            self.__print_balance_info("buy", old_balance, self.balance, buy_value)
            return {
                "request": request,
                "type": request["type"],
                "price": request["price"],
                "amount": request["amount"],
                "msg": "success",
                "balance": self.balance,
                "state": "done",
                "date_time": dt,
            }
        except KeyError as msg:
            self.logger.warning(f"internal error {msg}")
            return "error!"

    def __handle_sell_request(self, request, next_index, dt):
        old_balance = self.balance
        try:
            name = self.data[next_index]["market"]
            if name not in self.asset:
                self.logger.info("asset empty")
                return "error!"

            if request["price"] >= self.data[next_index]["high_price"]:
                self.logger.info("not matched")
                return "pass"

            sell_amount = request["amount"]
            if request["amount"] > self.asset[name][1]:
                sell_amount = self.asset[name][1]
                self.logger.warning(
                    f"sell request is bigger than asset {request['amount']} > {sell_amount}"
                )
                del self.asset[name]
            else:
                new_amount = self.asset[name][1] - sell_amount
                new_amount = round(new_amount, 6)
                self.asset[name] = (
                    self.asset[name][0],
                    new_amount,
                )

            sell_value = sell_amount * request["price"]
            self.balance += sell_amount * request["price"] * (1 - self.commission_ratio)
            self.balance = round(self.balance)
            self.__print_balance_info("sell", old_balance, self.balance, sell_value)
            return {
                "request": request,
                "type": request["type"],
                "price": request["price"],
                "amount": sell_amount,
                "msg": "success",
                "balance": self.balance,
                "state": "done",
                "date_time": dt,
            }
        except KeyError as msg:
            self.logger.error(f"invalid trading data {msg}")
            return "error!"

    def __print_balance_info(self, trading_type, old, new, total_asset_value):
        self.logger.debug(f"[Balance] from {old}")
        if trading_type == "buy":
            self.logger.debug(f"[Balance] - {trading_type}_asset_value {total_asset_value}")
        elif trading_type == "sell":
            self.logger.debug(f"[Balance] + {trading_type}_asset_value {total_asset_value}")
        self.logger.debug(f"[Balance] - commission {total_asset_value * self.commission_ratio}")
        self.logger.debug(f"[Balance] to {new}")
