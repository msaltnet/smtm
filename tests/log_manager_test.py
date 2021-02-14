import unittest
from smtm import LogManager
from unittest.mock import *


class LogManagerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    @patch("logging.getLogger")
    def test_get_logger_return_logger_with_handler(self, mock_getLogger):
        class DummyLogger:
            pass

        dummyLogger = DummyLogger()
        dummyLogger.addHandler = MagicMock()
        dummyLogger.setLevel = MagicMock()
        mock_getLogger.return_value = dummyLogger
        self.assertEqual("mango" in LogManager.logger_map, False)
        logger = LogManager.get_logger("mango")
        calls = [call(LogManager.file_handler), call(LogManager.stream_handler)]
        dummyLogger.addHandler.has_calls(calls, any_order=True)
        dummyLogger.setLevel.assert_called_once_with(10)
        self.assertEqual("mango" in LogManager.logger_map, True)
        self.assertEqual(logger, dummyLogger)
