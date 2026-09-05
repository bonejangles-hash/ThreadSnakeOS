from dataclasses import dataclass
from typing import FrozenSet
from .types import Rights
from .mailbox import Mailbox


@dataclass(frozen=True)
class Capability:
    """A right to act on a mailbox. Frozen: rights cannot be widened after issue"""
    mailbox: Mailbox
    rights: FrozenSet[Rights]
    label: str = ""         # for debugging/tracing only

    def has(self, right):
        return right in self.rights

    def restrict(self, rights):
        """Derive a weaker capability. You can narrow rights, never widen them."""
        return Capability(self.mailbox, frozenset(rights) & self.rights, self.label)
