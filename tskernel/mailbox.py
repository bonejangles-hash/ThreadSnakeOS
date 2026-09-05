from collections import deque


class Mailbox:
    """A FIFO message queue owned by one task."""

    def __init__(self, owner_tid, capacity=64):
        self.owner_tid = owner_tid
        self.capacity = capacity
        self._queue = deque()

    def is_empty(self):
        return len(self._queue) == 0

    def is_full(self):
        return len(self._queue) >= self.capacity

    def put(self, message):
        if self.is_full():
            raise MailboxFull(f"mailbox of task {self.owner_tid} is full")
        self._queue.append(message)

    def get(self):
        return self._queue.popleft()    # caller must check is_empty first

    def __len__(self):
        return len(self._queue)


class MailboxFull(Exception):
    pass
