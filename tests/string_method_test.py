import unittest

class TestStringMethods(unittest.TestCase):

    def test_upper(self):
        foo = "Foo"
        self.assertEqual(foo.upper(), 'FOO')

    def test_isupper(self):
        foo = "Foo"
        capital_foo = "FOO"
        self.assertTrue(capital_foo.isupper())
        self.assertFalse(foo.isupper())

    def this_is_not_test_method(self):
        self.assertTrue(False)
