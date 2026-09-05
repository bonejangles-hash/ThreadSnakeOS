from tskernel.task import Task
from tskernel.types import Yield


def hello():
    yield Yield()


t = Task(tid=1, coroutine=hello(), name="hello")
request = t.step()
print(request)
assert isinstance(request, Yield)
print("checkpoint3: OK")
