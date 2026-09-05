from tskernel.kernel import Kernel
from tskernel.lib import call, spawn
from servers.nameserver import name_server
from servers.console import console_server
from servers.fileserver import file_server


def init(ns_cap):
    con_cap = yield from spawn(console_server(), "console")
    fs_cap = yield from spawn(file_server(), "fs")

    yield from call(ns_cap, {"op": "REGISTER", "name": "console"}, caps={"service": con_cap})
    yield from call(ns_cap, {"op": "REGISTER", "name": "fs"}, caps={"service": fs_cap})

    result = yield from call(fs_cap, {"op": "READ", "path": "/etc/motd"})
    if result.get("status") == "OK":
        yield from call(con_cap, {"op": "WRITE", "text": result["data"].strip()})
    else:
        yield from call(con_cap, {"op": "WRITE", "text": f"read failed: {result}"})


def boot(trace=True):
    kernel = Kernel(trace=trace)
    ns_task = kernel.create_task(name_server(), "nameserver")

    init_coroutine = init(ns_cap=0)
    init_task = kernel.create_task(init_coroutine, "init")
    init_task.install_cap(kernel.full_cap(ns_task))

    outcome = kernel.run()
    print(f"\nkernel exited: {outcome}")
    print(f"stats: {kernel.stats}")


boot()
