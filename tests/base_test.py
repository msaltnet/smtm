import unittest
from unittest.mock import *
from smtm import Base

class BaseTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_say_hello_return_hello_world(self):
        base = Base()
        self.assertEqual(base.say_hello(), 'hello world!')