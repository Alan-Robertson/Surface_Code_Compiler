from test_tikz_helper import *

import allocator
from msf import MSF
# msfs = [
#     [8, 3],
#     [6, 2],
#     [5, 5],
#     [3, 8],
#     [5, 8],
#     [2, 3],
#     [6, 4],
#     [1, 4],
# ]
msfs = [
    # [13, 4],
    # [7, 3],
    [7, 3],
    [5, 2],
    # [5, 2],
    [5, 2],
]
msfs.sort(reverse=True)

msfs2 = []
for i, s in enumerate(msfs):
    msfs2.append(MSF(i, s, None))

# qcb = allocator.QCB(20, 17, 8, 13, *msfs2)
# qcb = allocator.QCB(15, 20, 8, 500, *msfs2)
qcb = allocator.QCB(20, 30, 8, 30, *msfs2)
try:
    qcb.allocate()
except Exception as e:
    import traceback
    traceback.print_exc()

# qcb.place_io()
# msfs = list(qcb.msfs.values())
# qcb.place_first_msf(msfs[0])
# for i, msf in enumerate(msfs[1:3]):
#     print(i)
#     qcb.place_msf(msf)
#     print_latex(qcb.segments, f"allocator{i}.tex")

# (seg, ), confirm = qcb.get_free_segments()[3].top_merge()
# confirm(qcb.segments)
# (seg, ), confirm = seg.left_merge()
# confirm(qcb.segments)
# (seg, *_), confirm = seg.top_merge()
# confirm(qcb.segments)

from test_segments import name_segments, print_edges

# name_segments(qcb.segments)

# print(qcb.get_free_segments())
# print(qcb.get_free_segments()[4])
# print(qcb.get_free_segments()[4].left)

print_qcb(qcb.segments, 'allocatorx.tex')
# print_edges(qcb.segments)
# print(list(qcb.segments)[-1].right)
# for s in qcb.segments:
#     print(s)

def _validate(self):
    all_segs = set.union(*map(lambda s: set.union(*s.edges().values()), self.segments))
    return len(all_segs - self.segments) == 0
print(_validate(qcb))