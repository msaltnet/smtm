"""Datetime 포맷을 변경해주는 기능을 제공"""
from datetime import datetime


class DateConverter:
    @classmethod
    def to_end_min(cls, from_dash_to):
        """숫자로 주어진 기간을 분으로 계산해서 마지막 날짜와 분을 반환

        Returns:
            (
                datetime: %Y-%m-%dT%H:%M:%S 형태의 datetime 문자열
                count: 주어진 기간을 분으로 변환
            )
        to_end_min('200220-200320')
        to_end_min('200220.120015-200320')
        to_end_min('200220-200320.120015')
        to_end_min('200220.120015-200320.235510')
        """
        count = -1
        ft = from_dash_to.split("-")
        from_dt = cls.num_2_datetime(ft[0])
        to_dt = cls.num_2_datetime(ft[1])
        if to_dt <= from_dt:
            return
        delta = to_dt - from_dt
        count = round(delta.total_seconds() / 60.0)
        return (cls.to_iso_string(to_dt), count)

    @classmethod
    def num_2_datetime(cls, number_string):
        """숫자로 주어진 시간을 datetime 객체로 변환해서 반환

        두가지 형태를 지원. yymmdd and yymmdd.HHMMSS
        num_2_datetime(200220)
        num_2_datetime(200220.213015)
        """
        number_string = str(number_string)
        if len(number_string) == 6:
            return datetime.strptime(number_string, "%y%m%d")
        elif len(number_string) == 13:
            return datetime.strptime(number_string, "%y%m%d.%H%M%S")
        else:
            raise ValueError("unsupported number string")

    @classmethod
    def to_iso_string(cls, datetime):
        """datetime 객체를 %Y-%m-%dT%H:%M:%S 형태의 문자열로 변환하여 반환"""
        ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"
        return datetime.strftime(ISO_DATEFORMAT)
