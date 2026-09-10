from .types import (TaskState, Rights, Message, Yield, Send, Receive, Spawn, Exit, GetInfo, SetTrace)
from .task import Task
from .caps import Capability
from .scheduler import RoundRobinScheduler


class Kernel:
    def __init__(self, scheduler=None, trace=False):
        self.tasks = {}
        self.blocked = set()
        self.scheduler = scheduler or RoundRobinScheduler()
        self.next_tid = 1
        self.trace = trace
        self.stats = {"switches": 0, "messages": 0}

    # ---- task lifecycle ----

    def create_task(self, coroutine, name='anon'):
        task = Task(self.next_tid, coroutine, name)
        self.next_tid += 1
        self.tasks[task.tid] = task
        self.scheduler.add(task)
        self._log(f"created {task}")
        return task

    def full_cap(self, task):
        """An all-rights capability to 'task''s mailbox (kernel-side object)"""
        return Capability(
            mailbox=task.mailbox,
            rights=frozenset({Rights.SEND, Rights.GRANT, Rights.KILL}),
            label=task.name,
        )

    def terminate(self, task, status=0):
        task.state = TaskState.ZOMBIE
        task.exit_status = status
        self.scheduler.remove(task)
        self.blocked.discard(task.tid)
        del self.tasks[task.tid]
        self._log(f"terminated {task.name} (status={status})")

    # ---- main loop ----
    def run(self, max_steps=100_000):
        for _ in range(max_steps):
            if not self.scheduler.has_runnable():
                if self.blocked:
                    self._report_deadlock()
                return "deadlock" if self.blocked else "done"

            task = self.scheduler.next_task()
            self.stats["switches"] += 1

            try:
                request = task.step()
            except StopIteration:
                self.terminate(task)        # returned normally
                continue
            except Exception as exc:        # the task crashed
                self._log(f"FAULT in {task.name}: {exc!r}")
                self.terminate(task, status=-1)
                continue

            self.dispatch(task, request)
        return "step limit reached"

    # ---- syscall dispatch ----
    def dispatch(self, task, request):
        if isinstance(request, Yield) or request is None:
            self.scheduler.add(task)
        elif isinstance(request, Send):
            self.sys_send(task, request)
        elif isinstance(request, Receive):
            self.sys_receive(task)
        elif isinstance(request, Spawn):
            self.sys_spawn(task, request)
        elif isinstance(request, Exit):
            self.terminate(task, request.status)
        elif isinstance(request, GetInfo):
            task.set_return((task.tid, task.name))
            self.scheduler.add(task)
        elif isinstance(request, SetTrace):
            self.trace = request.enabled
            task.set_return(self.trace)
            self.scheduler.add(task)
        else:
            task.set_return(("EBADCALL", repr(request)))
            self.scheduler.add(task)

    def sys_send(self, task, req):
        cap = task.resolve(req.cap)
        if cap is None or not cap.has(Rights.SEND):
            task.set_return("EPERM")
            self.scheduler.add(task)
            return

        target_tid = cap.mailbox.owner_tid
        target = self.tasks.get(target_tid)
        if target is None:
            task.set_return("EDEAD")
            self.scheduler.add(task)
            return

        # ---- translate capability handles from sender's table to receiver's ----
        transferred = {}
        for name, handle in req.caps.items():
            src = task.resolve(handle)
            if src is None or not src.has(Rights.GRANT):
                continue        # silently drop; or fail
            transferred[name] = target.install_cap(src)

        if req.reply:
            reply_cap = Capability(task.mailbox,
                                   frozenset({Rights.SEND}),
                                   f"reply->{task.name}")
            transferred["reply"] = target.install_cap(reply_cap)
        message = Message(sender=task.tid, body=req.body, caps=transferred)
        try:
            cap.mailbox.put(message)
        except Exception as exc:
            task.set_return(f"EFULL:{exc}")
            self.scheduler.add(task)
            return

        self.stats["messages"] += 1
        self._log(f"{task.name} -> {target.name}: {req.body}")

        task.set_return("OK")
        self.scheduler.add(task)        # sender keeps running
        self._wake_if_waiting(target)

    def sys_receive(self, task):
        if task.mailbox.is_empty():
            task.state = TaskState.BLOCKED
            self.blocked.add(task.tid)
            self._log(f"{task.name} blocks on receive")
        else:
            task.set_return(task.mailbox.get())
            self.scheduler.add(task)

    def sys_spawn(self, task, req):
        child = self.create_task(req.coroutine, req.name)
        handle = task.install_cap(self.full_cap(child))
        task.set_return(handle)
        self.scheduler.add(task)

    def _wake_if_waiting(self, target):
        if target.tid in self.blocked:
            self.blocked.discard(target.tid)
            target.set_return(target.mailbox.get())
            self.scheduler.add(target)
            self._log(f"{target.name} unblocked")

    # ---- diagnostics ----
    def _report_deadlock(self):
        print("\n*** DEADLOCK ***")
        for tid in sorted(self.blocked):
            t = self.tasks[tid]
            print(f" {t.name} (tid {tid} waiting for a message that "
                  f"will never arrive")

    def _log(self, text):
        if self.trace:
            print(f"[kernel] {text}")
