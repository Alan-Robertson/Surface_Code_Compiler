import qcb

def set_i(s, i):
    i_0 = iter(s)
    while i > 0:
        next(i_0)
        i -= 1
    return next(i_0)

def contains(edge, a, b=None):
    if b is None:
        return len()

q = qcb.QCB(5, 5)

s = qcb.Segment(0, 0, 4, 4)

segs = s.split(0, 0, 1, 1)

split = segs.pop(3)
segs += split.confirm_split(split.split(1, 1, 1, 1))

print(
    segs[2] in segs[0].right,
    segs[3] in segs[1].right,
    segs[4] in segs[1].right,
    len(segs[2].right) == 0,
    segs[5] in segs[3].right,
    segs[5] in segs[3].right,
    segs[6] in segs[4].right,
    len(segs[5].right) == 0,
    len(segs[6].right) == 0
)

print(
    segs[1] in segs[0].below,
    len(segs[2].below) == 0,
    segs[5] in segs[3].right,
    segs[5] in segs[3].right,
    segs[6] in segs[4].right,
    len(segs[5].right) == 0,
    len(segs[6].right) == 0
)

print(
    segs[2] in segs[0].right,
    segs[3] in segs[1].right,
    segs[4] in segs[1].right,
    len(segs[2].right) == 0,
    segs[5] in segs[3].right,
    segs[5] in segs[3].right,
    segs[6] in segs[4].right,
    len(segs[5].right) == 0,
    len(segs[6].right) == 0
)
