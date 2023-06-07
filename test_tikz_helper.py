
from allocator import RegNode
from qcb import SCPatch

def print_header(f, scale=1):
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


\begin{tikzpicture}[scale="""+str(scale)+""",background rectangle/.style={fill=white},
    show background rectangle]
        """, file=f)

def print_footer(f):
    print(r"""
\end{tikzpicture}


\end{document}
        """, file=f)



def recurse(node, f, used_pos):
    if node.seg:
        color = 'red'
    else:
        color = 'black'
    
    pos_list = []
    for s in node.children:
        pos_list.append(recurse(s, f, used_pos))
    
    if not pos_list:
        x = node.seg.x_0
        y = node.seg.y_0
        used_pos.add((x,y))
    else:
        x = sum(map(lambda x: x[0], pos_list))/len(pos_list)
        y = sum(map(lambda x: x[1], pos_list))/len(pos_list)
        x = int(x)
        y = int(y)
        while (x,y) in used_pos:
            x += 1

    print(f"\\node[shape=circle,draw={color},align=center] ({id(node)}) at ({x}, -{y}) {{{regnode_data(node)}}};", file=f)
    for c in node.children:
        print(f"\\path[->] ({id(node)}) edge ({id(c)});", file=f)
    return (x, y)

def print_mapping_tree(root, file="latex.tex"):
    with open(file, "w") as f:
        print_header(f, scale=2)
        recurse(root, f, set())
        print_footer(f)


def regnode_data(node:RegNode):
    return f"w={round(node.weight, 2)}\\\\s={node.slots}" + (f"\\\\{node.seg.x_0, node.seg.y_0}" if node.seg else '')


def print_connectivity_graph(segments, file="latex.tex"):
    with open(file, "w") as f:
        print_header(f, scale=1)

        seen = set()

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

            print(f"\\node[shape=circle,draw={color}] ({id(s)}) at ({s.x_0}, -{s.y_0}) {{{s.x_0},{s.y_0}}};", file=f)
            seen.add(id(s))
        for s in segments:
            for n in s.above | s.below | s.left | s.right:
                if n and id(n) in seen:
                    print(f"\\path[->] ({id(s)}) edge ({id(n)});", file=f)
                else:
                    print(f"\\path[->] ({id(s)}) edge (-1,1);", file=f)


        print_footer(f)


def print_qcb(segments, file="latex.tex"):
    with open(file, "w") as f:
        print_header(f)

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

        print_footer(f)