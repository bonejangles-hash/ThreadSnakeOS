from .types import Send, Receive, Spawn, Exit, Yield, GetInfo, SetTrace


def send(cap, body, caps=None, reply=False):
    result = yield Send(cap, body, caps or {}, reply)
    return result


def receive():
    message = yield Receive()
    return message


def call(cap, body, caps=None):
    """Blocking request/response RPC - the workhorse of the client code."""
    status = yield Send(cap, body, caps or {}, reply=True)
    if status != "OK":
        return {"error": status}
    response = yield Receive()
    result = dict(response.body)
    result.update(response.caps)
    return result


def reply_to(message, body, caps=None):
    """Answer a request, using the reply capability the kernel attached."""
    handle = message.caps.get("reply")
    if handle is None:
        return "ENOREPLY"
    result = yield Send(handle, body, caps or {})
    return result


def spawn(coroutine, name='anon'):
    handle = yield Spawn(coroutine, name)
    return handle


def exit_task(status=0):
    yield Exit(status)


def yield_cpu():
    yield Yield()


def whoami():
    info = yield GetInfo()
    return info

def set_trace(enabled):
    """Toggle the kernel's [kernel]-prefixed debug log on/off"""
    new_state = yield SetTrace(enabled)
    return new_state
