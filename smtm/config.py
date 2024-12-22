import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """
    시스템 전역 설정 모듈
    System global settings
    """

    # 시뮬레이션에 사용할 거래소 데이터 simulation_source: upbit, binance
    simulation_source = "upbit"
    # SimulationDualDataProvider의 데이터를 사용할지 여부: normal, dual
    simulation_data_provider_type = "normal"
    candle_interval = 60
    """
    스트림 핸들러의 레벨 levels of stream handlers
    CRITICAL  50
    ERROR     40
    WARNING   30
    INFO      20
    DEBUG     10
    NOTSET    0
    """
    operation_log_level = 30
    language = os.environ.get("SMTM_LANG", "ko")
