from tskernel.lib import receive, reply_to


def file_server(initial=None):
    files = dict(initial or {"/etc/motd": "welcome to ThreadSnakeOS\n"})
    open_handles = {}
    next_id = [0]

    while True:
        msg = yield from receive()
        op = msg.body.get("op")
        path = msg.body.get("path")

        if op == "READ":
            if path in files:
                yield from reply_to(msg, {"status": "OK", "data": files[path]})
            else:
                yield from reply_to(msg, {"status": "ENOENT"})
        elif op == "WRITE":
            files[path] = msg.body.get("data", "")
            yield from reply_to(msg, {"status": "OK"})
        elif op == "DELETE":
            removed = files.pop(path, None)
            yield from reply_to(msg,
                                {"status": "OK" if removed is not None else "ENOENT"})
        elif op == "LIST":
            yield from reply_to(msg, {"status": "OK", "files": sorted(files)})
        elif op == "CRASH":
            raise RuntimeError("simulated file server bug")
        else:
            yield from reply_to(msg, {"status": "EINVAL"})
