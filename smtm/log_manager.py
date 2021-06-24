"""logger 인스턴스를 제공

이 모듈은 상황에 맞는 핸들러가 설정된 logger 인스턴스를 제공한다.
"""

import logging
from logging.handlers import RotatingFileHandler


class LogManager:
    """
    파일, 스트림 핸들러가 설정된 logger 인스턴스를 제공하는 클래스
    """

    file_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)5.5s %(name)20.20s %(lineno)5d - %(message)s"
    )
    file_handler = RotatingFileHandler(filename="smtm.log", maxBytes=1000000, backupCount=10)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)
    stream_formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)5.5s %(name)20.20s - %(message)s"
    )
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.DEBUG)
    stream_handler.setFormatter(stream_formatter)
    logger_map = {}

    @classmethod
    def get_logger(cls, name):
        """
        파일, 스트림 핸들러가 설정된 logger 인스턴스를 제공한다
        """
        logger = logging.getLogger(name)
        if name in cls.logger_map:
            return logger

        logger.addHandler(cls.stream_handler)
        logger.addHandler(cls.file_handler)
        logger.setLevel(logging.DEBUG)
        cls.logger_map[name] = True
        return logger

    @classmethod
    def set_stream_level(cls, level):
        """
        스트림 핸들러의 레벨을 설정한다
        """
        cls.stream_handler.setLevel(level)
