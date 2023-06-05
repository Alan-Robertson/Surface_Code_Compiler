from qcb import SCPatch
def print_graph(segments, file="latex.tex"):
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
                color = 'green'
            elif s.state.state == SCPatch.MSF:
                color = 'blue'
            elif s.state.state == SCPatch.REG:
                color = 'red'
            elif s.state.state == SCPatch.NONE:
                color = 'black'
            elif s.state.state == 'debug':
                color = 'yellow'

            print(f"\\node[shape=circle,draw={color}] at ({s.x_0}, -{s.y_0}) {{{s.x_0},{s.y_0}}};", file=f)
            for n in s.above | s.below | s.left | s.right:
                if n:
                    print(f"\\path[->] ({s.x_0},-{s.y_0}) edge ({n.x_0},-{n.y_0});", file=f)

        print(r"""
\end{tikzpicture}


\end{document}
        """, file=f)