import logging
from logging.handlers import RotatingFileHandler

class LogManager():
    file_formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s - %(name)s:%(lineno)05d - %(message)s")
    file_handler = RotatingFileHandler(filename="smtm.log", maxBytes=1000000, backupCount=10)
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(file_formatter)
    stream_formatter = logging.Formatter(fmt="%(asctime)s %(levelname)s - %(name)s - %(message)s")

    @classmethod
    def get_logger(cls, name):
        logger = logging.getLogger(name)

        stream_handler = logging.StreamHandler()
        stream_handler.setLevel(logging.DEBUG)
        stream_handler.setFormatter(cls.stream_formatter)

        logger.addHandler(stream_handler)
        logger.addHandler(cls.file_handler)
        logger.setLevel(logging.DEBUG)
        return logger
