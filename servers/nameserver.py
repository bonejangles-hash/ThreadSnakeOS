from tskernel.lib import receive, reply_to


def name_server():
    registry = {}
    while True:
        msg = yield from receive()
        op = msg.body.get("op")

        if op == "REGISTER":
            handle = msg.caps.get("service")
            if handle is None:
                yield from reply_to(msg, {"status": "ENOCAP"})
            else:
                registry[msg.body["name"]] = handle
                yield from reply_to(msg, {"status": "OK"})
        elif op == "LOOKUP":
            name = msg.body["name"]
            if name in registry:
                # hand back a capability to the requested service
                yield from reply_to(msg, {"status": "OK"}, caps={"service": registry[name]})
            else:
                yield from reply_to(msg, {"status": "ENOENT"})
        elif op == "LIST":
            yield from reply_to(msg, {"status": "OK",
                                      "names": sorted(registry)})
