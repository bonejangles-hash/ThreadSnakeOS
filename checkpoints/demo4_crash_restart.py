from tskernel.kernel import Kernel
from tskernel.lib import call, send, spawn, yield_cpu
from servers.fileserver import file_server


def supervisor():
    fs_cap = yield from spawn(file_server(), "fs")

    # normal operation
    result = yield from call(fs_cap, {"op": "READ", "path": "/etc/motd"})
    print("before crash:", result)

    # deliberately crash the file server -- fire-and-forget, since a task
    # that's about to die mid-request will never send a reply
    status = yield from send(fs_cap, {"op": "CRASH"})
    print("crash send returned:", status)
    yield from yield_cpu()  # let the scheduler give fs a turn to process it

    # the server is now dead -- prove it
    result = yield from call(fs_cap, {"op": "READ", "path": "/etc/motd"})
    print("after crash, same cap:", result)

    # supervisor notices the EDEAD and spawns a fresh replacement
    new_fs_cap = yield from spawn(file_server(), "fs-restarted")
    result = yield from call(new_fs_cap, {"op": "READ", "path": "/etc/motd"})
    print("after restart, new cap:", result)


k = Kernel(trace=False)
k.create_task(supervisor(), "supervisor")
outcome = k.run()
print("kernel outcome:", outcome)
