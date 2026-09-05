from tskernel.lib import receive, reply_to


def console_server():
    history = []
    while True:
        msg = yield from receive()
        op = msg.body.get("op")

        if op == "WRITE":
            text = msg.body.get("text", "")
            history.append(text)
            print(f"[console] {text}")
            yield from reply_to(msg, {"status": "OK", "bytes": len(text)})

        elif op == "HISTORY":
            yield from reply_to(msg, {"status": "OK", "lines": history})

        else:
            yield from reply_to(msg, {"status": "EINVAL"})
