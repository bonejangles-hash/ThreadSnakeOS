from tskernel.kernel import Kernel
from servers.nameserver import name_server
from servers.init import init


def boot(trace=False):
    kernel = Kernel(trace=trace)

    ns_task = kernel.create_task(name_server(), "nameserver")

    # init is the only task that gets the name server capability for free
    # every other task must be given one. This is the root of trust.
    init_coroutine = init(ns_cap=0)
    init_task = kernel.create_task(init_coroutine, "init")
    init_task.install_cap(kernel.full_cap(ns_task))     # becomes handle 0

    outcome = kernel.run()
    print(f"\nkernel exited: {outcome}")
    print(f"stats: {kernel.stats}")


if __name__ == "__main__":
    boot()
