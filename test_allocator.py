from qcb import SCPatch

def print_latex(segments, file="latex.tex"):
    with open(file, "w") as f:
        print(r"""

\documentclass[tikz, border=100pt, convert={outext=.png}]{standalone}
\usepackage[utf8]{inputenc}
\usepackage{xcolor}
\usepackage{amsmath}
\usepackage{amssymb}
\usepackage{hyperref}
\usepackage{accsupp}    
\usepackage{graphicx}
\usepackage{mathtools}
\usepackage{pagecolor}
\usepackage{amsmath} % for \dfrac
\usepackage{tikz}
\tikzset{>=latex} % for LaTeX arrow head
\usepackage{pgfplots} % for the axis environment
\usepackage[edges]{forest}
\usetikzlibrary{patterns, backgrounds, arrows.meta}

\pagecolor{white}

\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}

\begin{document}


\begin{tikzpicture}[scale=1,background rectangle/.style={fill=white},
    show background rectangle]
        """, file=f)


        for s in segments:
            if s.state.state == SCPatch.IO:
                color = 'blue!50!red!50'
            elif s.state.state == SCPatch.ROUTE:
                color = 'green!20'
            elif s.state.state == SCPatch.MSF:
                color = 'blue!20'
            elif s.state.state == SCPatch.REG:
                color = 'red!20'
            elif s.state.state == SCPatch.NONE:
                color = 'black!10'
            elif s.state.state == 'debug':
                color = 'yellow'
            print(f"\\draw[fill={color},fill opacity=0.5] ({s.x_0},-{s.y_0}) -- ({s.x_0},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_0}) -- cycle;", file=f)
            print(f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s.state.state}}};", file=f)

        print(r"""
\end{tikzpicture}


\end{document}
        """, file=f)


import allocator
from msf import MSF
msfs = [
    [8, 3],
    [6, 2],
    [5, 5],
    [3, 8],
    [5, 8],
    [2, 3],
    [6, 4],
    [1, 4],
]
msfs.sort(reverse=True)

msfs2 = []
for i, s in enumerate(msfs):
    msfs2.append(MSF(i, s, None))


# qcb = allocator.QCB(15, 20, 8, 500, *msfs2)
qcb = allocator.QCB(20, 30, 8, 500, *msfs2)
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

name_segments(qcb.segments)

# print(qcb.get_free_segments())
# print(qcb.get_free_segments()[4])
# print(qcb.get_free_segments()[4].left)

print_latex(qcb.segments, 'allocatorx.tex')
# print_edges(qcb.segments)
# print(list(qcb.segments)[-1].right)
# for s in qcb.segments:
#     print(s)

def _validate(self):
    all_segs = set.union(*map(lambda s: set.union(*s.edges().values()), self.segments))
    return len(all_segs - self.segments) == 0
print(_validate(qcb))