from tskernel.types import Send, Message

s = Send(cap=3, body={"op": "PING"})
print(s)
assert s.cap == 3
assert s.body == {"op": "PING"}
assert s.reply is False

m = Message(sender=1, body={"x": 1})
assert m.caps == {}
print("checkpoint1: OK")
