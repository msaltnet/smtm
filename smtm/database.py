"""거래 데이터의 데이터베이스 역할의 Database 클래스"""
import sqlite3
from .log_manager import LogManager


class Database:
    """과거 거래 데이터의 데이터 베이스 클래스"""

    def __init__(self, db_file=None):
        db = db_file if db_file is not None else "smtm.db"
        self.logger = LogManager.get_logger(__class__.__name__)
        self.conn = sqlite3.connect(db, check_same_thread=False, timeout=30.0)

        def dict_factory(cursor, row):
            dictionay = {}
            for idx, col in enumerate(cursor.description):
                dictionay[col[0]] = row[idx]
            return dictionay

        self.conn.row_factory = dict_factory

        self.cursor = self.conn.cursor()
        self.create_table()

    def __del__(self):
        self.conn.close()

    def create_table(self):
        """테이블 생성
        id TEXT 고유 식별자 period(S)-date_time e.g. 60S-YYYY-MM-DD HH:MM:SS
        period INT 캔들의 기간(초), 분봉 - 60
        recoverd INT 복구된 데이터인지여부
        market TEXT 거래 시장 종류 BTC
        date_time DATETIME 정보의 기준 시간, 'YYYY-MM-DD HH:MM:SS' 형식의 sql datetime format
        opening_price FLOAT 시작 거래 가격
        high_price FLOAT 최고 거래 가격
        low_price FLOAT 최저 거래 가격
        closing_price FLOAT 마지막 거래 가격
        acc_price FLOAT 단위 시간내 누적 거래 금액
        acc_volume FLOAT 단위 시간내 누적 거래 양
        """
        self.cursor.execute(
            """CREATE TABLE IF NOT EXISTS upbit (id TEXT PRIMARY KEY, period INT, recovered INT, market TEXT, date_time DATETIME, opening_price FLOAT, high_price FLOAT, low_price FLOAT, closing_price FLOAT, acc_price FLOAT, acc_volume FLOAT)"""
        )
        self.conn.commit()

    def query(self, start, end, market, period=60):
        """데이터 조회"""

        self.cursor.execute(
            "SELECT period, recovered, market, date_time, opening_price, high_price, low_price, closing_price, acc_price, acc_volume FROM upbit WHERE market = ? AND period = ? AND date_time >= ? AND date_time < ? ORDER BY datetime(date_time) ASC",
            (market, period, start, end),
        )
        return self.cursor.fetchall()

    def update(self, data, period=60):
        """데이터베이스 데이터 추가 또는 업데이트"""
        tuple_list = []
        for item in data:
            recovered = item["recovered"] if "recovered" in item else 0
            tuple_list.append(
                (
                    f"{period}S-{item['date_time']}",
                    period,
                    recovered,
                    item["market"],
                    item["date_time"],
                    item["opening_price"],
                    item["high_price"],
                    item["low_price"],
                    item["closing_price"],
                    item["acc_price"],
                    item["acc_volume"],
                )
            )

        self.logger.info(f"Updated: {len(tuple_list)}")
        self.cursor.executemany(
            "REPLACE INTO upbit(id, period, recovered, market, date_time, opening_price, high_price, low_price, closing_price, acc_price, acc_volume) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            tuple_list,
        )
        self.conn.commit()
