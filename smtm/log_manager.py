"""file, stream handler를 공유하는 logger 인스턴스를 제공하는 LogManager 클래스"""
import os
import logging
from logging.handlers import RotatingFileHandler


class LogManager:
    """
    파일, 스트림 핸들러가 설정된 logger 인스턴스를 제공하는 클래스
    """

    LOG_FOLDER = "log"
    DEFAULT_FILE_NAME = "smtm.log"
    LOG_FILE = f"{LOG_FOLDER}/{DEFAULT_FILE_NAME}"
    LOG_FILE_SIZE = 2097152
    BACKUP_COUNT = 10
    CRITICAL = 50
    ERROR = 40
    WARNING = 30
    INFO = 20
    DEBUG = 10
    NOTSET = 0
    try:
        if not os.path.exists(LOG_FOLDER):
            os.makedirs(LOG_FOLDER)
    except OSError:
        print("Error: Creating directory. " + LOG_FOLDER)

    FORMATTER = logging.Formatter(
        fmt="%(asctime)s %(levelname)5.5s %(name)20.20s %(lineno)5d - %(message)s"
    )
    HANDLER = RotatingFileHandler(
        filename=LOG_FILE, maxBytes=LOG_FILE_SIZE, backupCount=BACKUP_COUNT
    )
    HANDLER.setLevel(logging.DEBUG)
    HANDLER.setFormatter(FORMATTER)
    STREAM_FORMATTER = logging.Formatter(
        fmt="%(asctime)s %(levelname)5.5s %(name)20.20s - %(message)s"
    )
    STREAM_HANDLER = logging.StreamHandler()
    STREAM_HANDLER.setLevel(logging.DEBUG)
    STREAM_HANDLER.setFormatter(STREAM_FORMATTER)
    REGISTERED_LOGGER = {}

    @classmethod
    def get_logger(cls, name):
        """파일, 스트림 핸들러가 설정된 logger 인스턴스를 제공한다"""
        logger = logging.getLogger(name)
        if name in cls.REGISTERED_LOGGER:
            return logger

        logger.addHandler(cls.STREAM_HANDLER)
        logger.addHandler(cls.HANDLER)
        logger.setLevel(logging.DEBUG)
        cls.REGISTERED_LOGGER[name] = logger
        return logger

    @classmethod
    def set_stream_level(cls, level):
        """스트림 핸들러의 레벨을 설정한다
        CRITICAL  50
        ERROR     40
        WARNING   30
        INFO      20
        DEBUG     10
        NOTSET    0
        """
        cls.STREAM_HANDLER.setLevel(level)

    @classmethod
    def change_log_file(cls, log_file=DEFAULT_FILE_NAME):
        """파일 핸들러의 로그 파일을 변경한다"""
        cls.LOG_FILE = f"{cls.LOG_FOLDER}/{log_file}"
        new_file_handler = RotatingFileHandler(
            filename=cls.LOG_FILE, maxBytes=cls.LOG_FILE_SIZE, backupCount=cls.BACKUP_COUNT
        )
        new_file_handler.setLevel(logging.DEBUG)
        new_file_handler.setFormatter(cls.FORMATTER)

        for logger in cls.REGISTERED_LOGGER.values():
            logger.removeHandler(cls.HANDLER)
            logger.addHandler(new_file_handler)
            cls.HANDLER.close()

        cls.HANDLER = new_file_handler
