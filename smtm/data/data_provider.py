from abc import ABCMeta, abstractmethod


class DataProvider(metaclass=ABCMeta):
    """
    거래에 관련된 데이터를 수집해서 정해진 데이터 포맷에 맞게 정보를 제공하는 DataProvider 추상클래스
    """

    @abstractmethod
    def get_info(self):
        """
        거래 정보·환율·지수·뉴스 등 다양한 정보 딕셔너리들을 리스트로 전달.
        주거래 정보는 'primary_candle' 타입으로 전달.
        그 외 딕셔너리는 'type' 값으로 소비자가 구분하며, 키 집합은 type에 따라 다름.
        수치형(캔들·환율·지수)과 텍스트형(뉴스·공지·요약)을 한 리스트에 혼합해도 된다.

        Passes a list of typed dictionaries representing trade data, exchange rates,
        indices, news, or any other information relevant to the LLM.
        The primary trading source is always emitted as type='primary_candle'.
        The key set varies by 'type'. Numeric (candle/rate/index) and text (news/notice)
        entries may be mixed in one list.

        Returns 예시:
        [
            {
                "type": "primary_candle",      # 주거래 캔들 (필수 스키마)
                "market": "BTC",
                "date_time": "...",
                "opening_price": ...,
                "high_price": ...,
                "low_price": ...,
                "closing_price": ...,
                "acc_price": ...,
                "acc_volume": ...,
            },
            {
                "type": "binance",             # 보조 거래소 캔들
                "market": "BTC-USDT",
                "date_time": "...",
                "opening_price": ..., ...
            },
            {
                "type": "exchange_rate",       # 환율
                "date_time": "...",
                "usd_krw": 1350.0
            },
            {
                "type": "news",                # 텍스트형 — 뉴스 한 건
                "date_time": "...",
                "source": "coindesk",
                "title": "...",
                "summary": "...",
                "url": "..."
            },
            {
                "type": "notice",              # 텍스트형 — 거래소 공지 등
                "date_time": "...",
                "source": "upbit",
                "title": "...",
                "body": "..."
            }
        ]
        """
