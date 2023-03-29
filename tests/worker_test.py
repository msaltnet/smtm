import unittest
from smtm import Worker
from unittest.mock import *


class WorkerTests(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_post_task_put_task_correctly(self):
        worker = Worker("robot")
        worker.task_queue = MagicMock()
        worker.post_task("mango")
        worker.task_queue.put.assert_called_once_with("mango")

    @patch("threading.Thread")
    def test_start_make_new_thread_and_start_thread_when_thread_is_none(self, mock_thread):
        worker = Worker("robot")
        mock_return_thread = MagicMock()
        mock_thread.return_value = mock_return_thread
        worker.start()
        mock_thread.assert_called_once_with(target=ANY, name="robot", daemon=True)
        mock_return_thread.start.assert_called_once()

    @patch("threading.Thread")
    def test_start_have_correct_looper(self, mock_thread):
        worker = Worker("robot")
        mock_runnable = MagicMock()
        mock_task = {"runnable": mock_runnable}
        worker.on_terminated = MagicMock()
        worker.task_queue.put(mock_task)
        worker.task_queue.put(None)
        worker.start()
        looper = mock_thread.call_args_list[0][1]["target"]
        looper()
        mock_runnable.assert_called_once_with(mock_task)
        worker.on_terminated.assert_called_once()

    @patch("threading.Thread")
    def test_stop_put_None(self, mock_thread):
        worker = Worker("robot")
        worker.task_queue = MagicMock()
        worker.stop()
        self.assertEqual(worker.thread, None)
        worker.task_queue.put.assert_not_called()
        worker.thread = "orange"
        worker.stop()
        self.assertEqual(worker.thread, None)
        worker.task_queue.put.assert_called_once_with(None)

    def test_register_on_terminated_keep_callback_correctly(self):
        worker = Worker("robot")
        worker.register_on_terminated("mango")
        self.assertEqual(worker.on_terminated, "mango")
