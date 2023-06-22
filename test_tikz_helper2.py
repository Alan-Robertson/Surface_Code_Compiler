
from mapper import RegNode
from qcb import SCPatch

def print_header2(f):
    print(r"""
%!TEX options=--shell-escape
\documentclass[tikz, border=100pt]{standalone}
\usepackage[export]{animate}
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

\begin{animateinline}[]{1}
""", file=f)
def print_tikz_start(f, scale=1.5):
    print(r"""\begin{tikzpicture}[scale="""+str(scale)+r""",background rectangle/.style={fill=white},
    show background rectangle]
        """, file=f)

def print_tikz_end(f):
    print(r"""
\end{tikzpicture}
\newframe    
    """, file=f)

def print_footer2(f):
    print(r"""
\end{animateinline}

\end{document}
        """, file=f)


def make_bg(segments, f):
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


def print_inst_locks2(segments, insts, file='router1.tex'):
    with open(file, "w") as f:
        print_header2(f)
        
        max_t = max(i.end for i in insts)
        
        for t in range(max_t):
            print_tikz_start(f, scale=1.5)
            make_bg(segments, f)
            for inst in insts:
                if not (inst.start <= t < inst.end):
                    continue
                nodes = inst.anc.nodes
                # offset = 0.03 * inst.start
                offset = 0
                if len(nodes) > 1:
                    x, y = nodes[0].x+0.5+offset, -nodes[0].y-0.5-offset
                    print(f"\\draw ({x}, {y}) ", end='', file=f)
                    for node in nodes[1:]:
                        x, y = node.x+0.5+offset, -node.y-0.5-offset
                        print(f"-- ({x}, {y}) ", end='', file=f)
                    print(";", file=f)
                x, y = nodes[0].x+0.5+offset, -nodes[0].y-0.5-offset
                print(f"\\node[shape=circle,draw=black] at ({x}, {y}) {{}};", file=f)
                x, y = nodes[-1].x+0.5+offset, -nodes[-1].y-0.5-offset
                print(f"\\node[shape=circle,draw=black] at ({x}, {y}) {{}};", file=f)

            print_tikz_end(f)

        print_footer2(f)
