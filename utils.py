
_f = open("log.txt", "w")

def log(*args, **kwargs):
    print(*args, **kwargs, file=_f, flush=True)