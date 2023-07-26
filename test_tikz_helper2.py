from mapper import RegNode
from qcb import SCPatch

colour_map = {
    SCPatch.IO:'blue!50!red!50',
    SCPatch.ROUTE:'green!20',
    SCPatch.EXTERN:'blue!20',
    SCPatch.REG:'red!20',
    SCPatch.NONE:'black!20',
    'debug':'yellow!30'
}

def tex_header(*tiksargs):
    return r"""
%!TEX options=--shell-escape
\documentclass[tikz]{standalone}
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
\usepackage{pgfplots} 
\usepackage[edges]{forest}
\usetikzlibrary{patterns, backgrounds, arrows.meta}

\pagecolor{white}

\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}

\begin{document}
"""

def tikz_arg_parse(*args, **kwargs):
    arg_str = ','.join(map(str, args))
    kwarg_str = ','.join(map(lambda item: f"{item[0]}={item[1]}", kwargs.items()))
    if len(kwarg_str) == 0:
        return arg_str
    return f"{arg_str},{kwarg_str}"

def tikz_header(*args, **kwargs):
    return f"""\\begin{{tikzpicture}}[{tikz_arg_parse(*args, **kwargs)}]\n"""

def tikz_footer():
    return "\n\\end{tikzpicture}\n"""

def new_frame():
    return "\n \\newframe \n"

def tex_footer():
    return r"\end{document}"


def make_bg(segments, f):
    for s in segments:
        colour = colour_map.get(s.state.state, 'yellow')
        
        print(f"\\draw[fill={colour},fill opacity=0.5] ({s.x_0},-{s.y_0}) -- ({s.x_0},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_0}) -- cycle;", file=f)
        if s.state.state == SCPatch.EXTERN:
            print(f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s.state.state}{s.state.extern.symbol}}};", file=f)
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

def tikz_rectangle(x_0, y_0, x_1, y_1, *args, **kwargs):
    return f"\\draw[{tikz_arg_parse(*args, **kwargs)}] \
({x_0},-{y_0}) -- ({x_0},-{y_1}) -- ({x_1},-{y_1}) -- ({x_1},-{y_0}) -- cycle;\n"

def tikz_node(x, y, label):
    return f"\\node at ({x},-{y}) {{{label}}};\n"

def tikz_segment_rectangle(segment, colour, *args):
    return tikz_rectangle(
            segment.x_0, 
            segment.y_0, 
            segment.x_1 + 1, 
            segment.y_1 + 1, 
            f"fill={colour}",
            "opacity=0.5")

def tikz_qcb_segement(segment):
    colour = colour_map[segment.state.state]
    segment_str = segment_rectangle(segment, colour)
    if segment.state.state == SCPatch.EXTERN:
        sym = str(s.state.msf.symbol).replace('_', '\\_')
        segment_str += tikz_node(segment.x_0 + 0.5, segment.y_0 + 0.5, f"{segment}{sym}")
    else:
        segment_str += tikz_node(segment.x_0 + 0.5, segment.y_0 + 0.5, f"{segment_type}{segment.debug_name}")
    return segment_str

def tikz_qcb(segments):    
    qcb_tikz_str = tex_header()
    for segment in segments:
        qcb_tikz_str += qcb_segement_str(segment)    
    qcb_tikz_str += tikz_footer(f)
    return qcb_tikz_str




def tikz_circle(x, y, key, label, *args, **kwargs)
    return f"\\node[shape=circle, \
            {tikz_arg_parse(*args, **kwargs)}] \
            ({key}) at ({x}, -{y}) {{{label}}};"

def tikz_path(start, end):
    return f"\\path[->] ({start}) edge ({end});\n"

def tikz_graph_edge(node_start, node_end):
    return tikz_path(hex(id(node_start)), hex(id(node_end)))

def tikz_graph_node(segment, *args, **kwargs):
    colour = colour_map.get(segment.state.state, colour_map['debug'])
    return tikz_circle(segment.x, segment.y, hex(id(segment)), f"{segment.x_0}, {segment.y_0}", fill=colour, draw=colour)

def print_connectivity_graph(segments):
        graph_tikz_str = tikz_header(scale=2.5)

        seen = set()

        colours = {
            SCPatch.IO:'blue!50!red!50',
            SCPatch.ROUTE:'green',
            SCPatch.EXTERN:'blue',
            SCPatch.REG:'red',
            SCPatch.NONE:'black',
            'debug':'yellow'
        }
        for segment in segments:
            graph_tikz_str += tikz_graph_node(segment) 
            seen.add(hex(id(s)))

        for segment in segments:
            for node in segment.above | segment.below | segment.left | segment.right:
                if node is not None and hex(id(node)) in seen:
                    graph_tikz_str += tikz_graph_edge(segment, node)
#                    print(f"\\path[->] ({id(s)}) edge ({id(n)});", file=f)
#                else:
#                    print(f"\\path[->] ({id(s)}) edge (-1,1);", file=f)
        graph_tikz_str += tikz_footer()
        return graph_tikz_str
