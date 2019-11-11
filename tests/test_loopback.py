import unittest
from context import loopback

class TestLoopback(unittest.TestCase):
    def test_hi(self):
        instance = loopback.Loopback()
        result = instance.hi('banana?')
        self.assertEqual(result, 'Hello!: banana')
