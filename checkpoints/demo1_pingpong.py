from tskernel.kernel import Kernel
from tskernel.lib import call, receive, send

def ping(pong_handle_box):
    for i in range(3):
        result = yield from call(pong_handle_box[0], {"n": i})
        print(f"ping received: {result}")

def pong():
    while True:
        msg = yield from receive()
        yield from send(msg.caps["reply"], {"n": msg.body["n"] + 100})

k = Kernel(trace=True)
box = [None]
pong_task = k.create_task(pong(), "pong")
ping_task = k.create_task(ping(box), "ping")
box[0] = ping_task.install_cap(k.full_cap(pong_task))

outcome = k.run(max_steps=200)
print("outcome:", outcome, "stats:", k.stats)
