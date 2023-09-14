from collections import deque
from functools import partial

consume = partial(deque, maxlen=0)

