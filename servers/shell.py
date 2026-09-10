from tskernel.lib import call, spawn, set_trace


def shell(ns_cap):
    """A user task that reads real commands from the terminal and turns
    them into IPC calls against the simulated fs/console servers.

    This is the one place in the whole system where 'blocking' means
    something outside the simulation: input() is a real syscall to the
    actual OS underneath us, and the entire kernel (every other task)
    is frozen while we wait for it -- exactly as if a real single-core
    machine were sitting at a shell prompt.
    """
    fs = (yield from call(ns_cap, {"op": "LOOKUP", "name": "fs"}))["service"]
    con = (yield from call(ns_cap, {"op": "LOOKUP", "name": "console"}))["service"]

    yield from call(con, {"op": "WRITE", "text": "ThreadSnakeOS shell. commands: ls, read <path>, write <path> <text>, , trace <on/off>, exit"})

    while True:
        line = input("tsos> ").strip()   # <-- real terminal I/O, not simulated
        if not line:
            continue
        parts = line.split(maxsplit=2)
        cmd = parts[0]

        if cmd == "exit":
            break

        elif cmd == "ls":
            result = yield from call(fs, {"op": "LIST"})
            yield from call(con, {"op": "WRITE", "text": str(result.get("files", result))})

        elif cmd == "read" and len(parts) >= 2:
            result = yield from call(fs, {"op": "READ", "path": parts[1]})
            text = result.get("data", result)
            yield from call(con, {"op": "WRITE", "text": str(text).rstrip()})

        elif cmd == "write" and len(parts) >= 3:
            result = yield from call(fs, {"op": "WRITE", "path": parts[1], "data": parts[2]})
            yield from call(con, {"op": "WRITE", "text": str(result)})

        elif cmd == "trace" and len(parts) >= 2:
            enabled = parts[1].lower() in ("on", "1", "true")
            new_state = yield from set_trace(enabled)
            yield from call(con, {"op": "WRITE",
                                  "text": f"kernel trace is now {'ON' if new_state else 'OFF'}"})

        else:
            yield from call(con, {"op": "WRITE", "text": f"unknown command: {line!r}"})
