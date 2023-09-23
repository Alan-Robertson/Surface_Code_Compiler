from collections import deque
from functools import partial

consume = partial(deque, maxlen=0)


def debug_print(*strings, debug=False):
    if debug:
        print(*strings)
