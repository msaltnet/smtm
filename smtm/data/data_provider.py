from abc import ABCMeta, abstractmethod


class DataProvider(metaclass=ABCMeta):
    """
    거래에 관련된 데이터를 수집해서 정해진 데이터 포맷에 맞게 정보를 제공하는 DataProvider 추상클래스
    """

    @abstractmethod
    def get_info(self):
        """
        거래 정보나 환율, 지수등의 다양한 정보 딕셔너리들을 리스트로 전달
        주거래 정보는 'primary_candle' 타입으로 전달.
        이외 정보 딕셔너리의 키 값은 type에 따라 다름.

        Passing trade information or various information dictionaries such as exchange rates, indices, etc. as lists
        The primary trade information is passed as a 'primary_candle' type.
        Key values for other information dictionaries depend on the type.

        Returns: 거래 정보 딕셔너리
        [
            {
                "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
                "market": 거래 시장 종류 BTC
                "date_time": 정보의 기준 시간
                "opening_price": 시작 거래 가격
                "high_price": 최고 거래 가격
                "low_price": 최저 거래 가격
                "closing_price": 마지막 거래 가격
                "acc_price": 단위 시간내 누적 거래 금액
                "acc_volume": 단위 시간내 누적 거래 양
            },
            {
                "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
                "usd_krw": 환율
                "date_time": 정보의 기준 시간
            },
            {
                "type": 데이터의 종류 e.g. 데이터 출처, 종류에 따른 구분으로 소비자가 데이터를 구분할 수 있게 함
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
