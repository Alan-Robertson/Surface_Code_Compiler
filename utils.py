from collections import deque
from functools import partial

consume = partial(deque, maxlen=0)


_f = open("log.txt", "w")


def log(*args, **kwargs):
    print(*args, **kwargs, file=_f, flush=True)