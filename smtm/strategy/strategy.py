from abc import ABCMeta, abstractmethod


class Strategy(metaclass=ABCMeta):
    """
    데이터를 받아서 매매 판단을 하고 결과를 받아서 다음 판단에 반영하는 전략 추상클래스

    Abstract class for strategies that receive data, make trading decisions, and reflect the results in the next decision
    """

    CODE = "---"
    NAME = "---"

    @abstractmethod
    def initialize(
        self,
        budget,
        min_price=100,
        add_spot_callback=None,
        add_line_callback=None,
        alert_callback=None,
    ):
        """예산을 설정하고 초기화한다

        budget: 예산
        min_price: 최소 거래 금액, 거래소의 최소 거래 금액
        add_spot_callback(date_time, value): 그래프에 그려질 spot을 추가하는 콜백 함수
        add_line_callback(date_time, value): 그래프에 그려질 line을 추가하는 콜백 함수
        alert_callback(msg): 알림을 전달하는 콜백 함수 e.g. Operator나 Controller에 전달
        """

    @abstractmethod
    def get_request(self):
        """
        전략에 따라 거래 요청 정보를 생성한다
        Generate trade request information based on your strategy

        Returns: 배열에 한 개 이상의 요청 정보를 전달
        [{
            "id": 요청 정보 id "1607862457.560075"
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "date_time": 요청 데이터 생성 시간, 시뮬레이션 모드에서는 데이터 시간
        }]
        """

    @abstractmethod
    def update_trading_info(self, info):
        """
        Data Provider에서 제공받은 새로운 거래 정보를 업데이트

        Update new trading information from data provider

        info:
        [
            {
                "type": 데이터 종류, 소스에 따라 다름, 기본 데이터는 'primary_candle'
                "market": 거래 시장 종류 BTC
                "date_time": 정보의 기준 시간
                "opening_price": 시작 거래 가격
                "high_price": 최고 거래 가격
                "low_price": 최저 거래 가격
                "closing_price": 마지막 거래 가격
                "acc_price": 단위 시간내 누적 거래 금액
                "acc_volume": 단위 시간내 누적 거래 양
            }
        ]
        """

    @abstractmethod
    def update_result(self, result):
        """
        요청한 거래의 결과를 업데이트

        Update the results of a requested trading

        request: 거래 요청 정보
        result:
        {
            "request": 요청 정보
            "type": 거래 유형 sell, buy, cancel
            "price": 거래 가격
            "amount": 거래 수량
            "state": 거래 상태 requested, done
            "msg": 거래 결과 메세지
            "date_time": 거래 체결 시간, 시뮬레이션 모드에서는 데이터 시간 +2초
        }
        """
