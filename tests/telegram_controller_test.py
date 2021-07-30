import unittest
from smtm import TelegramController
from unittest.mock import *


class TelegramControllerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_constructor(self):
        tc = TelegramController()
        self.assertIsNotNone(tc)
