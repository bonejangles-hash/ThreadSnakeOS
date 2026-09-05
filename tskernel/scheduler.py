from collections import deque
from .types import TaskState


class RoundRobinScheduler:
    """Simplest fair policy: everyone takes turns."""

    def __init__(self):
        self.ready = deque()

    def add(self, task):
        task.state = TaskState.READY
        self.ready.append(task)

    def next_task(self):
        if not self.ready:
            return None
        task = self.ready.popleft()
        task.state = TaskState.RUNNING
        return task

    def remove(self, task):
        """Used when a task is killed while still queued."""
        try:
            self.ready.remove(task)
        except ValueError:
            pass

    def has_runnable(self):
        return len(self.ready) > 0
