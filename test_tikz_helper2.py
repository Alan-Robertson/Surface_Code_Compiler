
from mapper import RegNode
from qcb import SCPatch

def print_header(f, scale=1):
    print(r"""
%!TEX options=--shell-escape
\documentclass[tikz, border=100pt]{standalone}
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

\begin{tikzpicture}[]{1}
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

def print_footer(f):
    print(r"""
\end{tikzpicture}

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
        print_header(f)
        
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

        print_footer(f)


def recurse(node, file_obj, used_pos):
    if node.seg and node.pred_sym is None:
        color = 'red'
    elif node.seg and node.pred_sym is not None:
        color = 'blue'
    else:
        color = 'black'
    
    pos_list = []
    for s in node.children:
        pos_list.append(recurse(s, file_obj, used_pos))
    
    if not pos_list:
        x = node.seg.x_0
        y = node.seg.y_0
        used_pos.add((x,y))
    else:
        x = sum(map(lambda x: x[0], pos_list)) / len(pos_list)
        y = sum(map(lambda x: x[1], pos_list)) / len(pos_list)
        x = int(x)
        y = int(y)
        while (x, y) in used_pos:
            x += 2.5

    print(f"\\node[shape=circle,draw={color},align=center] ({id(node)}) at ({x}, -{y}) {{{regnode_data(node)}}};", file=file_obj)
    for c in node.children:
        print(f"\\path[->] ({id(node)}) edge ({id(c)});", file=file_obj)
    return (x, y)

def print_mapping_tree(root, file="latex.tex"):
    with open(file, "w") as file_obj:
        print_header(file_obj, scale=2.5)
        recurse(root, file_obj, set())
        print_footer(file_obj)

def regnode_data(node:'RegNode'):
    out = f"w={round(node.weight, 2)}\\\\s={node.slots}"
    if node.seg:
        out += f"\\\\{node.seg.x_0, node.seg.y_0}"
    if node.qubits:
        
        out += f"\\\\ {','.join(map(str, node.qubits))}"
        out += f"\\\\ {','.join(map(lambda x: hex(id(x)), node.qubits))}"
        out += f"\\\\ {str(len(node.qubits))}"
    out = out.replace('_', '\\_')
    return out


def print_qcb(segments, file="latex.tex"):
    with open(file, "w") as f:
        print_header(f)

        colours = {
            SCPatch.IO:'blue!50!red!50',
            SCPatch.ROUTE:'green',
            SCPatch.EXTERN:'blue',
            SCPatch.REG:'red',
            SCPatch.NONE:'black',
            'debug':'yellow'
        }

        for s in segments:

            s_type = s
            colour = colours[s.state.state]
            
            print(f"\\draw[fill={colour},fill opacity=0.5] ({s.x_0},-{s.y_0}) -- ({s.x_0},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_0}) -- cycle;", file=f)
            if s.state.state == SCPatch.EXTERN:
                sym = str(s.state.msf.symbol).replace('_', '\\_')

                print(f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s_type}{sym}}};", file=f)
            else:
                print(f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s_type}{s.debug_name}}};", file=f)

        print_footer(f)


def print_connectivity_graph(segments, file="latex.tex"):
    with open(file, "w") as f:
        print_header(f, scale=2.5)

        seen = set()

        colours = {
            SCPatch.IO:'blue!50!red!50',
            SCPatch.ROUTE:'green',
            SCPatch.EXTERN:'blue',
            SCPatch.REG:'red',
            SCPatch.NONE:'black',
            'debug':'yellow'
        }
        for s in segments:

            colour = colours.get(s.state.state, colours['debug'])

            print(f"\\node[shape=circle,draw={colour}] ({id(s)}) at ({s.x_0}, -{s.y_0}) {{{s.x_0},{s.y_0}}};", file=f)
            seen.add(id(s))
        for s in segments:
            for n in s.above | s.below | s.left | s.right:
                if n and id(n) in seen:
                    print(f"\\path[->] ({id(s)}) edge ({id(n)});", file=f)
                else:
                    print(f"\\path[->] ({id(s)}) edge (-1,1);", file=f)
        print_footer(f)
