from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any


class TaskState(Enum):
    READY = auto()      # runnable, in ready queue
    RUNNING = auto()    # executing
    BLOCKED = auto()    # waiting for message
    ZOMBIE = auto()     # task finished, needs cleanup


class Rights(Enum):
    SEND = auto()       # may send messages to this mailbox
    GRANT = auto()      # may pass this capability to another task
    KILL = auto()       # may kill the owning task


@dataclass
class Message:
    """One IPC message, 'caps' maps a name -> capability handle (int)"""
    sender: int                                 # TID of sender
    body: dict                                  # payload; servers define
    caps: dict = field(default_factory=dict)    # capabilities transferred


# ------------SYSTEM CALLS-------------- #
# Task performs syscall by yielding one of these objects.
# Kernel inspects it, acts, and returns the task with a return value.

class SysCall:
    """Base class. The kernel dispatches on type."""


@dataclass
class Yield(SysCall):
    """Give up the CPU voluntarily; stay runnable."""


@dataclass
class Send(SysCall):
    """Deliver 'body' to the mailbox named by capability handle 'cap."""
    cap: int
    body: dict
    caps: dict = field(default_factory=dict)   # capability handles to transfer
    reply: bool = False


@dataclass
class Receive(SysCall):
    """Take the next message from my mailbox; block if empty."""


@dataclass
class Spawn(SysCall):
    """Create a new task from a coroutine. Returns a capability to do it."""
    coroutine: Any
    name: str = "anon"


@dataclass
class Exit(SysCall):
    """Terminate the calling task."""
    status: int = 0


@dataclass
class GetInfo(SysCall):
    """Debugging aid: returns (tid, name)"""


@dataclass
class SetTrace(SysCall):
    """Toggle the kernel's debug trace log on/off. Returns the new state."""
    enabled: bool
