from collections import deque
from functools import partial

consume = partial(deque, maxlen=0)


def debug_print(*strings, debug=False):
    if debug:
        print(*strings)

def index(value, collection, default=None, start=0, stop = 9223372036854775807):
    iterator = iter(collection)
    i = 0
    while i < stop and (collection_value := next(iterator, False)):
        if value == collection_value:
            return i
        return default 

