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
            if s.state.state == SCPatch.MSF:
                print(f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s.state.state}{s.state.msf.symbol}}};", file=f)
            else:
                print(f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s.state.state}{s.debug_name}}};", file=f)

        print(r"""
\end{tikzpicture}


\end{document}
        """, file=f)


import allocator
from msf import MSF
import dag
import msf

t_fact = msf.MSF('T', (5, 3), 19)
q_fact = msf.MSF('Q', (4, 4), 15)


g = dag.DAG(12)
g.add_gate(2, 'T', magic_state=True)
# g.add_gate(3, 'T', magic_state=True)
# g.add_gate(0, 'Q', magic_state=True)
g.add_gate(0, 'Z')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate([0, 1], 'CNOT')
g.add_gate(1, 'Z')
g.add_gate([0, 1], 'CNOT')
g.add_gate(2, 'Z')
g.add_gate(2, 'Z')
g.add_gate(2, 'Z')
#g.add_gate([2, 3], 'CNOT')
g.add_gate([0, 2], 'CNOT')
#g.add_gate(1, 'Z')
g.add_gate([0, 2], 'CNOT')
g.add_gate([2, 3], 'CNOT')
g.add_gate(2, 'T', magic_state=True)
# g.add_gate(3, 'T', magic_state=True)
# g.add_gate(0, 'Q', magic_state=True)
#g.add_gate(1, 'Z')
g.add_gate([0, 1], 'CNOT')


qcb = allocator.QCB(7, 8, 4, g.n_blocks, t_fact)


try:
    qcb.allocate()
    print("Allocate success")
    try:
        qcb.optimise(g)
    except Exception as e:
        import traceback
        traceback.print_exc()

    print("Optimise success")
except Exception as e:
    import traceback
    traceback.print_exc()

print_latex(qcb.segments, 'allocatora.tex')



def _validate(self):
    all_segs = set.union(*map(lambda s: set.union(*s.edges().values()), self.segments))
    return len(all_segs - self.segments) == 0
print(_validate(qcb))
