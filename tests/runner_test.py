import unittest
from simulator import Runner, RunnerStatus, RunnerOrderType, RunnerItem

class RunnerTests(unittest.TestCase):

    def setUp(self):
        self.dummyRecordList = [{"banana": "1"}, {"apple": "2"}]
        pass

    def tearDown(self):
        pass

    def test_start(self):
        runner = Runner()
        self.assertEqual(runner.getStatus(), RunnerStatus.NOT_STARTED)

        runner.start(self.dummyRecordList)
        self.assertEqual(runner.getStatus(), RunnerStatus.RUNNING)
        self.assertEqual(runner.getCurrentIndex(), 0)
        self.assertEqual(runner.getCurrentRecord(), {"banana": "1"})

    def test_next(self):
        runner = Runner()
        runner.start(self.dummyRecordList)
        self.assertEqual(runner.getCurrentIndex(), 0)
        runner.next()
        self.assertEqual(runner.getCurrentIndex(), 1)

    def test_order(self):
        runner = Runner()
        runner.start(self.dummyRecordList)
        self.assertEqual(runner.getCurrentIndex(), 0)
        item = RunnerItem(RunnerOrderType.BUY, 500, 100)
        print(type(item) is RunnerItem)
