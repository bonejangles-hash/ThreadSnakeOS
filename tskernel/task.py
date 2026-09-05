from .types import TaskState
from .mailbox import Mailbox


class Task:
    def __init__(self, tid, coroutine, name='anon'):
        self.tid = tid
        self.name = name
        self.coroutine = coroutine       # the paused generator = saved context
        self.state = TaskState.READY
        self.mailbox = Mailbox(owner_tid=tid)

        self.cap_table = {}             # handle (int) -> capability
        self.next_handle = 0            # next free slot, like a file desc
        self._sendval = None            # value to inject on next resume
        self.exit_status = None
        self.steps = 0                  # how many times we've run: for stats

# ---- context switch ---- #
    def step(self):
        """Resume this task until its next yield. Returns the yielded syscall."""
        value, self._sendval = self._sendval, None      # consume then clear
        self.steps += 1
        return self.coroutine.send(value)

    def set_return(self, value):
        """Set the value the task's pending 'yield' will evaluate to."""
        self._sendval = value

# ---- capability table ---- #
    def install_cap(self, capability):
        handle = self.next_handle
        self.next_handle += 1
        self.cap_table[handle] = capability
        return handle

    def resolve(self, handle):
        return self.cap_table.get(handle)  # none if the task doesn't hold it

    def __repr__(self):
        return f"<Task {self.tid} {self.name} {self.state.name}>"
