# ThreadSnakeOS

A microkernel architecture simulator written in pure Python.

ThreadSnakeOS models the design of a microkernel operating system — capability-based IPC, a round-robin scheduler, and unprivileged user-space servers — using Python generators as task contexts. It ships with an interactive shell so you can poke at the running system from your terminal.

**This is not an operating system.** It does not boot, touch hardware, or write to your disk. It is a faithful simulation of microkernel *architecture*, built as a learning project. See [What this is and isn't](#what-this-is-and-isnt).

---

## Contents

- [Why](#why)
- [What this is and isn't](#what-this-is-and-isnt)
- [Quick start](#quick-start)
- [The shell](#the-shell)
- [Architecture](#architecture)
- [How it works](#how-it-works)
- [Project layout](#project-layout)
- [Running the demos](#running-the-demos)
- [Extending it](#extending-it)
- [Further reading](#further-reading)

---

## Why

In a monolithic kernel (Linux, classic Windows), the file system, network stack, and device drivers all run inside the kernel with full privileges. A bug in a graphics driver can corrupt the file system's data structures and take down the machine.

In a **microkernel**, the kernel keeps only what's impossible to do outside it — scheduling, IPC, and basic resource control. Everything else runs as an ordinary unprivileged **server**. If the file server crashes, you restart the file server; the kernel and every other server keep running.

ThreadSnakeOS exists to make that trade-off tangible. You can watch a single `read` cost five context switches, crash a server and watch the system survive, and see a task get `EPERM` for touching a capability it was never given.

---

## What this is and isn't

**What's architecturally real:**

- Cooperative scheduling with genuine context switching (paused generators as saved contexts)
- Blocking message-passing IPC with mailboxes, wake-on-delivery, and deadlock detection
- Capability-based security with per-task capability tables and kernel-mediated handle translation
- Fault isolation — a crashing server is terminated alone; the rest of the system continues
- Servers as unprivileged, independently schedulable tasks that communicate only through the kernel

**What's simulated, because Python can't do better:**

- No CPU privilege levels, MMU, page tables, or interrupts
- No real context switching — Python's generator machinery stands in for saving registers and stacks
- The file server is a Python `dict` in memory. `write /tmp/note hello` does **not** create `/tmp/note` on your disk, and nothing survives process exit
- Capabilities are unforgeable *by convention*: tasks only ever hold integer handles, and the kernel resolves them against per-task tables — but since all tasks share one address space, a determined task could construct a `Capability` object directly. In seL4 or KeyKOS this is physically impossible
- Single-threaded and cooperative: a task that loops without yielding hangs the whole system, exactly like Mac OS 9 or Windows 3.x

---

## Quick start

Requires Python 3.10+. No dependencies.

```bash
git clone https://github.com/bonejangles-hash/ThreadSnakeOS.git
cd ThreadSnakeOS
PYTHONPATH=. python3 main.py
```

You'll get:

```
[console] ThreadSnakeOS shell. commands: ls, read <path>, write <path> <text>, trace on/off, exit
tsos>
```

Try it:

```
tsos> ls
[console] ['/etc/motd']
tsos> read /etc/motd
[console] welcome to ThreadSnakeOS
tsos> write /tmp/note hello world
[console] {'status': 'OK'}
tsos> read /tmp/note
[console] hello world
tsos> exit
```

The `*** DEADLOCK ***` report printed after `exit` is **expected**, not an error. Once the shell terminates, the name server, console, and file server are still alive and blocked on `Receive()` waiting for messages that will never come. The kernel detects this and reports it by name instead of hanging silently.

---

## The shell

| Command | Description |
|---|---|
| `ls` | List all paths in the file server |
| `read <path>` | Read a file's contents. Missing files return `{'status': 'ENOENT'}` |
| `write <path> <text>` | Write text to a path. Everything after the path is one string, spaces included |
| `trace on` / `trace off` | Toggle the kernel's syscall trace log live |
| `exit` | Terminate the shell |

Anything else echoes back as `unknown command`.

### Watching the kernel work

`trace on` is the most instructive thing in the project. With it enabled, a single `read` shows every hop:

```
tsos> read /etc/motd
[kernel] init -> fs: {'op': 'READ', 'path': '/etc/motd'}
[kernel] fs unblocked
[kernel] init blocks on receive
[kernel] fs -> init: {'status': 'OK', 'data': 'welcome to ThreadSnakeOS\n'}
[kernel] init unblocked
[kernel] fs blocks on receive
[kernel] init -> console: {'op': 'WRITE', 'text': 'welcome to ThreadSnakeOS'}
[kernel] console unblocked
[kernel] init blocks on receive
[console] welcome to ThreadSnakeOS
[kernel] console -> init: {'status': 'OK', 'bytes': 24}
[kernel] init unblocked
[kernel] console blocks on receive
```

That's the microkernel tax, measured. A monolithic kernel does this with one function call.

Tracing defaults to off. To change the default, edit `boot(trace=False)` in `main.py`.

---

## Architecture

```
        ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐
 user   │  shell   │  │  name    │  │   file   │  │ console  │
 space  │  (init)  │  │  server  │  │  server  │  │  driver  │
        └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘
             │             │             │             │
   ══════════╪═════════════╪═════════════╪═════════════╪══════════
             │             │             │             │
        ┌────▼─────────────▼─────────────▼─────────────▼─────┐
 kernel │  syscall dispatch │ scheduler │ mailboxes │ caps    │
        └────────────────────────────────────────────────────┘
```

Nothing crosses horizontally. The shell cannot call a function in the file server — it can only send a message, and only if it holds a capability for that server's mailbox.

### Boot sequence

1. `main.py` creates the kernel and starts the **name server**
2. `init` is spawned holding exactly one capability — to the name server. This is the root of trust; every other capability in the system derives from it
3. `init` spawns the **console** and **file server**, then registers both with the name server
4. `init` hands control to the **shell**, which looks up `fs` and `console` by name and enters its command loop

---

## How it works

### Generators as task contexts

A paused generator keeps its instruction pointer and all local variables alive. That's a saved CPU context, without any assembly:

```python
def counter():
    n = 0
    while True:
        yield n      # pause here, resume here next time
        n += 1
```

The kernel holds one paused generator per task. "Context switching" is calling `.send()` on a different one.

### Syscalls as yielded objects

A task performs a syscall by yielding a dataclass instance. The kernel inspects it, acts, and resumes the task with a return value:

```python
def my_task():
    data = yield Receive()      # yields a syscall, resumes with a message
```

`yield Receive()` is this project's `int 0x80`. Real kernels use integer syscall numbers because they must cross a hardware boundary; objects work better here and let the kernel dispatch with `isinstance`.

Available syscalls: `Yield`, `Send`, `Receive`, `Spawn`, `Exit`, `GetInfo`, `SetTrace`.

### Capabilities

A capability is the right to act on a mailbox. Tasks never hold `Capability` objects — they hold **integer handles**, like Unix file descriptors, meaningless outside their own task's table:

```python
task A: Send(cap=3, body={...})
        ↓  kernel resolves A's handle 3 -> Capability object
        ↓  kernel checks Rights.SEND
        ↓  kernel installs it in B's cap_table -> new handle 7
task B: receives Message(caps={"reply": 7})
```

A new task starts with an **empty** capability table and can do nothing until someone grants it something. This is least authority enforced structurally, not by policy. The handle translation on send is the same mechanism Unix uses to pass file descriptors over a domain socket with `SCM_RIGHTS`.

### Blocking

Blocking is an *absence*, not a state machine. A task that calls `Receive` on an empty mailbox is simply not added back to the scheduler's ready queue. When a message arrives, `_wake_if_waiting` hands it over and requeues the task. There's no blocked queue to scan — the mailbox owner is found directly from the capability.

When the ready queue empties but blocked tasks remain, the kernel reports a deadlock with the name of every stuck task.

### Fault isolation

```python
try:
    request = task.step()
except StopIteration:
    self.terminate(task)              # returned normally
except Exception as exc:              # the task crashed
    self._log(f"FAULT in {task.name}: {exc!r}")
    self.terminate(task, status=-1)
```

Those four lines are the entire reason microkernels are more reliable than monolithic ones. A server that raises is killed alone; a stale capability to it then returns `EDEAD`, and a supervisor can spawn a replacement. See `demo4_crash_restart.py`.

---

## Project layout

```
ThreadSnakeOS/
├── main.py                     # boot()
├── tskernel/
│   ├── types.py                # Message, syscalls, enums
│   ├── mailbox.py              # FIFO message queue, one per task
│   ├── task.py                 # PCB: coroutine + cap table + mailbox
│   ├── caps.py                 # Capability, rights, restriction
│   ├── scheduler.py            # round-robin ready queue
│   ├── kernel.py               # main loop, syscall dispatch
│   └── lib.py                  # userspace syscall wrappers
├── servers/
│   ├── nameserver.py           # service registry
│   ├── console.py              # the only task allowed to print()
│   ├── fileserver.py           # in-memory filesystem
│   ├── shell.py                # interactive command loop
│   └── init.py                 # first user task
└── checkpoints/                # component tests and demos
```

**House rule:** no task except the console server may call `print()`. The kernel's `_log` is exempt — real kernels do have a privileged debug channel. Break this rule and the isolation model stops teaching you anything.

---

## Running the demos

```bash
cd ThreadSnakeOS

# Component checkpoints
PYTHONPATH=. python3 checkpoints/checkpoint1.py    # syscall/message dataclasses
PYTHONPATH=. python3 checkpoints/checkpoint2.py    # mailbox put/get
PYTHONPATH=. python3 checkpoints/checkpoint3.py    # task step() yields a syscall
PYTHONPATH=. python3 checkpoints/checkpoint4.py    # capabilities narrow, never widen

# Full-system demos
PYTHONPATH=. python3 checkpoints/demo1_pingpong.py                # blocking IPC round trips
PYTHONPATH=. python3 checkpoints/demo2_boot.py                    # name server + fs + console
PYTHONPATH=. python3 checkpoints/demo3_capability_enforcement.py  # EPERM on an unheld handle
PYTHONPATH=. python3 checkpoints/demo4_crash_restart.py           # crash, EDEAD, respawn
```

`demo4` is the payoff: the file server raises, gets terminated alone, a stale capability returns `EDEAD`, and a freshly spawned replacement serves the same file. On a monolithic kernel, that bug is a panic.

---

## Extending it

Roughly in order of value:

- **Preemption** — force a `Yield` after N steps, then discover why you now need locks
- **Synchronous rendezvous IPC** (seL4 style) alongside the async version; measure both
- **Timeouts** — `Receive(timeout=...)` plus a kernel tick counter
- **Real persistence** — swap the file server's `dict` for actual `open()`/`read()`/`write()` calls, which opens the door to crash consistency and write-ahead logging
- **Priority scheduling**, then deliberately starve a task and add aging to fix it
- **Shared memory** — a `Page` object transferred by capability
- **A `ps` server** — and think hard about which capability should gate kernel introspection
- **Sender blocking** on a full mailbox instead of returning `EFULL`
- **A trace viewer** — log every message to JSON and render a sequence diagram
- **Port to real processes** — replace generators with `multiprocessing`, mailboxes with Unix domain sockets, and capabilities with passed file descriptors. The design survives nearly unchanged, and then the isolation is real

### Questions worth answering as you build

1. Why must `Receive` block but `Send` need not? What breaks if both block?
2. The kernel is ~200 lines. What in it genuinely cannot be moved to a server?
3. If the name server crashes, can the system recover? What would it take?
4. A client sends a request and never receives the reply. Whose bug is it, and how would you detect it?
5. What in this simulation is architecturally real, and what is fake because Python can't do better?

---

## Further reading

- **MINIX 3** — a real, readable microkernel OS built for teaching. Tanenbaum's *Operating Systems: Design and Implementation* walks its source
- **seL4** — formally verified microkernel; its manual is the definitive modern treatment of capabilities and synchronous IPC
- **QNX** — commercial microkernel in cars and medical devices; proof the model works in production
- **David Beazley's coroutine course** — the source of the generator-based task/syscall trick used here
- **Operating Systems: Three Easy Pieces** — free online, the best general OS textbook

---

## License

MIT
