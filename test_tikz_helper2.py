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

def tikz(obj):
    return obj.__tikz__()

def tex(obj, *args, **kwargs):
    return tex_file(obj.__tikz__, *args, **kwargs)

dag_colour_map = lambda dag_node: ['red!20', 'blue!20'][dag_node.is_extern()]
tikz_sanitise = lambda string : str(string).replace('_', '\\_')

def tex_header(*tiksargs):
    return r"""
%!TEX options=--shell-escape
\documentclass[tikz]{standalone}
\usepackage[T1]{fontenc}
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
\usepackage[export]{animate}


\pagecolor{white}

\setlength{\parindent}{0cm}
\setlength{\parskip}{1em}

\begin{document}
"""

def tikz_argparse(*args, **kwargs):
    arg_str = ','.join(map(tikz_sanitise, map(str, args)))
    kwarg_str = ','.join(map(lambda item: f"{tikz_sanitise(item[0])}={tikz_sanitise(item[1])}", kwargs.items()))
    if len(kwarg_str) == 0:
        return arg_str
    return f"{arg_str},{kwarg_str}"

def tikz_footer():
    return "\n \\end{tikzpicture} \n"""

def new_frame():
    return "\n \\newframe \n"

def tex_footer():
    return "\n\end{document}\n"

def tex_file(fn, *args, **kwargs):
    tex_file = tex_header()
    tex_file += fn(*args, **kwargs)
    tex_file += tex_footer()
    return tex_file


def tikz_header(*args, **kwargs):
    return f"\\begin{{tikzpicture}}[{tikz_argparse(*args, **kwargs)}]\n"

def animate_header():
    return "\\begin{animateinline}[]{1}\n"
def animate_footer():
    return "\\end{animateinline}\n"

def make_bg(segments):
    out = ''
    for s in segments:
        colour = colour_map.get(s.state.state, 'yellow')
        
        out += f"\\draw[fill={colour},fill opacity=0.5] ({s.x_0},-{s.y_0}) -- ({s.x_0},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_1+1}) -- ({s.x_1+1},-{s.y_0}) -- cycle;\n"
        if s.state.state == SCPatch.EXTERN:
            out += f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s.state.state}{s.state.msf.symbol}}};\n"
        else:
            out += f"\\node at ({s.x_0+0.5},-{s.y_0+0.5}) {{{s.state.state}{s.debug_name}}};\n"
    return out



# def print_inst_locks2(segments, insts, file='router1.tex'):
#     with open(file, "w") as f:
#         print_header(f,skip=True)
        
#         max_t = max(i.end for i in insts)
        
#         for t in range(max_t):
#             print_tikz_start(f, scale=1.5)
#             make_bg(segments, f)
#             for inst in insts:
#                 if not (inst.start <= t < inst.end):
#                     continue
#                 nodes = inst.anc.nodes
#                 # offset = 0.03 * inst.start
#                 offset = 0
#                 if len(nodes) > 1:
#                     x, y = nodes[0].x+0.5+offset, -nodes[0].y-0.5-offset
#                     print(f"\\draw ({x}, {y}) ", end='', file=f)
#                     for node in nodes[1:]:
#                         x, y = node.x+0.5+offset, -node.y-0.5-offset
#                         print(f"-- ({x}, {y}) ", end='', file=f)
#                     print(";", file=f)
#                 x, y = nodes[0].x+0.5+offset, -nodes[0].y-0.5-offset
#                 print(f"\\node[shape=circle,draw=black] at ({x}, {y}) {{}};", file=f)
#                 x, y = nodes[-1].x+0.5+offset, -nodes[-1].y-0.5-offset
#                 print(f"\\node[shape=circle,draw=black] at ({x}, {y}) {{}};", file=f)

#             print_tikz_end(f)

#         print_footer(f,skip=True)


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
    out = f"w={round(node.weight, 2)}"
    # out += f"\\\\s={node.slots}"
    if node.seg:
        out += f"\\\\{node.seg.x_0, node.seg.y_0}"
    if node.qubits and not node.children:
        
        out += f"\\\\ {','.join(map(str, node.qubits))}"
        out += f"\\\\ {','.join(map(lambda x: hex(id(x)), node.qubits))}"
        out += f"\\\\ {str(len(node.qubits))}"
    out = out.replace('_', '\\_')
    return out

def tikz_rectangle(x_0, y_0, x_1, y_1, *args, **kwargs):
    return f"\\draw[{tikz_argparse(*args, **kwargs)}] \
({x_0},-{y_0}) -- ({x_0},-{y_1}) -- ({x_1},-{y_1}) -- ({x_1},-{y_0}) -- cycle;\n"

def tikz_node(x, y, label):
    return f"\\node at ({x},-{y}) {{{tikz_sanitise(label)}}};\n"

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
    segment_str = tikz_segment_rectangle(segment, colour)
    sym = segment.get_symbol()
    segment_str += tikz_node(segment.x_0 + 0.5, segment.y_0 + 0.5, f"{segment}{sym}")
    return segment_str

def tikz_qcb(qcb):    
    tikz_str = tikz_header()
    for segment in qcb.segments:
        tikz_str += tikz_qcb_segement(segment)    
    tikz_str += tikz_footer()
    return tikz_str


def tikz_circle(x, y, key, label, *args, **kwargs):
    return f"\\node[shape=circle \
{tikz_argparse(*args, **kwargs)}] \
({key}) at ({x}, -{y}) {{{tikz_sanitise(label)}}};\n"

def tikz_path(start, end):
    return f"\\path[->] ({start}) edge ({end});\n"

def tikz_graph_edge(node_start, node_end):
    return tikz_path(hex(id(node_start)), hex(id(node_end)))

def tikz_graph_node(segment, *args, **kwargs):
    colour = colour_map.get(segment.state.state, colour_map['debug'])
    return tikz_circle(segment.x, segment.y, hex(id(segment)), f"{segment.x_0}, {segment.y_0}", fill=colour, draw=colour)

def tikz_dag_node(node, x, y, *args, **kwargs):
    colour = dag_colour_map(node)
    return tikz_circle(x, y, key=hex(id(node)), label=node, draw=colour)

def tikz_dag_edge(node_start, node_end):
    return tikz_graph_edge(node_start, node_end)

def tikz_connectivity_graph(segments):
        graph_tikz_str = tikz_header(scale=2.5)

        seen = set()

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

def tikz_dag(dag):
    tikz_str = tikz_header(scale=5)
    for layer_num, gates in enumerate(dag.layers):
        for gate_num, gate in enumerate(gates):
            tikz_str += tikz_dag_node(gate, 2 * gate_num, 2 * layer_num) 
            for prev_gate in gate.predicates:
                tikz_str += tikz_dag_edge(prev_gate, gate)
    tikz_str += tikz_footer()
    return tikz_str


def tikz_compiled_dag(dag, *args, **kwargs):
    tikz_str = tikz_header(scale=5)
    _, layers = dag.compile(*args, **kwargs)
    for layer_num, gates in enumerate(layers):
        for gate_num, gate in enumerate(gates):
            tikz_str += tikz_dag_node(gate.get_symbol(), 0.2 * gate_num, 0.2 * layer_num) 
    tikz_str += tikz_footer()
    return tikz_str
