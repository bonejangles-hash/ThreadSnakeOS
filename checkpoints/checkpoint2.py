from tskernel.mailbox import Mailbox

box = Mailbox(owner_tid=1)
box.put("hello")
assert box.get() == "hello"
assert box.is_empty()

try:
    box.get()
    print("FAIL: should have raised")
except IndexError:
    print("OK: empty mailbox raised IndexError as expected")

print("checkpoint2: OK")
