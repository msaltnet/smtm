https://api.upbit.com/v1/candles/minutes/1?market=KRW-BTC&count=100

{
    "market":"KRW-BTC",
    "candle_date_time_utc":"2020-02-25T06:41:00",
    "candle_date_time_kst":"2020-02-25T15:41:00",
    "opening_price":11436000.00000000,
    "high_price":11443000.00000000,
    "low_price":11428000.00000000,
    "trade_price":11443000.00000000,
    "timestamp":1582612901489,
    "candle_acc_trade_price":17001839.06758000,
    "candle_acc_trade_volume":1.48642105,
    "unit":1
}

market
마켓명
String

candle_date_time_utc
캔들 기준 시각(UTC 기준)
String

candle_date_time_kst
캔들 기준 시각(KST 기준)
String

opening_price
시가
Double

high_price
고가
Double

low_price
저가
Double

trade_price
종가
Double

timestamp
해당 캔들에서 마지막 틱이 저장된 시각
Long

candle_acc_trade_price
누적 거래 금액
Double

candle_acc_trade_volume
누적 거래량
Double

unit
분 단위(유닛)
Integer