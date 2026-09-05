from tskernel.caps import Capability
from tskernel.types import Rights
from tskernel.mailbox import Mailbox

mb = Mailbox(owner_tid=1)
full = Capability(mb, frozenset({Rights.SEND, Rights.GRANT}))
weak = full.restrict({Rights.SEND})

assert weak.has(Rights.SEND)
assert not weak.has(Rights.GRANT)

widened = weak.restrict({Rights.SEND, Rights.GRANT, Rights.KILL})
assert not widened.has(Rights.GRANT)
assert not widened.has(Rights.KILL)

print("checkpoint4: OK — restrict can only narrow, never widen")
