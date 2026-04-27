import threading
from collections import deque

class FifoSemaphore:
    def __init__(self, initial: int) -> None:
        if initial <= 0:
            raise ValueError("initial deve ser maior que zero")
        self._available = initial
        self._queue: deque[object] = deque()
        self._condition = threading.Condition()

    def down(self) -> None:
        ticket = object()
        with self._condition:
            self._queue.append(ticket)
            while self._queue[0] is not ticket or self._available == 0:
                self._condition.wait()
            self._queue.popleft()
            self._available -= 1
            self._condition.notify_all()

    def up(self) -> None:
        with self._condition:
            self._available += 1
            self._condition.notify_all()
