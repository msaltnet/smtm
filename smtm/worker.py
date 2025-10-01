import queue
import threading
import traceback
from typing import Dict, Any, Callable, Optional
from .log_manager import LogManager


class Worker:
    """
    입력받은 task를 별도의 thread에서 차례대로 수행하는 일꾼
    Workers that take input tasks and perform them in turn in separate threads

    task가 추가되면 차례대로 task를 수행하며, task가 모두 수행되면 새로운 task가 추가 될때까지 대기한다.
    task는 dictionary이며 runnable에는 실행 가능한 객체를 담고 있어야 하며, runnable의 인자로 task를 넘겨준다.

    As tasks are added, it executes them one after the other,
    and when all tasks have been executed, it waits for a new task to be added.
    task is a dictionary and runnable must contain an executable object,
    passing task as an argument to runnable.
    """

    def __init__(self, name: str) -> None:
        self.task_queue = queue.Queue()
        self.thread = None
        self.name = name
        self.logger = LogManager.get_logger(name)
        self.on_terminated = None

    def register_on_terminated(self, callback: Optional[Callable[[], None]]) -> None:
        """
        종료될 때 실행될 콜백 등록
        Register a callback to run on exit
        """
        self.on_terminated = callback

    def post_task(self, task: Dict[str, Any]) -> None:
        """
        task를 추가한다
        Add task into task_queue

        task: dictionary이며 runnable에는 실행 가능한 객체를 담고 있어야 하며, runnable의 인자로 task를 넘겨준다.
        """
        self.task_queue.put(task)

    def start(self):
        """
        작업을 수행할 스레드를 만들고 start한다.
        Create a thread to perform the operation and start it.

        이미 작업이 진행되고 있는 경우 아무런 일도 일어나지 않는다.
        If worker is already started, nothing happens.
        """

        if self.thread is not None:
            return

        def looper():
            while True:
                self.logger.debug(
                    f"Worker[{self.name}:{threading.get_ident()}] WAIT =========="
                )
                task = self.task_queue.get()
                self.task_queue.task_done()
                if task is None:
                    self.logger.debug(
                        f"Worker[{self.name}:{threading.get_ident()}] Termanited .........."
                    )
                    if self.on_terminated is not None:
                        self.on_terminated()
                    break
                self.logger.debug(
                    f"Worker[{self.name}:{threading.get_ident()}] GO ----------"
                )
                runnable = task["runnable"]
                try:
                    runnable(task)
                except Exception as err:
                    self.logger.error(traceback.format_exc())
                    self.thread = None
                    raise UserWarning("Worker catched exception. force stop!") from err

        self.thread = threading.Thread(target=looper, name=self.name, daemon=True)
        self.thread.start()

    def stop(self):
        """
        현재 진행 중인 작업을 끝으로 스레드를 종료하도록 한다.
        End the thread by finishing the current task in progress.
        """
        if self.thread is None:
            return

        self.task_queue.put(None)
        self.thread = None
        self.task_queue.join()
