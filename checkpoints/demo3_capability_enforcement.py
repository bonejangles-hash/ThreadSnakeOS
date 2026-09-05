from tskernel.kernel import Kernel
from tskernel.lib import send

def rogue():
    # tries to send to handle 99, which it was never given
    status = yield from send(99, {"attack": "give me root"})
    print("rogue's send returned:", status)

k = Kernel()
k.create_task(rogue(), "rogue")
k.run()
