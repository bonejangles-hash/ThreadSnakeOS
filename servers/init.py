from tskernel.lib import call, send, spawn, receive
from servers.nameserver import name_server
from servers.console import console_server
from servers.fileserver import file_server
from servers.shell import shell


def init(ns_cap):
    # 1. start the servers
    con_cap = yield from spawn(console_server(), "console")
    fs_cap = yield from spawn(file_server(), "fs")

    # 2. publish them in the name server
    yield from call(ns_cap, {"op": "REGISTER", "name": "console"},
                    caps={"service": con_cap})
    yield from call(ns_cap, {"op": "REGISTER", "name": "fs"},
                    caps={"service": fs_cap})

    # 3
    yield from shell(ns_cap)
