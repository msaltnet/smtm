"""Datetime 포맷을 변경해주는 기능을 제공하는 DateConverter 클래스"""
import time
from datetime import datetime
from datetime import timedelta


class DateConverter:
    """날짜와 시간을 필요에 따라 변경해주는 클래스"""

    ISO_DATEFORMAT = "%Y-%m-%dT%H:%M:%S"

    @classmethod
    def to_end_min(
        cls,
        from_dash_to=None,
        start_dt=None,
        end_dt=None,
        start_iso=None,
        end_iso=None,
        max_count=9999999999,
    ):
        """숫자로 주어진 기간을 분으로 계산해서 시작, 끝, 분의 배열로 반환

        Returns:
            (
                start: %Y-%m-%dT%H:%M:%S 형태의 datetime 문자열
                end: %Y-%m-%dT%H:%M:%S 형태의 datetime 문자열
                count: 주어진 기간을 분으로 변환
            )
        to_end_min('200220-200320')
        to_end_min('200220.120015-200320')
        to_end_min('200220-200320.120015')
        to_end_min('200220.120015-200320.235510')
        """
        count = -1
        if from_dash_to is None and start_dt is not None and end_dt is not None:
            from_dt = start_dt
            to_dt = end_dt
        elif from_dash_to is None and start_iso is not None and end_iso is not None:
            from_dt = datetime.strptime(start_iso, cls.ISO_DATEFORMAT)
            to_dt = datetime.strptime(end_iso, cls.ISO_DATEFORMAT)
        else:
            from_to = from_dash_to.split("-")
            from_dt = cls.num_2_datetime(from_to[0])
            to_dt = cls.num_2_datetime(from_to[1])
        if to_dt <= from_dt:
            return None

        result_list = []
        delta = to_dt - from_dt
        while delta.total_seconds() > 0:
            count = round(delta.total_seconds() / 60.0)
            start_str = cls.to_iso_string(from_dt)
            if count <= max_count:
                from_dt = to_dt
                result = (start_str, cls.to_iso_string(to_dt), count)
            else:
                from_dt = from_dt + timedelta(minutes=max_count)
                result = (start_str, cls.to_iso_string(from_dt), max_count)

            delta = to_dt - from_dt
            result_list.append(result)

        return result_list

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
        if len(number_string) == 13:
            return datetime.strptime(number_string, "%y%m%d.%H%M%S")

        raise ValueError("unsupported number string")

    @classmethod
    def to_iso_string(cls, dt):
        """datetime 객체를 %Y-%m-%dT%H:%M:%S 형태의 문자열로 변환하여 반환"""
        return dt.strftime(cls.ISO_DATEFORMAT)

    @classmethod
    def from_kst_to_utc_str(cls, datetime_str):
        """%Y-%m-%dT%H:%M:%S 형태의 문자열에서 9시간 뺀 문자열 반환"""
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S")
        dt = dt - timedelta(hours=9)
        return dt.strftime(cls.ISO_DATEFORMAT)

    @classmethod
    def timestamp_id(cls):
        """unixtime(sec) + %M%S 형태의 문자열 반환"""
        time_prefix = round(time.time() * 1000)
        now = datetime.now()
        now_time = now.strftime("%H%M%S")
        return f"{time_prefix}.{now_time}"
