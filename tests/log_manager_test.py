import logging.handlers
import unittest
from smtm import LogManager
from unittest.mock import *


class LogManagerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_logger_return_logger_with_handler(self):
        self.assertEqual("mango" in LogManager.logger_map, False)
        logger = LogManager.get_logger("mango")
        self.assertEqual("mango" in LogManager.logger_map, True)
        logger2 = LogManager.get_logger("mango")
        self.assertEqual(logger, logger2)

    def test_set_stream_level_call_stream_handler_setLevel(self):
        original = LogManager.stream_handler
        LogManager.stream_handler = MagicMock()
        LogManager.set_stream_level(50)
        LogManager.stream_handler.setLevel.assert_called_once_with(50)
        LogManager.stream_handler = original

    def test_change_log_file_should_change_file_handler(self):
        logger = LogManager.get_logger("orange")
        has_RotatingFileHandler = False
        old_handler = None
        for handler in logger.handlers:
            if issubclass(type(handler), logging.handlers.RotatingFileHandler):
                self.assertEqual(handler.baseFilename[-8:], "smtm.log")
                has_RotatingFileHandler = True
                old_handler = handler
        self.assertTrue(has_RotatingFileHandler)

        has_RotatingFileHandler = False
        LogManager.change_log_file("kiwi.log")
        for handler in logger.handlers:
            if issubclass(type(handler), logging.handlers.RotatingFileHandler):
                self.assertEqual(handler.baseFilename[-8:], "kiwi.log")
                has_RotatingFileHandler = True
                self.assertNotEqual(old_handler, handler)
                old_handler = handler
        self.assertTrue(has_RotatingFileHandler)

        has_RotatingFileHandler = False
        LogManager.change_log_file("kiwi.log")
        for handler in logger.handlers:
            if issubclass(type(handler), logging.handlers.RotatingFileHandler):
                self.assertEqual(handler.baseFilename[-8:], "kiwi.log")
                self.assertEqual(old_handler, handler)
                has_RotatingFileHandler = True
        self.assertTrue(has_RotatingFileHandler)
