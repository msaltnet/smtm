import logging
from logging.handlers import RotatingFileHandler

class LogManager():
    """
    파일, 스트림 핸들러가 설정된 logger 인스턴스를 제공하는 클래스
    """

    file_formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s - %(name)s:%(lineno)05d - %(message)s")
    file_handler = RotatingFileHandler(filename="smtm.log", maxBytes=1000000, backupCount=10)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    stream_formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s - %(name)s - %(message)s")
    logger_map = {}

    @classmethod
    def get_logger(cls, name):
        """
        파일, 스트림 핸들러가 설정된 logger 인스턴스를 제공한다
        """
        logger = logging.getLogger(name)
        if name in cls.logger_map:
            return logger

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(cls.stream_formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(cls.file_handler)
        logger.setLevel(logging.DEBUG)
        cls.logger_map[name] = True
        return logger
