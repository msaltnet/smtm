import unittest
from smtm import Record

class RecordTests(unittest.TestCase):

    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_importFromFile(self):
        record = Record(1, 2)
        record.importFromFile('test_record.json')
        recordList = record.getList()
        self.assertEqual(len(recordList), 100)
        self.assertEqual(len(recordList[0]), 11)
        self.assertEqual(recordList[0]['market'], 'KRW-BTC')
